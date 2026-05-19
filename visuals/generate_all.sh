#!/bin/bash

./visuals/mutex_metrics_report.py ./benchmark_logs/
./visuals/generate_innodb_metrics_report.sh
./visuals/generate_throughput_reports.sh
./visuals/generate_var_comparisons.sh
./visuals/generate_pmp_index.py
./visuals/generate_index.py