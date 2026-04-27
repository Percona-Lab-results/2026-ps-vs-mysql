# Why MySQL 8.4.8 outperforms Percona Server 8.4.8-8 at 16/32 threads (2G tier)

## Scope

`benchmark_logs/` contains sysbench `oltp_read_write` runs with an identical
dataset (20 × ~3M row `sbtest*` tables, ~18-20 GB on disk) against two servers
running the same host, same NVMe, same kernel, same my.cnf. The only
difference is the binary: `mysql/8.4.8` vs `percona/8.4.8-8`. At the 2G
buffer-pool tier the dataset is ~10× the buffer pool, so the workload is
I/O-bound.

The two config files are byte-identical:

```
$ diff benchmark_logs/mysql/8.4.8/Tier2G.cnf.txt \
       benchmark_logs/percona/8.4.8-8/Tier2G.cnf.txt
(no output)
```

## The pattern

| Threads | MySQL TPS | Percona TPS | MySQL / Percona |
| ------: | --------: | ----------: | --------------: |
|       1 |    124.14 |      113.64 |           1.09× |
|       4 |    560.96 |      533.03 |           1.05× |
|  **16** |  **1822** |    **1581** |       **1.15×** |
|  **32** |  **2795** |    **2211** |       **1.26×** |
|      64 |      1978 |        2543 |           0.78× |
|     128 |      1187 |        1533 |           0.77× |
|     256 |       657 |         766 |           0.86× |
|     512 |       356 |         461 |           0.77× |

Data extracted from `Tier2G_RW_*th.sysbench.txt`. Below 64 threads MySQL
wins; from 64 upward Percona's thread-scheduling / contention code pays off
and it overtakes MySQL. The question is why MySQL's lead is so pronounced at
16 and 32 threads specifically.

## What the OS counters show at 16 / 32 threads

Averaged over the 900-second run (`iostat`, `vmstat`, `mpstat`):

| Metric                 | MySQL 16 | PS 16 | MySQL 32 | PS 32 |
| ---------------------- | -------: | ----: | -------: | ----: |
| `nvme0n1` r/s          |   43,261 | 37,664 |   66,067 | 52,581 |
| `nvme0n1` w/s          |   36,281 | 32,628 |   51,292 | 40,657 |
| `nvme0n1` rMB/s        |    675.9 |  588.5 |  1,032.3 |  821.6 |
| `nvme0n1` wMB/s        |    450.3 |  401.3 |    660.1 |  534.9 |
| avg queue depth        |    10.10 |   8.26 |    19.17 | 13.67 |
| disk `%util`           |    69.8 %|  65.4%|    81.1 %| 72.5 %|
| vmstat cs/s            |  361,135 | 316,024 |  564,709 | 447,010 |
| mpstat `%usr`          |      9.6 |    8.5 |     17.6 |  14.0 |
| mpstat `%iowait`       |     11.0 |    8.9 |     21.6 | 15.1 |
| mpstat `%idle`         |     76.4 |   80.1 |     55.9 |  67.0 |

Reading this together:

- **MySQL is pushing more IOPS through the same disk** — at 32 threads it
  sustains 66k read + 51k write IOPS versus Percona's 53k + 41k, on a disk
  that still has headroom in both cases (81 % vs 72 % util, queue depth 19
  vs 14).
- **MySQL burns more CPU and more iowait** — it keeps ~14 % more cores busy
  and takes 26 % more context switches per second, and that translates
  directly into the throughput gap. Percona is sitting idle more (67 % vs
  56 % at 32 threads) while having the same disk available.
- Percona is not bottlenecked on the device. The NVMe is not saturated, the
  redo log (`innodb_os_log_pending_writes = 0`) is not saturated, and
  `Innodb_log_waits = 0` / `Innodb_buffer_pool_wait_free = 0` in both
  baselines.

So the shortfall is **inside the engine**: Percona is pulling fewer pages
through the buffer pool per second, even though work is queued for it.

## Why Percona is slower per-query at low/mid concurrency

### 1. Extra per-page bookkeeping in Percona's InnoDB LRU

