# 2026-ps-vs-mysql

Performance comparison of MySQL 8.4.8 vs Percona Server 8.4.8-8 on OLTP Read-Write workloads.

## Key Findings

See **[FINDINGS.md](FINDINGS.md)** for detailed performance analysis, including:
- Root cause analysis of 14% performance gap at 64 threads
- Transaction log subsystem bottleneck identification
- Lock contention patterns
- Buffer pool and CPU utilization analysis

## Interactive Reports

- **[Sysbench Results - Average](https://percona-lab-results.github.io/2026-ps-vs-mysql/sysbench_ps_mysql_average.html)** - Performance comparison averaged across runs
- **[Sysbench Results - Individual Runs](https://percona-lab-results.github.io/2026-ps-vs-mysql/sysbench_ps_mysql_individual.html)** - Detailed per-run results
- **[InnoDB Metrics Analyzer](https://percona-lab-results.github.io/2026-ps-vs-mysql/innodb_metrics_report.html)** - Interactive deep-dive into 319 InnoDB metrics
- **[System Variables Comparison](https://percona-lab-results.github.io/2026-ps-vs-mysql/system_variables_comparison.html)** - Side-by-side comparison of 706 system variables
- **[Status Variables Comparison](https://percona-lab-results.github.io/2026-ps-vs-mysql/status_variables_comparison.html)** - Side-by-side comparison of 550 status variables

## Reproducibility

### Prerequisites

Install required packages:

```bash
sudo apt install docker.io linux-tools-generic sysstat sysbench mysql-client dstat -y
```

### Grant Permissions

Add your current user to the docker group:

```bash
sudo usermod -aG docker $USER
```

Log out and back in, or run `newgrp docker` to update your group permissions without restarting.

**Note:** The user requires root access (`sudo`) as the scripts internally execute sudo commands for environment management and telemetry collection.

### Running Benchmarks

1. **Configure benchmark parameters** in `run_metrics.sh`:
   ```bash
   POOL_SIZES=(12)              # Buffer pool size in GB
   THREADS=(32 64)              # Thread counts to test
   TABLE_ROWS=5000000           # Rows per table
   DURATION=900                 # Test duration (seconds)
   ```

2. **Run MySQL benchmark**:
   ```bash
   ./run_metrics.sh mysql 8.4.8 0
   ```

3. **Run Percona Server benchmark**:
   ```bash
   ./run_metrics.sh percona-server 8.4.8-8 0
   ```

4. **Run Percona Server with legacy LSN mode**:
   ```bash
   ./run_metrics.sh percona-server 8.4.8-8 0 1
   ```

Parameters:
- `$1` - Database server name (`mysql`, `percona-server`)
- `$2` - Version tag (`8.4.8`, `8.4.8-8`)
- `$3` - Read-only mode (`0` = read-write, `1` = read-only)
- `$4` - Use legacy LSN age factor (`1` = enable, `0` or omit = disable)

### Output Structure

Benchmark results are stored in `benchmark_logs/`:

```
benchmark_logs/
├── mysql/
│   └── 8.4.8/
│       ├── Tier12G.cnf.txt
│       ├── Tier12G.vars.txt
│       ├── Tier12G.status.txt
│       ├── Tier12G.errlog.txt
│       ├── run1_Tier12G_RW_32th.sysbench.txt
│       ├── run1_Tier12G_RW_32th.innodb.txt
│       ├── run1_Tier12G_RW_32th.iostat.txt
│       ├── run1_Tier12G_RW_32th.vmstat.txt
│       ├── run1_Tier12G_RW_32th.mpstat.txt
│       └── run1_Tier12G_RW_32th.dstat.txt
│       └── ... (runs 2-3, 64 threads)
└── percona-server/
    ├── 8.4.8-8/
    │   └── ... (same structure)
    └── 8.4.8-8-legacy/
        └── ... (same structure with legacy LSN mode)
```

### Generating Reports

After running benchmarks, generate interactive reports:

```bash
# Generate all reports
bash visuals/generate_both_reports.sh

# Generate InnoDB metrics analyzer
python3 visuals/innodb_metrics_report.py benchmark_logs innodb_metrics_report.html

# Generate system/status variable comparisons
python3 << 'EOF'
# See workflow scripts for generation code
EOF
```

## Benchmark Configuration

- **Hardware**: 2x Intel Xeon Gold 6230 (40 cores, 80 threads), 187.5 GB RAM
- **OS**: Ubuntu 24.04 LTS, Kernel 6.8.0-60-generic
- **Storage**: NVMe SSD
- **Workload**: Sysbench OLTP Read-Write
- **Tables**: 20 tables × 5M rows each
- **Buffer Pool**: 12 GB
- **Thread Counts**: 16, 32, 64
- **Duration**: 15 minutes per test, 3 runs per configuration
- **Warmup**: 3 min read-only + 10 min read-write

## Documentation

- **[FINDINGS.md](FINDINGS.md)** - Performance analysis and root cause investigation
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick reference for InnoDB Metrics Analyzer
- **[THREAD_SELECTION_UPDATE.md](THREAD_SELECTION_UPDATE.md)** - Thread selection feature documentation

## License

This benchmark suite and analysis is provided as-is for reproducibility and transparency.