#!/usr/bin/env python3
"""
Reformat InnoDB metrics CSV to JavaScript variable arrays.

Input CSV format:
  timestamp_unix,timestamp_human,metric_name,count,count_reset,avg_count,status

Output format:
  var metric_name = [ [count, count_reset, avg_count], [count, count_reset, avg_count], ... ];
"""

import sys
import csv
from collections import defaultdict


def reformat_csv_to_js(input_file, output_file):
    """
    Convert long-format metrics CSV to JavaScript arrays.

    Args:
        input_file: Path to input CSV file
        output_file: Path to output JavaScript file
    """

    # Dictionary to store metrics data: metric_name -> list of [count, count_reset, avg_count]
    metrics_data = defaultdict(list)

    # Read CSV file
    try:
        with open(input_file, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                metric_name = row['metric_name']
                count = row['count']
                count_reset = row['count_reset']
                avg_count = row['avg_count']

                # Append data point for this metric
                metrics_data[metric_name].append([count, count_reset, avg_count])

        print(f"Read {sum(len(v) for v in metrics_data.values())} data points for {len(metrics_data)} metrics")

    except FileNotFoundError:
        print(f"ERROR: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"ERROR: Missing column in CSV: {e}", file=sys.stderr)
        sys.exit(1)

    # Write JavaScript file
    try:
        with open(output_file, 'w') as f:
            f.write("// InnoDB Metrics Data\n")
            f.write("// Auto-generated from metrics CSV\n")
            f.write(f"// Total metrics: {len(metrics_data)}\n")
            f.write(f"// Data points per metric: {len(next(iter(metrics_data.values()))) if metrics_data else 0}\n")
            f.write("\n")

            # Sort metrics by name for consistent output
            for metric_name in sorted(metrics_data.keys()):
                data_points = metrics_data[metric_name]

                # Start variable declaration
                f.write(f"var {metric_name} = [\n")

                # Write data points (one per line for readability)
                for i, point in enumerate(data_points):
                    count, count_reset, avg_count = point

                    # Format: [count, count_reset, avg_count]
                    if i < len(data_points) - 1:
                        f.write(f"  [{count}, {count_reset}, {avg_count}],\n")
                    else:
                        f.write(f"  [{count}, {count_reset}, {avg_count}]\n")

                f.write("];\n\n")

        print(f"Successfully wrote {len(metrics_data)} metric arrays to {output_file}")

    except IOError as e:
        print(f"ERROR: Failed to write output file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""

    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_csv> <output_js>", file=sys.stderr)
        print(f"Example: {sys.argv[0]} run1_Tier12G_RW_64th.lru_metrics.csv metrics.js", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    reformat_csv_to_js(input_file, output_file)


if __name__ == '__main__':
    main()
