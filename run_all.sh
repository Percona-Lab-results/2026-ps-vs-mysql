#!/bin/bash

# Check if required tools are installed
if ! command -v sysbench >/dev/null 2>&1; then
    echo "Error: sysbench is not installed." >&2
    exit 1
fi

if ! command -v iostat >/dev/null 2>&1; then
    echo "Error: sysstat (iostat) is not installed." >&2
    exit 1
fi

if ! command -v dstat >/dev/null 2>&1; then
    echo "Error: dstat is not installed." >&2
    exit 1
fi

# Check if server directories exist
SERVERS_BASE="/home/bogdan.degtyariov/mysql-nvme/servers"
if [ ! -d "$SERVERS_BASE" ]; then
    echo "Error: Server base directory not found: $SERVERS_BASE" >&2
    exit 1
fi

# Optional: Install prerequisites if not present
# sudo apt update
# sudo apt install linux-tools-generic sysstat sysbench dstat -y

./run_pt.sh

IS_READ_ONLY="0"
ENABLE_THREAD_POOL="1"
ENABLE_BINLOG="0"

  # Run MySQL 8.4.8 benchmarks
  # echo ""
  # echo "=========================================================================="
  # echo "Starting MySQL 8.4.8 benchmarks ($BINLOG_MODE)"
  # echo "=========================================================================="
  # ./run_metrics.sh "mysql" "8.4.8" "$IS_READ_ONLY" "$ENABLE_BINLOG"

  # Run Percona Server 8.4.8-8 benchmarks
  # echo ""
  # echo "=========================================================================="
  # echo "Starting Percona Server 8.4.8-8 benchmarks With Optimization ($BINLOG_MODE)"
  # echo "=========================================================================="
  # ./run_metrics.sh "percona-server-optimization" "8.4.8-8" "$IS_READ_ONLY" "$ENABLE_BINLOG" "$ENABLE_THREAD_POOL"
  # echo ""
  # echo "=========================================================================="
  # echo "Starting Percona Server 8.4.8-8 benchmarks Without Optimization ($BINLOG_MODE)"
  # echo "=========================================================================="
  # ./run_metrics.sh "percona-server-no-optimization" "8.4.8-8" "$IS_READ_ONLY" "$ENABLE_BINLOG" "$ENABLE_THREAD_POOL"


  for BP_INSTANCES in 2 8; do
    echo ""
    echo "=========================================================================="
    echo "Starting Percona Server 8.4.8-8 (innodb_buffer_pool_instances=${BP_INSTANCES})"
    echo "=========================================================================="
    ./run_metrics.sh --dbms-name="ps-lru-6007-bp${BP_INSTANCES}" --dbms-ver="8.4.8-8" --read-only="$IS_READ_ONLY" --binlog="$ENABLE_BINLOG" --thread-pool="$ENABLE_THREAD_POOL" --bp-instances="$BP_INSTANCES"
  done


echo ""
echo "=========================================================================="
echo "All benchmarks completed!"
echo "=========================================================================="
echo ""
echo "Results saved to:"
echo "  - benchmark_logs/ (binlog disabled)"
echo "  - benchmark_logs_binlog/ (binlog enabled)"
echo ""
echo "Next steps:"
echo "  1. Generate reports:"
echo "     bash visuals/generate_both_reports.sh"
echo "  2. Generate InnoDB metrics reports:"
echo "     python3 visuals/innodb_metrics_report.py benchmark_logs innodb_metrics_report.html"
echo "     python3 visuals/innodb_metrics_report.py benchmark_logs_binlog innodb_metrics_report_binlog.html _binlog"
echo "  3. Generate variable comparisons:"
echo "     python3 visuals/generate_variable_comparisons.py benchmark_logs"
echo "     python3 visuals/generate_variable_comparisons.py benchmark_logs_binlog \"Binlog Enabled\""
echo "=========================================================================="