#!/bin/bash
# InnoDB Metrics Collector (Bash-only version)
# Collects all enabled metrics from information_schema.INNODB_METRICS every 1 second

if [ $# -ne 5 ]; then
    echo "Usage: $0 <host> <port> <user> <password> <output_file>" >&2
    echo "Example: $0 127.0.0.1 3306 root password metrics.csv" >&2
    exit 1
fi

DB_HOST="$1"
DB_PORT="$2"
DB_USER="$3"
DB_PASS="$4"
OUTPUT_FILE="$5"

# MySQL client command with credentials
MYSQL_CMD="mysql -h $DB_HOST --port=$DB_PORT -u $DB_USER -p$DB_PASS -N -B"

# Check if MySQL is accessible
if ! $MYSQL_CMD -e "SELECT 1" 2>/dev/null >/dev/null; then
    echo "ERROR: Failed to connect to MySQL server" >&2
    exit 1
fi

# Write CSV header
echo "timestamp_unix,timestamp_human,metric_name,count,count_reset,avg_count,status" > "$OUTPUT_FILE"

echo "Recording all enabled InnoDB metrics to $OUTPUT_FILE" >&2
echo "Sampling every 1 second. Press Ctrl+C to stop." >&2

# Collection loop
while true; do
    # Get current timestamp
    TIMESTAMP_UNIX=$(date +%s.%3N)
    TIMESTAMP_HUMAN=$(date '+%Y-%m-%d %H:%M:%S.%3N')

    # Query for all enabled InnoDB metrics
    # Output format: name|count|count_reset|avg_count|status
    $MYSQL_CMD -e "
        SELECT
            name,
            IFNULL(count, 0),
            IFNULL(count_reset, 0),
            IFNULL(avg_count, 0),
            status
        FROM information_schema.INNODB_METRICS
        WHERE status = 'enabled'
        ORDER BY name
    " 2>/dev/null | while IFS=$'\t' read -r name count count_reset avg_count status; do
        # Write to CSV: timestamp_unix,timestamp_human,metric_name,count,count_reset,avg_count,status
        printf "%s,%s,%s,%s,%s,%.6f,%s\n" \
            "$TIMESTAMP_UNIX" \
            "$TIMESTAMP_HUMAN" \
            "$name" \
            "$count" \
            "$count_reset" \
            "$avg_count" \
            "$status" >> "$OUTPUT_FILE"
    done

    sleep 1
done
