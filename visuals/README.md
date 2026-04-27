# Visualization Scripts

This directory contains scripts for generating interactive HTML reports from benchmark data.

## Scripts

### throughput_report.py

Generates interactive Plotly charts for sysbench TPS/QPS data.

**Usage:**
```bash
python3 throughput_report.py [base_dir] [output_file] [test_type] [mode]
```

**Parameters:**
- `base_dir`: Directory containing benchmark logs (default: `benchmark_logs`)
- `output_file`: Output HTML file path (default: `sysbench_interactive_comparison.html`)
- `test_type`: Test description (default: `"OLTP Read-Write"`)
- `mode`: Display mode - `average` or `individual` (default: `average`)

**Modes:**
- **average**: Averages the 3 runs together, displays as single server line (e.g., "mysql 8.4.8")
- **individual**: Shows each run separately (e.g., "run1-mysql-8.4.8", "run2-mysql-8.4.8", "run3-mysql-8.4.8")

**Examples:**
```bash
# Generate with averaged runs (default)
python3 throughput_report.py

# Generate with individual runs
python3 throughput_report.py benchmark_logs sysbench_individual.html "OLTP Read-Write" individual

# Generate both versions
./generate_both_reports.sh
```

### innodb_metrics_report.py

Generates interactive table viewer for InnoDB metrics from *.innodb.txt files.

**Usage:**
```bash
python3 innodb_metrics_report.py [base_dir] [output_file]
```

**Features:**
- Multi-select for servers (e.g., mysql 8.4.8, percona-server 8.4.7-7)
- Multi-select for runs (Run 1, Run 2, Run 3)
- Dropdown to select any of 319+ InnoDB metrics
- Statistics panel showing avg/min/max values
- Time-series table view

**Example:**
```bash
python3 innodb_metrics_report.py
```

Output: `innodb_metrics_report.html`

### generate_both_reports.sh

Convenience script that generates both average and individual throughput reports in one command.

**Usage:**
```bash
./generate_both_reports.sh
```

**Output:**
- `sysbench_average.html` - Runs averaged together
- `sysbench_individual.html` - Each run shown separately

## File Structure

```
visuals/
├── throughput_report.py          # Main script for TPS/QPS charts
├── innodb_metrics_report.py      # InnoDB metrics analyzer
├── visual_template.html.in       # HTML template for throughput reports
├── generate_both_reports.sh      # Wrapper to generate both report types
└── README.md                     # This file
```

## Requirements

- Python 3.6+
- Standard library only (no external dependencies)
- Modern web browser with JavaScript enabled for viewing reports