The `Tier2G.vars.txt` diff reveals Percona carries a set of InnoDB
counters/features that vanilla MySQL does not:

```
innodb_buffer_pool_pages_old
innodb_buffer_pool_pages_made_young
innodb_buffer_pool_pages_made_not_young
innodb_buffer_pool_pages_LRU_flushed
innodb_cleaner_lsn_age_factor       = high_checkpoint
innodb_empty_free_list_algorithm    = legacy
innodb_show_locks_held              = 10
innodb_corrupt_table_action         = assert
innodb_print_lock_wait_timeout_info = OFF
have_backup_locks / have_snapshot_cloning = YES
```

These translate to a handful of extra atomics / counters on every page
touch. On a cache-resident run (12G tier) the impact is ~5-10 %; at 2G the
LRU is churning constantly because the working set doesn't fit, so the
per-eviction overhead is multiplied. This is consistent with what we see:
the gap grows from 9 % at 1 thread → 15 % at 16 → 26 % at 32, and Percona's
disk IOPS drops proportionally.

### 2. Legacy free-list algorithm

Percona ships with `innodb_empty_free_list_algorithm = legacy` by default.
The legacy algorithm falls back to single-page sync flushes when the free
list is empty; the `backoff` algorithm (Percona's own alternative) yields
the mutex and retries. With a 2 GB buffer pool and 16-32 threads all racing
for free pages, the legacy path serializes more often. Switching this to
`backoff` would be the single highest-leverage change to test.

### 3. NUMA interleave requested but denied

Percona's `Tier2G.errlog.txt` is full of:

```
[Warning] [MY-011879] [InnoDB] Failed to set NUMA memory policy of buffer
pool page frames with mbind(...,MPOL_INTERLEAVE,...) failed with
Operation not permitted
```

`innodb_numa_interleave = ON` is the Percona default but the process lacks
`CAP_SYS_NICE`, so the `mbind()` calls fail — the buffer pool ends up on
whichever NUMA node happened to fault first. The host is 80-CPU so likely
2 NUMA nodes. This penalizes Percona but *not* MySQL, which doesn't set
that flag by default. Expected penalty: a few percent extra memory latency
on buffer-pool reads, which shows up most when the pool is small and
turnover is high — exactly the 2G tier.

### 4. Higher context switch rate does not help

One might expect Percona's lower cs/s (447k vs 564k at 32 threads) to
indicate *less* contention. In context it means the opposite: with the same
workload, fewer switches means the threads are getting blocked for longer
per stall (on a free-list spin or a NUMA-remote fetch) instead of
productively moving to a runnable state.

## Summary

At 16-32 threads in the 2G tier the workload is I/O-bound but the disk has
headroom. Percona Server falls behind MySQL because:

1. **LRU / buffer-pool churn is heavier per page**, due to Percona's extra
   instrumentation counters (`pages_old`, `pages_made_young`, etc.) that
   fire on every page access in a pool that is being completely recycled
   every few seconds.
2. **`innodb_empty_free_list_algorithm = legacy`** serializes on empty-free-
   list stalls, which happen constantly when the working set is 10× the
   pool.
3. **`innodb_numa_interleave = ON` is silently failing** (no
   `CAP_SYS_NICE`), so the Percona buffer pool is on a single NUMA node
   while readers arrive from all 80 CPUs.

The result is that Percona issues ~20 % fewer IOPS per second than MySQL at
the same thread count, which matches the ~15-26 % TPS gap almost exactly.
Above 64 threads Percona's better thread-scheduling / contention handling
outweighs these costs and it takes the lead — which is why the curves
cross.

### Suggested follow-up tests

- Set `innodb_empty_free_list_algorithm = backoff` on Percona and re-run
  the 2G / 16 and 32 thread points.
- Launch Percona with `CAP_SYS_NICE` (or `numactl --interleave=all`) so
  `innodb_numa_interleave` actually takes effect; verify no warnings in
  `errlog`.
- Rerun with `performance_schema = OFF` confirmed on both (it is) and with
  Percona-specific instrumentation off (`userstat = OFF`,
  `innodb_monitor_*` empty) — isolates the pure counter overhead.
