#!/bin/bash
# Test script for mutex metrics collector

DB_HOST="127.0.0.1"
DB_PORT="3306"
DB_USER="root"
DB_PASS="password"

echo "=== Testing InnoDB Mutex Metrics Collector ==="
echo ""

# Check if mysql client is available
if ! command -v mysql &> /dev/null; then
    echo "ERROR: mysql client not found"
    exit 1
fi
echo "✓ MySQL client found: $(mysql --version)"

# Check if MySQL server is running
if ! mysqladmin --host=$DB_HOST --port=$DB_PORT -u"$DB_USER" -p"$DB_PASS" ping 2>/dev/null; then
    echo "ERROR: MySQL server is not running or credentials are incorrect"
    exit 1
fi
echo "✓ MySQL server is accessible"

# Check for mutex data availability
echo ""
echo "Checking for InnoDB mutex data..."
MUTEX_COUNT=$(mysql -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -s \
    -e "SHOW ENGINE INNODB MUTEX" 2>/dev/null | wc -l)

if [ "$MUTEX_COUNT" -gt 0 ]; then
    echo "✓ Found $MUTEX_COUNT mutex entries"
else
    echo "WARNING: No mutex data found (may not be available in this MySQL version)"
fi

# Show sample mutex data
if [ "$MUTEX_COUNT" -gt 0 ]; then
    echo ""
    echo "Sample mutex data (first 5 entries):"
    mysql -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" \
        -e "SHOW ENGINE INNODB MUTEX" 2>/dev/null | head -6
fi

# Test the collector for 5 seconds
echo ""
echo "=== Testing collector for 5 seconds ==="
OUTPUT_FILE="/tmp/test_mutex_metrics.csv"
rm -f "$OUTPUT_FILE"

./collect_mutex_metrics.sh "$DB_HOST" "$DB_PORT" "$DB_USER" "$DB_PASS" "$OUTPUT_FILE" &
COLLECTOR_PID=$!

sleep 5

kill $COLLECTOR_PID 2>/dev/null
wait $COLLECTOR_PID 2>/dev/null

if [ -f "$OUTPUT_FILE" ]; then
    LINE_COUNT=$(wc -l < "$OUTPUT_FILE")
    echo "✓ Output file created: $OUTPUT_FILE"
    echo "  Lines collected: $LINE_COUNT (including header)"
    echo ""
    echo "First few lines:"
    head -10 "$OUTPUT_FILE"

    if [ "$LINE_COUNT" -gt 1 ]; then
        echo ""
        echo "Last few lines:"
        tail -5 "$OUTPUT_FILE"
        echo ""
        echo "Test completed successfully!"
    else
        echo ""
        echo "WARNING: Only header was written. No mutex data collected."
        echo "This may be normal if mutex data is not available in your MySQL version."
    fi
else
    echo "ERROR: Output file was not created"
    exit 1
fi
