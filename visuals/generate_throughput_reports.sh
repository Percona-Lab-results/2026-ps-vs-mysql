#!/bin/bash
# Generate both average and individual run reports

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Generating averaged report..."
python3 visuals/throughput_report.py benchmark_logs disabled_binlog_sysbench_average.html "OLTP Read-Write disabled binlog" average
echo ""
echo "Generating individual runs report..."
python3 visuals/throughput_report.py benchmark_logs disabled_binlog_sysbench_individual.html "OLTP Read-Write disabled binlog" individual
echo ""

echo "Generating averaged report..."
python3 visuals/throughput_report.py benchmark_logs_binlog enabled_binlog_sysbench_average.html "OLTP Read-Write enabled binlog" average
echo ""
echo "Generating individual runs report..."
python3 visuals/throughput_report.py benchmark_logs_binlog enabled_binlog_sysbench_individual.html "OLTP Read-Write enabled binlog" individual
echo ""


echo "Done! Generated reports:"
echo "  - disabled_binlog_sysbench_average.html (runs averaged together)"
echo "  - disabled_binlog_sysbench_individual.html (each run shown separately)"
echo "  - enabled_binlog_sysbench_average.html (runs averaged together)"
echo "  - enabled_binlog_sysbench_individual.html (each run shown separately)"
