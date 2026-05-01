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
sudo apt install linux-tools-generic sysstat sysbench mysql-client dstat gdb -y

# Ubuntu 24.04: Install libaio compatibility libraries
sudo apt install libaio1t64 libaio-dev
sudo ln -s /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1

# Install OpenSSL 1.1 for Percona Server (Ubuntu 24.04 compatibility)
wget http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2.23_amd64.deb
sudo dpkg -i libssl1.1_1.1.1f-1ubuntu2.23_amd64.deb
rm libssl1.1_1.1.1f-1ubuntu2.23_amd64.deb
```

**Note:** The user requires root access (`sudo`) as the scripts internally execute sudo commands for CPU governor, pt-pmp profiling, and telemetry collection.

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
```

**Generated files**:
- `index.html` - Navigation page with links to all reports
- `sysbench_ps_mysql_average.html` - Performance averages across runs
- `sysbench_ps_mysql_individual.html` - Individual run results
- `innodb_metrics_report.html` - Interactive InnoDB metrics (no binlog)
- `innodb_metrics_report_binlog.html` - Interactive InnoDB metrics (with binlog)
- `system_variables_comparison.html` - System variables comparison (no binlog)
- `status_variables_comparison.html` - Status variables comparison (no binlog)
- `Binlog Enabled_system_variables.html` - System variables (with binlog)
- `Binlog Enabled_status_variables.html` - Status variables (with binlog)

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

## License

This benchmark suite and analysis is provided as-is for reproducibility and transparency.