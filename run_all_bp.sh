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

# Buffer pool instances to test for Percona Server
BP_INSTANCES_LIST=(4 8)

# Loop through both binlog configurations
for ENABLE_BINLOG in 0; do
  if [ "$ENABLE_BINLOG" == "1" ]; then
    BINLOG_MODE="with binlog"
  else
    BINLOG_MODE="without binlog"
  fi

  # Run MySQL 8.4.8 benchmarks (default buffer pool instance calculation)
  # echo ""
  # echo "=========================================================================="
  # echo "Starting MySQL 8.4.8 benchmarks ($BINLOG_MODE)"
  # echo "=========================================================================="
  # ./run_metrics.sh "mysql" "8.4.8" "$IS_READ_ONLY" "$ENABLE_BINLOG"

  # Run Percona Server 8.4.8-8 benchmarks with different buffer pool instance counts
  for BP_INSTANCES in "${BP_INSTANCES_LIST[@]}"; do
    echo ""
    echo "=========================================================================="
    echo "Starting Percona Server 8.4.8-8 benchmarks ($BINLOG_MODE, ${BP_INSTANCES} buffer pool instances)"
    echo "=========================================================================="
    ./run_metrics_bp.sh "percona-server" "8.4.8-8" "$IS_READ_ONLY" "$ENABLE_BINLOG" "$BP_INSTANCES"
  done
done


echo ""
echo "=========================================================================="
echo "All benchmarks completed!"
echo "=========================================================================="
echo ""
echo "Results saved to:"
echo "  - benchmark_logs/ (binlog disabled, MySQL default BP instances)"
echo "  - benchmark_logs_binlog/ (binlog enabled, MySQL default BP instances)"
echo "  - benchmark_logs_bp4/ (binlog disabled, Percona Server 4 BP instances)"
echo "  - benchmark_logs_binlog_bp4/ (binlog enabled, Percona Server 4 BP instances)"
echo "  - benchmark_logs_bp8/ (binlog disabled, Percona Server 8 BP instances)"
echo "  - benchmark_logs_binlog_bp8/ (binlog enabled, Percona Server 8 BP instances)"
echo ""
echo "Next steps:"
echo "  1. Generate reports for each configuration:"
echo "     bash visuals/generate_both_reports.sh"
echo "  2. Generate InnoDB metrics reports:"
echo "     python3 visuals/innodb_metrics_report.py benchmark_logs innodb_metrics_report.html"
echo "     python3 visuals/innodb_metrics_report.py benchmark_logs_binlog innodb_metrics_report_binlog.html _binlog"
echo "     python3 visuals/innodb_metrics_report.py benchmark_logs_bp4 innodb_metrics_report_bp4.html _bp4"
echo "     python3 visuals/innodb_metrics_report.py benchmark_logs_binlog_bp4 innodb_metrics_report_binlog_bp4.html _binlog_bp4"
echo "     (repeat for bp8 directories)"
echo "  3. Generate variable comparisons:"
echo "     python3 visuals/generate_variable_comparisons.py benchmark_logs"
echo "     python3 visuals/generate_variable_comparisons.py benchmark_logs_binlog \"Binlog Enabled\""
echo "     (repeat for bp4 and bp8 directories)"
echo "=========================================================================="