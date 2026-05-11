#!/bin/bash
# Test script for LRU metrics collector

DB_HOST="127.0.0.1"
DB_PORT="3306"
DB_USER="root"
DB_PASS="password"

echo "=== Testing InnoDB Metrics Collector (Bash Version) ==="
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

# Check for InnoDB metrics
echo ""
echo "Checking for InnoDB metrics..."
METRIC_COUNT=$(mysql -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -s \
    -e "SELECT COUNT(*) FROM information_schema.INNODB_METRICS" 2>/dev/null)

echo "✓ Found $METRIC_COUNT total InnoDB metrics"

# Check for buffer_LRU_% metrics specifically
LRU_COUNT=$(mysql -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -s \
    -e "SELECT COUNT(*) FROM information_schema.INNODB_METRICS WHERE name LIKE 'buffer_LRU_%'" 2>/dev/null)

if [ "$LRU_COUNT" -gt 0 ]; then
    echo "✓ Found $LRU_COUNT buffer_LRU_% metrics (LRU patch detected)"
else
    echo "ℹ No buffer_LRU_% metrics found (vanilla MySQL, no LRU patch)"
fi

# Enable all metrics
echo ""
echo "Enabling all InnoDB metrics..."
mysql -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" \
    -e "SET GLOBAL innodb_monitor_enable = 'all';" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ All metrics enabled"
else
    echo "WARNING: Failed to enable metrics"
fi

# Check enabled metrics
ENABLED_COUNT=$(mysql -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -s \
    -e "SELECT COUNT(*) FROM information_schema.INNODB_METRICS WHERE status = 'enabled'" 2>/dev/null)

echo "Enabled InnoDB metrics: $ENABLED_COUNT"

# Show some sample enabled metrics
if [ "$ENABLED_COUNT" -gt 0 ]; then
    echo ""
    echo "Sample enabled metrics (first 10):"
    mysql -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -s \
        -e "SELECT name FROM information_schema.INNODB_METRICS WHERE status = 'enabled' ORDER BY name LIMIT 10" 2>/dev/null

    if [ "$LRU_COUNT" -gt 0 ]; then
        echo ""
        echo "Buffer LRU metrics (all):"
        mysql -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -s \
            -e "SELECT name FROM information_schema.INNODB_METRICS WHERE name LIKE 'buffer_LRU_%' AND status = 'enabled' ORDER BY name" 2>/dev/null
    fi
fi

# Test the collector for 5 seconds
echo ""
echo "=== Testing collector for 5 seconds ==="
OUTPUT_FILE="/tmp/test_lru_metrics.csv"
rm -f "$OUTPUT_FILE"

./collect_lru_metrics.sh "$DB_HOST" "$DB_PORT" "$DB_USER" "$DB_PASS" "$OUTPUT_FILE" &
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
    echo ""
    echo "Test completed successfully!"
else
    echo "ERROR: Output file was not created"
    exit 1
fi
