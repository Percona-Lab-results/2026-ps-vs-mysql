# 2026-ps-vs-mysql

Performance comparison of MySQL 8.4.8 vs Percona Server 8.4.8-8 on OLTP Read-Write workloads.

## Key Findings

See **[FINDINGS.md](FINDINGS.md)** for detailed performance analysis, including:
- Root cause analysis of 14% performance gap at 64 threads
- Transaction log subsystem bottleneck identification
- Lock contention patterns
- Buffer pool and CPU utilization analysis

## Interactive Reports

- **[Index Page](https://percona-lab-results.github.io/2026-ps-vs-mysql/index.html)** - Navigation page for all reports
- **[Sysbench Results - Average (Binlog Disabled)](https://percona-lab-results.github.io/2026-ps-vs-mysql/disabled_binlog_sysbench_average.html)** - Performance comparison averaged across runs
- **[Sysbench Results - Individual Runs (Binlog Disabled)](https://percona-lab-results.github.io/2026-ps-vs-mysql/disabled_binlog_sysbench_individual.html)** - Detailed per-run results
- **[Sysbench Results - Average (Binlog Enabled)](https://percona-lab-results.github.io/2026-ps-vs-mysql/enabled_binlog_sysbench_average.html)** - Performance comparison averaged across runs
- **[Sysbench Results - Individual Runs (Binlog Enabled)](https://percona-lab-results.github.io/2026-ps-vs-mysql/enabled_binlog_sysbench_individual.html)** - Detailed per-run results
- **[InnoDB Metrics Analyzer (Binlog Disabled)](https://percona-lab-results.github.io/2026-ps-vs-mysql/disabled_binlog_innodb_metrics_report.html)** - Interactive deep-dive into 319 InnoDB metrics
- **[InnoDB Metrics Analyzer (Binlog Enabled)](https://percona-lab-results.github.io/2026-ps-vs-mysql/enabled_binlog_innodb_metrics_report.html)** - Interactive deep-dive into 319 InnoDB metrics
- **[System Variables Comparison (Binlog Disabled)](https://percona-lab-results.github.io/2026-ps-vs-mysql/disabled_binlog_system_variables.html)** - Side-by-side comparison of system variables
- **[Status Variables Comparison (Binlog Disabled)](https://percona-lab-results.github.io/2026-ps-vs-mysql/disabled_binlog_status_variables.html)** - Side-by-side comparison of status variables
- **[System Variables Comparison (Binlog Enabled)](https://percona-lab-results.github.io/2026-ps-vs-mysql/enabled_binlog_system_variables.html)** - Side-by-side comparison of system variables
- **[Status Variables Comparison (Binlog Enabled)](https://percona-lab-results.github.io/2026-ps-vs-mysql/enabled_binlog_status_variables.html)** - Side-by-side comparison of status variables

## Reproducibility

**Supported OS**: Ubuntu 24.04 LTS only. The test scripts are currently tailored for Ubuntu 24.04 and require specific library compatibility patches.

### Prerequisites

Install required packages:

```bash
sudo apt install linux-tools-generic sysstat sysbench mysql-client dstat -y

# Ubuntu 24.04: Install libaio compatibility libraries
sudo apt install libaio1t64 libaio-dev
sudo ln -s /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1

# Install OpenSSL 1.1 for Percona Server (Ubuntu 24.04 compatibility)
wget http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2.23_amd64.deb
sudo dpkg -i libssl1.1_1.1.1f-1ubuntu2.23_amd64.deb
rm libssl1.1_1.1.1f-1ubuntu2.23_amd64.deb
```

**Note:** The user requires root access (`sudo`) as the scripts internally execute sudo commands for CPU governor, pt-pmp profiling, and telemetry collection.

### Server Binaries Setup

**Note:** These are generic Linux binary packages (not Ubuntu-specific builds). They require the library compatibility patches installed in Prerequisites.

1. **Download server binary tarballs**:

   - MySQL 8.4.8: `mysql-8.4.8-linux-glibc2.28-x86_64.tar.xz`
   ```
   wget https://downloads.mysql.com/archives/get/p/23/file/mysql-8.4.8-linux-glibc2.28-x86_64.tar.xz
   ```  
   - Percona Server 8.4.8-8: `Percona-Server-8.4.8-8-Linux.x86_64.glibc2.35.tar.gz`
   ```
   wget https://downloads.percona.com/downloads/Percona-Server-8.4/Percona-Server-8.4.8-8/binary/tarball/Percona-Server-8.4.8-8-Linux.x86_64.glibc2.35.tar.gz
   ```
   
2. **Configure server base directory**:
   
   Edit the `SERVERS_BASE` and `DATADIR_BASE` variable in both `run_all.sh` and `run_metrics.sh`:
   ```bash
   SERVERS_BASE="/path/to/your/servers"
   ```

3. **Unpack servers** into the configured directory:
   ```bash
   cd $SERVERS_BASE
   tar xf mysql-8.4.8-linux-glibc2.28-x86_64.tar.xz
   tar xf Percona-Server-8.4.8-8-Linux.x86_64.glibc2.35.tar.gz
   ```

   The resulting directory structure should be:
   ```
   $SERVERS_BASE/
   ├── mysql-8.4.8-linux-glibc2.28-x86_64/
   │   └── bin/mysqld
   └── Percona-Server-8.4.8-8-Linux.x86_64.glibc2.35/
       └── bin/mysqld
   ```

### Running Benchmarks

1. **Download Percona Toolkit utilities**:
   ```bash
   ./run_pt.sh
   ```

2. **Configure benchmark parameters** in `run_metrics.sh`:
   ```bash
   POOL_SIZES=(12)              # Buffer pool size in GB
   THREADS=(32 64)              # Thread counts to test
   TABLE_ROWS=5000000           # Rows per table
   DURATION=900                 # Test duration (seconds)
   ```

3. **Run all benchmarks** (both servers, with and without binlog):
   ```bash
   ./run_all.sh
   ```

   Or run individual benchmarks:

   ```bash
   # MySQL without binlog
   ./run_metrics.sh mysql 8.4.8 0 0

   # MySQL with binlog
   ./run_metrics.sh mysql 8.4.8 0 1

   # Percona Server without binlog
   ./run_metrics.sh percona-server 8.4.8-8 0 0

   # Percona Server with binlog
   ./run_metrics.sh percona-server 8.4.8-8 0 1
   ```

**Parameters**:
- `$1` - Database server name (`mysql`, `percona-server`)
- `$2` - Version tag (`8.4.8`, `8.4.8-8`)
- `$3` - Read-only mode (`0` = read-write, `1` = read-only)
- `$4` - Enable binary logging (`1` = enable, `0` = disable)

### Output Structure

Benchmark results are stored in separate directories:

```
benchmark_logs/              # Results with binlog disabled
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
│       ├── run1_Tier12G_RW_32th.dstat.txt
│       ├── run1_Tier12G_RW_32th.pt-pmp.txt
│       └── ... (runs 2-3, 64 threads)
└── percona-server/
    └── 8.4.8-8/
        └── ... (same structure)

benchmark_logs_binlog/       # Results with binlog enabled
├── mysql/
│   └── 8.4.8/
│       └── ... (same structure)
└── percona-server/
    └── 8.4.8-8/
        └── ... (same structure)
```

**Per-run files**:
- `.sysbench.txt` - Sysbench output with TPS/QPS metrics
- `.innodb.txt` - InnoDB metrics sampled every second
- `.iostat.txt`, `.vmstat.txt`, `.mpstat.txt`, `.dstat.txt` - System metrics
- `.pt-pmp.txt` - Stack trace profiling (starts at benchmark midpoint)

**Per-tier files**:
- `Tier12G.cnf.txt` - MySQL configuration used
- `Tier12G.vars.txt` - System variables (`SHOW VARIABLES`)
- `Tier12G.status.txt` - Status variables (`SHOW STATUS`)
- `Tier12G.errlog.txt` - MySQL error log
- `Tier12G-pt-mysql-summary.txt` - Percona Toolkit server summary

### Generating Reports

After running benchmarks, generate interactive reports:

```bash
# 1. Generate Sysbench performance reports
bash visuals/generate_both_reports.sh

# 2. Generate InnoDB metrics reports
python3 visuals/innodb_metrics_report.py benchmark_logs innodb_metrics_report.html
python3 visuals/innodb_metrics_report.py benchmark_logs_binlog innodb_metrics_report_binlog.html _binlog

# 3. Generate system/status variable comparisons
python3 visuals/generate_variable_comparisons.py benchmark_logs
python3 visuals/generate_variable_comparisons.py benchmark_logs_binlog "Binlog Enabled"

# 4. Generate index.html (navigation page for all reports)
python3 visuals/generate_index.py

# 5. Generate index-pmp.html (tree view of all pt-pmp stack trace files)
python3 visuals/generate_pmp_index.py

# 6. Generate off-CPU flame graphs from offcpu.txt files
bash visuals/generate_offcpu_flamegraphs.sh
```

**Off-CPU Flame Graph Notes**:
- Flame graphs visualize where threads spend time blocked (off-CPU)
- Wide towers ending in `futex_wait`, `pthread_mutex_lock`, or `__lll_lock_wait` indicate contention hotspots
- The stacks above these functions show which code path is experiencing contention
- Blue color scheme represents blocking/waiting time (cold = waiting)
- Open `.offcpu.svg` files in a web browser to view interactive flame graphs
```

**Generated files**:
- `index.html` - Navigation page with links to all reports
- `index-pmp.html` - Tree view index of all pt-pmp stack trace files
- `index-offcpu.html` - Gallery of all off-CPU flame graphs with auto-search links
- `*.offcpu.svg` - Off-CPU flame graphs (one per benchmark run)
- `disabled_binlog_sysbench_average.html` - Performance averages (binlog disabled)
- `disabled_binlog_sysbench_individual.html` - Individual run results (binlog disabled)
- `enabled_binlog_sysbench_average.html` - Performance averages (binlog enabled)
- `enabled_binlog_sysbench_individual.html` - Individual run results (binlog enabled)
- `disabled_binlog_innodb_metrics_report.html` - Interactive InnoDB metrics (binlog disabled)
- `enabled_binlog_innodb_metrics_report.html` - Interactive InnoDB metrics (binlog enabled)
- `disabled_binlog_system_variables.html` - System variables comparison (binlog disabled)
- `disabled_binlog_status_variables.html` - Status variables comparison (binlog disabled)
- `enabled_binlog_system_variables.html` - System variables comparison (binlog enabled)
- `enabled_binlog_status_variables.html` - Status variables comparison (binlog enabled)

## Benchmark Configuration

- **Hardware**: 2x Intel Xeon Gold 6230 (40 cores, 80 threads), 187.5 GB RAM
- **OS**: Ubuntu 24.04 LTS, Kernel 6.8.0-60-generic
- **Storage**: NVMe SSD (Make sure that the tests run on NVMe fast storage)
- **Workload**: Sysbench OLTP Read-Write
- **Tables**: 20 tables × 5M rows each
- **Buffer Pool**: 12 GB
- **Thread Counts**: 32, 64
- **Duration**: 15 minutes per test, 3 runs per configuration
- **Warmup**: 3 min read-only + 10 min read-write
- **Binary Logging**: Tested both enabled and disabled
- **Profiling**: pt-pmp stack traces collected at benchmark midpoint (7.5 min)

## Key Features

- **Direct mysqld execution** - Runs MySQL/Percona binaries directly on host (no Docker)
- **Clean data directories** - Each benchmark starts with fresh `mysqld --initialize-insecure`
- **Comprehensive telemetry** - iostat, vmstat, mpstat, dstat, InnoDB metrics, pt-pmp profiling
- **Binary logging comparison** - Tests both with and without binlog overhead
- **Interactive visualizations** - HTML reports with Chart.js for time-series analysis
- **Variable comparison** - Side-by-side system/status variable analysis

## Tools Used

- **Sysbench** - OLTP workload generator
- **Percona Toolkit** - pt-summary, pt-mysql-summary, pt-pmp (stack profiling)
- **sysstat** - iostat, mpstat for system metrics
- **dstat** - Combined system statistics
- **Chart.js** - Interactive time-series visualization

## Documentation

- **[FINDINGS.md](FINDINGS.md)** - Performance analysis and root cause investigation
