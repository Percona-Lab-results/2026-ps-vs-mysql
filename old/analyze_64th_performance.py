#!/usr/bin/env python3
"""
Analyze why Percona Server is slower than MySQL at 64 threads
"""

import csv
from pathlib import Path
import statistics

def analyze_metric(mysql_file, ps_file, metric_name):
    """Compare a specific metric between MySQL and Percona Server"""

    def read_metric(file_path, metric):
        values = []
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if metric in row and row[metric]:
                    try:
                        values.append(float(row[metric]))
                    except ValueError:
                        pass
        return values

    mysql_vals = read_metric(mysql_file, metric_name)
    ps_vals = read_metric(ps_file, metric_name)

    if not mysql_vals or not ps_vals:
        return None

    mysql_avg = statistics.mean(mysql_vals)
    ps_avg = statistics.mean(ps_vals)

    # Calculate difference
    diff_pct = ((ps_avg - mysql_avg) / mysql_avg * 100) if mysql_avg > 0 else 0

    return {
        'metric': metric_name,
        'mysql_avg': mysql_avg,
        'ps_avg': ps_avg,
        'diff_pct': diff_pct,
        'mysql_max': max(mysql_vals),
        'ps_max': max(ps_vals),
        'mysql_min': min(mysql_vals),
        'ps_min': min(ps_vals)
    }

def main():
    base = Path("benchmark_logs")

    # Average across all 3 runs
    mysql_files = [
        base / "mysql/8.4.8/run1_Tier12G_RW_64th.innodb.txt",
        base / "mysql/8.4.8/run2_Tier12G_RW_64th.innodb.txt",
        base / "mysql/8.4.8/run3_Tier12G_RW_64th.innodb.txt"
    ]

    ps_files = [
        base / "percona-server/8.4.8-8/run1_Tier12G_RW_64th.innodb.txt",
        base / "percona-server/8.4.8-8/run2_Tier12G_RW_64th.innodb.txt",
        base / "percona-server/8.4.8-8/run3_Tier12G_RW_64th.innodb.txt"
    ]

    # Key metrics to analyze
    key_metrics = [
        # Lock contention
        'lock_row_lock_waits',
        'lock_row_lock_time',
        'lock_deadlocks',
        'lock_row_lock_current_waits',
        'lock_timeouts',

        # RW lock contention
        'innodb_rwlock_x_os_waits',
        'innodb_rwlock_s_os_waits',
        'innodb_rwlock_x_spin_waits',
        'innodb_rwlock_s_spin_waits',

        # Buffer pool pressure
        'buffer_pool_wait_free',
        'buffer_pool_reads',
        'buffer_pool_read_requests',
        'buffer_pool_pages_dirty',

        # Log system
        'log_waits',
        'log_on_flush_waits',
        'log_on_write_waits',
        'log_on_buffer_space_waits',

        # CPU time
        'cpu_utime_abs',
        'cpu_stime_abs',

        # Transactions
        'trx_on_log_waits',
        'trx_rollbacks'
    ]

    print("=" * 80)
    print("PERFORMANCE ANALYSIS: MySQL 8.4.8 vs Percona Server 8.4.8-8 @ 64 threads")
    print("=" * 80)
    print()

    # Analyze first run for each
    mysql_file = mysql_files[0]
    ps_file = ps_files[0]

    print(f"Analyzing: {mysql_file.name} vs {ps_file.name}")
    print()

    significant_diffs = []

    for metric in key_metrics:
        result = analyze_metric(mysql_file, ps_file, metric)
        if result and abs(result['diff_pct']) > 5:  # More than 5% difference
            significant_diffs.append(result)

    # Sort by absolute difference
    significant_diffs.sort(key=lambda x: abs(x['diff_pct']), reverse=True)

    print("\nSIGNIFICANT DIFFERENCES (>5%):")
    print("-" * 80)
    print(f"{'Metric':<40} {'MySQL Avg':>15} {'PS Avg':>15} {'Diff %':>10}")
    print("-" * 80)

    for r in significant_diffs[:20]:  # Top 20
        print(f"{r['metric']:<40} {r['mysql_avg']:>15,.2f} {r['ps_avg']:>15,.2f} {r['diff_pct']:>9,.1f}%")

    print()
    print("\nKEY FINDINGS:")
    print("-" * 80)

    # Analyze specific patterns
    for r in significant_diffs:
        if 'lock' in r['metric'].lower() and r['ps_avg'] > r['mysql_avg']:
            print(f"⚠️  LOCK CONTENTION: {r['metric']}")
            print(f"   PS has {r['diff_pct']:.1f}% MORE lock contention than MySQL")
            print(f"   MySQL: {r['mysql_avg']:,.0f}, PS: {r['ps_avg']:,.0f}")
            print()

        elif 'wait' in r['metric'].lower() and r['ps_avg'] > r['mysql_avg']:
            print(f"⚠️  WAIT EVENT: {r['metric']}")
            print(f"   PS has {r['diff_pct']:.1f}% MORE waits than MySQL")
            print(f"   MySQL: {r['mysql_avg']:,.0f}, PS: {r['ps_avg']:,.0f}")
            print()

if __name__ == '__main__':
    main()
