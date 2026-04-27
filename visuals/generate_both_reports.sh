#!/bin/bash
# Generate both average and individual run reports

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Generating averaged report..."
python3 visuals/throughput_report.py benchmark_logs sysbench_ps_mysql_average.html "OLTP Read-Write" average

echo ""
echo "Generating individual runs report..."
python3 visuals/throughput_report.py benchmark_logs sysbench_ps_mysql_individual.html "OLTP Read-Write" individual

echo ""
echo "Done! Generated reports:"
echo "  - sysbench_average.html (runs averaged together)"
echo "  - sysbench_individual.html (each run shown separately)"
