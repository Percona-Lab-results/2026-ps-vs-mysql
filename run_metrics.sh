#!/bin/bash
# MySQL/Percona Server Benchmark Script with Metrics Collection
#
# Usage: ./run_metrics.sh --dbms-name=<name> --dbms-ver=<version> --server-dir=<path> --read-only=yes|no --binlog=yes|no [--thread-pool=yes|no] [--bp-instances=<n>] [--base-version=yes|no] [--lru-scan-depth=<n>]
#
# Arguments:
#   --dbms-name      Name (e.g., "percona-server-no-optimization", "percona-server-optimization", "mysql")
#   --dbms-ver       Version string (e.g., "8.4.8-8", "9.7.0")
#   --server-dir     Path to the unpacked server directory (must contain bin/mysqld, bin/mysql, bin/mysqladmin)
#   --read-only      yes for read-only tests, no for read-write tests
#   --binlog         yes to enable binary logging, no to disable
#   --thread-pool    (Optional) yes to enable thread pool, no to disable (default: no)
#   --bp-instances   (Optional) override innodb_buffer_pool_instances; if omitted, computed from buffer pool size
#   --base-version   (Optional) yes to omit PR-6007 LRU tuning knobs, no to include them (default: no)
#   --lru-scan-depth (Optional) set innodb_lru_scan_depth; if 0 or omitted, the option is not set
#   --lru-threads    (Optional) on|off to set innodb_lru_threads; if omitted, the option is not set
#
# Examples:
#   ./run_metrics.sh --dbms-name=percona-server --dbms-ver=8.4.8-8 --read-only=no --binlog=no
#   ./run_metrics.sh --dbms-name=percona-server --dbms-ver=8.4.8-8 --read-only=no --binlog=yes
#   ./run_metrics.sh --dbms-name=percona-server --dbms-ver=8.4.8-8 --read-only=no --binlog=no --thread-pool=yes
#   ./run_metrics.sh --dbms-name=percona-server --dbms-ver=8.4.8-8 --read-only=no --binlog=no --bp-instances=4
#   ./run_metrics.sh --dbms-name=mysql --dbms-ver=9.7.0 --read-only=yes --binlog=no

# --- VARIABLES ---
DB_HOST="127.0.0.1"
DB_USER="root"
DB_PASS="password"
DB_DATABASE="sbtest"
DB_PORT="3306"

# Server locations
DATADIR_BASE="/home/bogdan.degtyariov/servers/data"

POOL_SIZES=(32 2)      # The 3 Tiers (GB)
#POOL_SIZES=(12)

#THREADS=(1 4 16 32 64 128 256 512 1024)
THREADS=(32 64 128 256 512)

# --- DEBUG SETTINGS ---
TABLE_ROWS=5000000
WARMUP_RO_TIME=180
WARMUP_RW_TIME=600
DURATION=900

# TABLE_ROWS=50000
# WARMUP_RO_TIME=10
# WARMUP_RW_TIME=10
# DURATION=15

usage() {
    echo "Usage: $0 --dbms-name=<name> --dbms-ver=<version> --server-dir=<path> --read-only=yes|no --binlog=yes|no [--thread-pool=yes|no] [--bp-instances=<n>] [--base-version=yes|no] [--lru-scan-depth=<n>] [--lru-threads=on|off]" >&2
    exit 1
}

yesno_to_bool() {
    case "${1,,}" in
        yes|y|1|true)  echo 1 ;;
        no|n|0|false)  echo 0 ;;
        *) echo "ERROR: invalid yes/no value for $2: '$1'" >&2; exit 1 ;;
    esac
}

DBMS_NAME=""
DBMS_VER=""
SERVER_DIR_ARG=""
READ_ONLY_ARG=""
BINLOG_ARG=""
THREAD_POOL_ARG="no"
BP_INSTANCES_ARG=""
BASE_VERSION_ARG="no"
LRU_SCAN_DEPTH_ARG="0"
LRU_THREADS_ARG=""

for arg in "$@"; do
    case "$arg" in
        --dbms-name=*)       DBMS_NAME="${arg#*=}" ;;
        --dbms-ver=*)        DBMS_VER="${arg#*=}" ;;
        --server-dir=*)      SERVER_DIR_ARG="${arg#*=}" ;;
        --read-only=*)       READ_ONLY_ARG="${arg#*=}" ;;
        --binlog=*)          BINLOG_ARG="${arg#*=}" ;;
        --thread-pool=*)     THREAD_POOL_ARG="${arg#*=}" ;;
        --bp-instances=*)    BP_INSTANCES_ARG="${arg#*=}" ;;
        --base-version=*)    BASE_VERSION_ARG="${arg#*=}" ;;
        --lru-scan-depth=*)  LRU_SCAN_DEPTH_ARG="${arg#*=}" ;;
        --lru-threads=*)     LRU_THREADS_ARG="${arg#*=}" ;;
        -h|--help)           usage ;;
        *) echo "ERROR: unknown argument: $arg" >&2; usage ;;
    esac
done

[ -z "$DBMS_NAME" ]      && { echo "ERROR: --dbms-name is required" >&2; usage; }
[ -z "$DBMS_VER" ]       && { echo "ERROR: --dbms-ver is required" >&2; usage; }
[ -z "$SERVER_DIR_ARG" ] && { echo "ERROR: --server-dir is required" >&2; usage; }
[ -z "$READ_ONLY_ARG" ]  && { echo "ERROR: --read-only is required" >&2; usage; }
[ -z "$BINLOG_ARG" ]     && { echo "ERROR: --binlog is required" >&2; usage; }

IS_READ_ONLY=$(yesno_to_bool "$READ_ONLY_ARG" --read-only)
ENABLE_BINLOG=$(yesno_to_bool "$BINLOG_ARG" --binlog)
ENABLE_THREAD_POOL=$(yesno_to_bool "$THREAD_POOL_ARG" --thread-pool)
BASE_VERSION=$(yesno_to_bool "$BASE_VERSION_ARG" --base-version)

if [ -n "$BP_INSTANCES_ARG" ]; then
    if ! [[ "$BP_INSTANCES_ARG" =~ ^[1-9][0-9]*$ ]]; then
        echo "ERROR: --bp-instances must be a positive integer (got: '$BP_INSTANCES_ARG')" >&2
        exit 1
    fi
fi
BP_INSTANCES_OVERRIDE="$BP_INSTANCES_ARG"

if ! [[ "$LRU_SCAN_DEPTH_ARG" =~ ^(0|[1-9][0-9]*)$ ]]; then
    echo "ERROR: --lru-scan-depth must be a non-negative integer (got: '$LRU_SCAN_DEPTH_ARG')" >&2
    exit 1
fi
LRU_SCAN_DEPTH="$LRU_SCAN_DEPTH_ARG"

LRU_THREADS=""
if [ -n "$LRU_THREADS_ARG" ]; then
    case "${LRU_THREADS_ARG,,}" in
        on|yes|y|1|true)   LRU_THREADS="ON" ;;
        off|no|n|0|false)  LRU_THREADS="OFF" ;;
        *) echo "ERROR: --lru-threads must be on|off (got: '$LRU_THREADS_ARG')" >&2; exit 1 ;;
    esac
fi

sudo cpupower frequency-set -g performance > /dev/null

echo "============= Running benchmarks for ${DBMS_NAME}:${DBMS_VER} ============="
echo "Thread pool: $([ "$ENABLE_THREAD_POOL" -eq 1 ] && echo "ENABLED" || echo "DISABLED")"

# Server directory and binaries (passed in via --server-dir)
SERVER_DIR="$SERVER_DIR_ARG"
ADMIN_TOOL="mysqladmin"

if [ ! -d "$SERVER_DIR" ]; then
    echo "ERROR: Server directory not found: $SERVER_DIR"
    exit 1
fi

MYSQLD="${SERVER_DIR}/bin/mysqld"
MYSQL_CLIENT="${SERVER_DIR}/bin/mysql"
MYSQLADMIN="${SERVER_DIR}/bin/${ADMIN_TOOL}"

if [ ! -x "$MYSQLD" ]; then
    echo "ERROR: mysqld not found or not executable: $MYSQLD"
    exit 1
fi

CONFIG_DIR="$HOME/configs"
CONFIG_NAME="my.cnf"
CONFIG_PATH="${CONFIG_DIR}/${CONFIG_NAME}"

# PID file for server management
PID_FILE="/tmp/mysql_benchmark.pid"

server_wait() {
  echo "Waiting for DB Server to initialize..."
  sleep 5

  # Check if mysqld process is running
  if [ -f "$PID_FILE" ]; then
    local pid=$(cat "$PID_FILE")
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "Fatal error: mysqld process is not running (PID: $pid). Terminating script."
      exit 1
    fi
  else
    echo "Fatal error: PID file not found. Terminating script."
    exit 1
  fi

  until "$MYSQLADMIN" ping --host=$DB_HOST --port=$DB_PORT -u"$DB_USER" -p"$DB_PASS" 2>/dev/null; do
    echo "Waiting for server to respond..."
    sleep 2
  done
  echo "Server is ready!"
}

stop_server() {
  echo "Stopping MySQL server..."
  if [ -f "$PID_FILE" ]; then
    local pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      "$MYSQLADMIN" --host=$DB_HOST --port=$DB_PORT -u"$DB_USER" -p"$DB_PASS" shutdown 2>/dev/null
      sleep 3
      # Force kill if still running
      if kill -0 "$pid" 2>/dev/null; then
        echo "Force killing mysqld (PID: $pid)"
        kill -9 "$pid" 2>/dev/null
      fi
    fi
    rm -f "$PID_FILE"
  fi
  sleep 2
}

start_server() {
  local DATADIR=$1
  local CONFIG=$2

  echo "Starting MySQL server..."
  echo "  Server: $MYSQLD"
  echo "  Datadir: $DATADIR"
  echo "  Config: $CONFIG"
  echo "  Command: $MYSQLD --defaults-file=$CONFIG --datadir=$DATADIR --pid-file=$PID_FILE --user=$(whoami)"

  # Start mysqld in background
  "$MYSQLD" --defaults-file="$CONFIG" --datadir="$DATADIR" --pid-file="$PID_FILE" \
    --user=$(whoami) &

  # Wait a moment for PID file to be created
  sleep 15

  cat $PID_FILE

  if [ ! -f "$PID_FILE" ]; then
    echo "ERROR: Failed to start mysqld (PID file not created)"
    exit 1
  fi

  echo "mysqld started with PID: $(cat $PID_FILE)"
}

initialize_datadir() {
  local DATADIR=$1

  echo "Initializing clean data directory: $DATADIR"

  # Remove old datadir if exists
  if [ -d "$DATADIR" ]; then
    echo "Removing old datadir..."
    rm -rf "$DATADIR"
  fi

  # Create fresh datadir
  mkdir -p "$DATADIR"

  # Initialize MySQL data directory
  echo "Running mysqld --initialize-insecure..."
  "$MYSQLD" --initialize-insecure --datadir="$DATADIR" --user=$(whoami)

  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to initialize data directory"
    exit 1
  fi

  echo "Data directory initialized successfully"
}

# Make sure no server is running at this stage
stop_server

# --- DETECT VERSION & VENDOR ---
echo "Starting server to detect version..."

if [[ "$IS_READ_ONLY" == "1" ]]; then
    BENCH_DIR="./benchmark_logs_read_only"
elif [[ "$ENABLE_BINLOG" == "1" ]]; then
    BENCH_DIR="./benchmark_logs_binlog"
else
    BENCH_DIR="./benchmark_logs"
fi

echo "Removing old config if exists: $CONFIG_PATH"
rm -rf "$CONFIG_PATH"

# Create temporary minimal config for version detection
TMP_DATADIR="${DATADIR_BASE}/tmp_init"
initialize_datadir "$TMP_DATADIR"

# Create minimal config
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_PATH" << EOF
[mysqld]
port=$DB_PORT
socket=/tmp/mysql_benchmark.sock
datadir=$TMP_DATADIR
EOF

start_server "$TMP_DATADIR" "$CONFIG_PATH"
server_wait

# Set root password and grant TCP/IP access (use socket for initial connection)
"$MYSQLADMIN" --socket=/tmp/mysql_benchmark.sock -u"$DB_USER" password "$DB_PASS" 2>/dev/null

# Grant access from 127.0.0.1
"$MYSQL_CLIENT" --socket=/tmp/mysql_benchmark.sock -u"$DB_USER" -p"$DB_PASS" -e "CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY '$DB_PASS'; GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION; FLUSH PRIVILEGES;" 2>/dev/null

RAW_VERSION=$("$MYSQL_CLIENT" -h $DB_HOST --port=$DB_PORT -u $DB_USER -p$DB_PASS -N -e "SELECT VERSION();" 2>/dev/null)
MAJOR_VER=$(echo $RAW_VERSION | cut -d'.' -f1,2)

LOG_DIR="${BENCH_DIR}/${DBMS_NAME}/${RAW_VERSION}"
mkdir -p "$LOG_DIR"

echo "Detected: $RAW_VERSION (Major: $MAJOR_VER)"
[ "$ENABLE_BINLOG" == "1" ] && echo "Binary logging: ENABLED"
[ "$ENABLE_BINLOG" != "1" ] && echo "Binary logging: DISABLED"
[ "$ENABLE_THREAD_POOL" == "1" ] && echo "Thread pool: ENABLED"
[ "$ENABLE_THREAD_POOL" != "1" ] && echo "Thread pool: DISABLED"

stop_server
rm -rf "$TMP_DATADIR"

check_innodb_buffer() {
    local EXPECTED_GB=$1
    echo ">>> Verifying InnoDB Buffer Pool: ${EXPECTED_GB}GB..."

    local ACTUAL_BYTES=$("$MYSQL_CLIENT" -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -s -e "SELECT @@innodb_buffer_pool_size;")
    local ACTUAL_GB=$(( ACTUAL_BYTES / 1024 / 1024 / 1024 ))

    if [ "$ACTUAL_GB" -ne "$EXPECTED_GB" ]; then
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "CRITICAL ERROR: Buffer Pool is ${ACTUAL_GB}GB (Expected ${EXPECTED_GB}GB)"
        echo "Aborting entire benchmark script immediately."
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        exit 1
    fi

    echo "Verification successful: Buffer Pool is ${ACTUAL_GB}GB."
}

check_vars_status() {
    local FILE_PREFIX=$1
    echo ">>> Capturing server variables and status..."

    "$MYSQL_CLIENT" -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -e "SHOW VARIABLES;" > "${FILE_PREFIX}.vars.txt" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "    Variables saved to: ${FILE_PREFIX}.vars.txt"
    else
        echo "    ERROR: Failed to capture variables"
    fi

    "$MYSQL_CLIENT" -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -e "SHOW STATUS;" > "${FILE_PREFIX}.status.txt" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "    Status saved to: ${FILE_PREFIX}.status.txt"
    else
        echo "    ERROR: Failed to capture status"
    fi
}

run_mysql_summary() {
    local FILE_PREFIX=$1
    ./pt-mysql-summary --host="$DB_HOST" --port=$DB_PORT --user="$DB_USER" --password="$DB_PASS" > "${FILE_PREFIX}-pt-mysql-summary.txt"
    if [ $? -eq 0 ]; then
        echo "    Server summary saved to: ${FILE_PREFIX}-pt-mysql-summary.txt"
    else
        echo "    ERROR: Failed to server summary with pt-mysql-summary"
    fi
}

# --- CONFIGURATION GENERATOR ---
generate_config() {
    local SIZE=$1
    local DATADIR=$2
    local CFG="/tmp/$CONFIG_NAME"
    rm -f "$CFG"

    # 1. Start Base Config
    echo "[mysqld]" > "$CFG"
    echo "port                            = $DB_PORT" >> "$CFG"
    echo "socket                          = /tmp/mysql_benchmark.sock" >> "$CFG"
    echo "datadir                         = $DATADIR" >> "$CFG"
    echo "log_error_verbosity             = 3" >> "$CFG"
    echo "log_error                       = ${DATADIR}/mysql-error.log" >> "$CFG"

    echo "# --- General -------------------------------------------------------------------" >> "$CFG"
    echo "user                            = $(whoami)" >> "$CFG"
    echo "bind-address                    = 0.0.0.0" >> "$CFG"
    echo "skip-name-resolve               = ON" >> "$CFG"
    #echo "performance_schema              = OFF" >> "$CFG"
    echo "" >> "$CFG"

    echo "# --- Connection & Threading ----------------------------------------------------" >> "$CFG"
    echo "max_connections                 = 2000" >> "$CFG"
    echo "max_connect_errors              = 1000000" >> "$CFG"
    echo "max_prepared_stmt_count         = 1000000" >> "$CFG"
    echo "thread_stack                    = 512K" >> "$CFG"
    echo "thread_cache_size               = 256" >> "$CFG"
    echo "back_log                        = 4096" >> "$CFG"
    echo "wait_timeout                    = 300" >> "$CFG"
    echo "interactive_timeout             = 300" >> "$CFG"
    echo "connect_timeout                 = 60" >> "$CFG"
    echo "" >> "$CFG"

    if [ "$ENABLE_THREAD_POOL" -eq 1 ]; then
        echo "" >> "$CFG"
        echo "# --- Thread Pool (Percona Server) ------------------------------------------" >> "$CFG"
        echo "thread_handling                 = pool-of-threads" >> "$CFG"
        echo "thread_pool_size                = 80                # match physical core count" >> "$CFG"
        echo "thread_pool_max_threads         = 2000" >> "$CFG"
        echo "thread_pool_oversubscribe       = 3" >> "$CFG"
        echo "" >> "$CFG"
    fi

    echo "# --- InnoDB - Buffer pool Tier -------------------------------------------------" >> "$CFG"
    echo "innodb_buffer_pool_size         = ${SIZE}G" >> "$CFG"
    echo "innodb_buffer_pool_load_at_startup  = OFF" >> "$CFG"
    echo "innodb_buffer_pool_dump_at_shutdown = OFF" >> "$CFG"

    echo "" >> "$CFG"
    echo "# --- InnoDB – I/O (NVMe can saturate many threads) ----------------------------" >> "$CFG"
    echo "innodb_io_capacity              = 10000" >> "$CFG"
    echo "innodb_io_capacity_max          = 20000" >> "$CFG"
    echo "innodb_read_io_threads          = 16" >> "$CFG"
    echo "innodb_write_io_threads         = 16" >> "$CFG"
    echo "innodb_use_native_aio           = ON" >> "$CFG"
    echo "" >> "$CFG"

    echo "# --- InnoDB – Log / Durability -------------------------------------------------" >> "$CFG"
    echo "innodb_log_buffer_size          = 256M" >> "$CFG"
    echo "innodb_flush_log_at_trx_commit  = 1          # full ACID; use 2 for ~10 % more speed" >> "$CFG"
    echo "innodb_doublewrite              = ON" >> "$CFG"
    echo "" >> "$CFG"

    echo "# --- InnoDB – Concurrency & OLTP Tuning ---------------------------------------" >> "$CFG"
    echo "innodb_stats_on_metadata        = OFF" >> "$CFG"
    echo "innodb_open_files               = 65536" >> "$CFG"
    echo "innodb_lock_wait_timeout        = 50" >> "$CFG"
    echo "innodb_rollback_on_timeout      = ON" >> "$CFG"
    echo "" >> "$CFG"

    echo "# --- Per-Session Buffers (keep modest; many connections × this = RAM) ----------" >> "$CFG"
    echo "sort_buffer_size                = 4M" >> "$CFG"
    echo "join_buffer_size                = 4M" >> "$CFG"
    echo "read_buffer_size                = 2M" >> "$CFG"
    echo "read_rnd_buffer_size            = 4M" >> "$CFG"
    echo "tmp_table_size                  = 256M" >> "$CFG"
    echo "max_heap_table_size             = 256M" >> "$CFG"
    echo "" >> "$CFG"

    echo "# --- Table & File Handles ------------------------------------------------------" >> "$CFG"
    echo "table_open_cache                = 65536" >> "$CFG"
    echo "table_definition_cache          = 65536" >> "$CFG"
    echo "open_files_limit                = 1000000" >> "$CFG"
    echo "table_open_cache_instances      = 64" >> "$CFG"
    echo "" >> "$CFG"

    echo "# --- Binary Log ----------------------------------------------------------------" >> "$CFG"
    if [ "$ENABLE_BINLOG" == "1" ]; then
        echo "# Binary logging ENABLED" >> "$CFG"
        echo "server_id                       = 1" >> "$CFG"
        echo "log_bin                         = ${DATADIR}/mysql-bin" >> "$CFG"
        echo "binlog_format                   = ROW" >> "$CFG"
        echo "binlog_row_image                = MINIMAL" >> "$CFG"
        echo "sync_binlog                     = 1" >> "$CFG"
        echo "binlog_cache_size               = 4M" >> "$CFG"
        echo "max_binlog_size                 = 512M" >> "$CFG"
    else
        echo "# Binary logging DISABLED for benchmarking" >> "$CFG"
        echo "disable_log_bin                 = ON" >> "$CFG"
    fi
    echo "" >> "$CFG"

    echo "# --- Slow Query Log ------------------------------------------------------------" >> "$CFG"
    echo "slow_query_log                  = ON" >> "$CFG"
    echo "slow_query_log_file             = ${DATADIR}/slow.log" >> "$CFG"
    echo "long_query_time                 = 1" >> "$CFG"
    echo "log_queries_not_using_indexes   = OFF" >> "$CFG"
    echo "min_examined_row_limit          = 1000" >> "$CFG"
    echo "" >> "$CFG"

    echo "# --- Character Set -------------------------------------------------------------" >> "$CFG"
    echo "character_set_server            = utf8mb4" >> "$CFG"
    echo "collation_server                = utf8mb4_unicode_ci" >> "$CFG"
    echo "" >> "$CFG"

    echo "# --- Misc ----------------------------------------------------------------------" >> "$CFG"
    echo "max_allowed_packet              = 64M" >> "$CFG"
    echo "bulk_insert_buffer_size         = 256M" >> "$CFG"
    echo "myisam_sort_buffer_size         = 128M" >> "$CFG"
    echo "key_buffer_size                 = 64M        # MyISAM only; keep small for OLTP" >> "$CFG"
    echo "" >> "$CFG"

    echo "# --- Version specific settings -------------------------------------------------" >> "$CFG"

    # 3. VERSION SPECIFIC LOGIC
    if [ -n "$BP_INSTANCES_OVERRIDE" ]; then
        INSTANCES="$BP_INSTANCES_OVERRIDE"
    else
        INSTANCES=$(( SIZE / 5 ))
        [ "$INSTANCES" -lt 1 ] && INSTANCES=1
        [ "$INSTANCES" -gt 8 ] && INSTANCES=8
    fi

    # MySQL 8.4+ / 9.x
    echo "innodb_redo_log_capacity = 4G" >> "$CFG"
    echo "innodb_change_buffering = none" >> "$CFG"
    echo "innodb_flush_method = O_DIRECT" >> "$CFG"
    echo "innodb_buffer_pool_instances    = $INSTANCES" >> "$CFG"

    # if [ "$BASE_VERSION" -ne 1 ]; then
    #     # From PR-6007
    #     # This is for deferred make-young promotion
    #     # 8 BP instances -> 256; 2 BP instances -> 64; otherwise default to 256
    #     if [ "$INSTANCES" -eq 8 ]; then
    #         LRU_MAKE_YOUNG_DRAIN_THRESHOLD=256
    #         SINGLE_PAGE_FLUSH_MAX=16
    #         # echo "innodb_lru_flush_batch_size = 1" >> "$CFG"
    #     elif [ "$INSTANCES" -eq 2 ]; then
    #         LRU_MAKE_YOUNG_DRAIN_THRESHOLD=64
    #         SINGLE_PAGE_FLUSH_MAX=4
    #     else
    #         LRU_MAKE_YOUNG_DRAIN_THRESHOLD=256
    #         SINGLE_PAGE_FLUSH_MAX=16
    #     fi
    #     echo "innodb_lru_make_young_drain_threshold = $LRU_MAKE_YOUNG_DRAIN_THRESHOLD" >> "$CFG"
    #     # echo "innodb_single_page_flush_max_concurrent = $SINGLE_PAGE_FLUSH_MAX" >> "$CFG"
    # fi

    if [ "$LRU_SCAN_DEPTH" -ne 0 ]; then
        echo "innodb_lru_scan_depth = $LRU_SCAN_DEPTH" >> "$CFG"
    fi

    if [ -n "$LRU_THREADS" ]; then
        echo "innodb_lru_threads = $LRU_THREADS" >> "$CFG"
    fi

    # Percona Server specific settings
    # if [[ "$DBMS_NAME" == "percona-server" ]]; then
    #     echo "innodb_empty_free_list_algorithm = backoff" >> "$CFG"
    # fi

    # 4. Deploy Config
    mkdir -p "$CONFIG_DIR"
    cp "$CFG" "$CONFIG_PATH"
    cp "$CFG" "${LOG_DIR}/Tier${SIZE}G.cnf.txt"

    chmod 644 "$CONFIG_PATH"
}

copy_server_logs() {
    local SIZE=$1
    local DATADIR=$2
    local DEST_DIR="${LOG_DIR}"

    echo "Copying server logs to ${DEST_DIR}..."
    if [ -f "${DATADIR}/mysql-error.log" ]; then
        cp "${DATADIR}/mysql-error.log" "${DEST_DIR}/Tier${SIZE}G.errlog.txt"
    fi
}

# --- TELEMETRY FUNCTIONS ---
start_innodb_metrics() {
    local PREFIX=$1
    local OUT="${PREFIX}.innodb.txt"
    echo "innodb metrics -> ${OUT}"

    (
        # Header: one column per metric NAME, sorted
        HEADER=$("$MYSQL_CLIENT" -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -B \
            -e "SELECT NAME FROM information_schema.INNODB_METRICS ORDER BY NAME" 2>/dev/null \
            | paste -sd,)
        echo "timestamp,${HEADER}" > "$OUT"

        while :; do
            TS=$(date +%s.%3N)
            VALS=$("$MYSQL_CLIENT" -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -B \
                -e "SELECT COUNT FROM information_schema.INNODB_METRICS ORDER BY NAME" 2>/dev/null \
                | paste -sd,)
            echo "${TS},${VALS}" >> "$OUT"
            sleep 1
        done
    ) &
    echo $! > /tmp/innodb.pid
}

start_lru_metrics() {
    local PREFIX=$1
    local OUT="${PREFIX}.lru_metrics.csv"
    echo "all enabled InnoDB metrics (long format) -> ${OUT}"

    # Get the directory of this script
    local SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local COLLECTOR="${SCRIPT_DIR}/collect_lru_metrics.sh"

    if [ ! -x "$COLLECTOR" ]; then
        echo "WARNING: InnoDB metrics collector not found or not executable: $COLLECTOR"
        return 1
    fi

    # Start the collector in the background
    "$COLLECTOR" "$DB_HOST" "$DB_PORT" "$DB_USER" "$DB_PASS" "$OUT" 2>/dev/null &
    local pid=$!
    echo $pid > /tmp/lru_metrics.pid

    # Verify it started successfully
    sleep 0.5
    if ! kill -0 $pid 2>/dev/null; then
        echo "WARNING: Failed to start InnoDB metrics collector"
        rm -f /tmp/lru_metrics.pid
        return 1
    fi

    return 0
}

start_mutex_metrics() {
    local PREFIX=$1
    local OUT="${PREFIX}.mutex_metrics.csv"
    echo "InnoDB mutex metrics -> ${OUT}"

    # Get the directory of this script
    local SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local COLLECTOR="${SCRIPT_DIR}/collect_mutex_metrics.sh"

    if [ ! -x "$COLLECTOR" ]; then
        echo "WARNING: Mutex metrics collector not found or not executable: $COLLECTOR"
        return 1
    fi

    # Start the collector in the background
    "$COLLECTOR" "$DB_HOST" "$DB_PORT" "$DB_USER" "$DB_PASS" "$OUT" 2>/dev/null &
    local pid=$!
    echo $pid > /tmp/mutex_metrics.pid

    # Verify it started successfully
    sleep 0.5
    if ! kill -0 $pid 2>/dev/null; then
        echo "WARNING: Failed to start mutex metrics collector"
        rm -f /tmp/mutex_metrics.pid
        return 1
    fi

    return 0
}

enable_innodb_metrics() {
    echo ">>> Enabling all InnoDB metrics counters..."
    "$MYSQL_CLIENT" -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N \
        -e "SET GLOBAL innodb_monitor_enable = 'latch';" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "    innodb_monitor_enable = 'latch'"
    else
        echo "    ERROR: Failed to set innodb_monitor_enable"
    fi

    # Note: 'all' enables all available metrics including buffer_LRU_% if present
}

start_gdb_snapshots() {
    local PREFIX=$1
    local OUT="${PREFIX}.pt-pmp.txt"
    local DELAY=$((DURATION / 2))

    echo "pt-pmp stack profiling -> ${OUT} (will start after ${DELAY}s)"

    (
        # Wait for half of benchmark duration before starting profiling
        echo "Waiting ${DELAY} seconds before starting pt-pmp profiling..." > "$OUT"
        sleep $DELAY

        echo "" >> "$OUT"
        echo "Starting stack trace collection at $(date)" >> "$OUT"
        echo "Collecting stack traces using pt-pmp (auto-detecting mysqld)" >> "$OUT"
        echo "================================================" >> "$OUT"
        echo "" >> "$OUT"

        # Get absolute path to current directory for pt-eustack-resolver
        local SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

        # Run pt-pmp with sudo, providing PATH so it can find pt-eustack-resolver
        # Collect 30 snapshots with pt-pmp (auto-detects mysqld process)
        sudo env "PATH=$SCRIPT_DIR:$PATH" "$SCRIPT_DIR/pt-pmp" -i 30 -d pteu >> "$OUT" 2>&1

        echo "" >> "$OUT"
        echo "Profiling completed at $(date)" >> "$OUT"
    ) &
    echo $! > /tmp/gdb.pid
}

start_thread_status() {
    local PREFIX=$1
    local OUT_THPOOL="${PREFIX}.stat-thpool.txt"
    local OUT_THR="${PREFIX}.stat-thr.txt"
    echo "Thread pool status -> ${OUT_THPOOL}"
    echo "Threads status -> ${OUT_THR}"

    (
        while :; do
            TS=$(date +%s.%3N)
            "$MYSQL_CLIENT" -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -e "SHOW GLOBAL STATUS LIKE 'Threadpool%';" 2>/dev/null | awk -v ts="$TS" '{print ts"\t"$0}' >> "$OUT_THPOOL"
            sleep 1
        done
    ) &
    echo $! > /tmp/thread_status_thpool.pid

    (
        while :; do
            TS=$(date +%s.%3N)
            "$MYSQL_CLIENT" -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -N -e "SHOW GLOBAL STATUS LIKE 'Threads%';" 2>/dev/null | awk -v ts="$TS" '{print ts"\t"$0}' >> "$OUT_THR"
            sleep 1
        done
    ) &
    echo $! > /tmp/thread_status_thr.pid
}

start_metrics() {
    local PREFIX=$1
    echo " --- START METRICS ---"

    iostat -dxm 1 > "${PREFIX}.iostat.txt" & echo $! > /tmp/iostat.pid
    vmstat 1 > "${PREFIX}.vmstat.txt" & echo $! > /tmp/vmstat.pid
    mpstat -P ALL 1 > "${PREFIX}.mpstat.txt" & echo $! > /tmp/mpstat.pid
    dstat -t 1 > "${PREFIX}.dstat.txt" & echo $! > /tmp/dstat.pid

    start_innodb_metrics "$PREFIX"
    start_lru_metrics "$PREFIX"
    start_mutex_metrics "$PREFIX"
    start_gdb_snapshots "$PREFIX"
    start_thread_status "$PREFIX"
}

stop_metrics() {
    # Stop all monitoring processes
    local pids_to_kill=""

    for pidfile in /tmp/iostat.pid /tmp/vmstat.pid /tmp/mpstat.pid /tmp/dstat.pid /tmp/innodb.pid /tmp/lru_metrics.pid /tmp/mutex_metrics.pid /tmp/gdb.pid /tmp/thread_status_thpool.pid /tmp/thread_status_thr.pid; do
        if [ -f "$pidfile" ]; then
            pids_to_kill="$pids_to_kill $(cat $pidfile)"
        fi
    done

    if [ -n "$pids_to_kill" ]; then
        kill $pids_to_kill 2>/dev/null
    fi

    # Give GDB snapshot a moment to finish if still running
    if [ -f /tmp/gdb.pid ]; then
        local gdb_pid=$(cat /tmp/gdb.pid)
        if kill -0 "$gdb_pid" 2>/dev/null; then
            echo "Waiting for GDB snapshots to complete..."
            sleep 2
        fi
    fi

    # Clean up PID files
    rm -f /tmp/iostat.pid /tmp/vmstat.pid /tmp/mpstat.pid /tmp/dstat.pid /tmp/innodb.pid /tmp/lru_metrics.pid /tmp/mutex_metrics.pid /tmp/gdb.pid /tmp/thread_status_thpool.pid /tmp/thread_status_thr.pid
}

trap 'stop_metrics; stop_server' EXIT
trap 'stop_metrics; stop_server; exit 1' INT TERM

init_data() {
  echo ">>> Create tables and insert data..."
  sysbench oltp_read_only --mysql-host=$DB_HOST --mysql-port=$DB_PORT --mysql-user=$DB_USER --mysql-password=$DB_PASS \
    --mysql-db=$DB_DATABASE --tables=20 --table-size=$TABLE_ROWS --threads=64 prepare
}

# --- EXECUTION LOOP ---
for SIZE in "${POOL_SIZES[@]}"; do
  echo "========================================================="
  echo ">>> TIER: ${SIZE}GB | VER: $RAW_VERSION <<<"
  echo "========================================================="

  # 1. Create clean datadir for this tier
  TIER_DATADIR="${DATADIR_BASE}/${DBMS_NAME}_${RAW_VERSION}_tier${SIZE}G"
  if [ "$ENABLE_BINLOG" == "1" ]; then
      TIER_DATADIR="${TIER_DATADIR}_binlog"
  fi
  if [ "$ENABLE_THREAD_POOL" == "1" ]; then
      TIER_DATADIR="${TIER_DATADIR}_threadpool"
  fi

  initialize_datadir "$TIER_DATADIR"

  # 2. Generate config
  generate_config $SIZE "$TIER_DATADIR"

  echo "Starting server with the new config..."
  start_server "$TIER_DATADIR" "$CONFIG_PATH"
  server_wait

  # Set root password and grant TCP/IP access (use socket for initial connection after fresh init)
  "$MYSQLADMIN" --socket=/tmp/mysql_benchmark.sock -u"$DB_USER" password "$DB_PASS" 2>/dev/null

  # Grant access from 127.0.0.1
  "$MYSQL_CLIENT" --socket=/tmp/mysql_benchmark.sock -u"$DB_USER" -p"$DB_PASS" -e "CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY '$DB_PASS'; GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION; FLUSH PRIVILEGES;" 2>/dev/null

  # Create database
  "$MYSQL_CLIENT" -h "$DB_HOST" --port=$DB_PORT -u "$DB_USER" -p"$DB_PASS" -e "CREATE DATABASE IF NOT EXISTS ${DB_DATABASE};" 2>/dev/null

  echo "Server started with custom config."
  check_innodb_buffer $SIZE
  enable_innodb_metrics
  check_vars_status "${LOG_DIR}/Tier${SIZE}G"
  init_data
  run_mysql_summary "${LOG_DIR}/Tier${SIZE}G"

  # 2. WARMUP (Reads then Writes)
  echo ">>> Warmup A: Read-Only (${WARMUP_RO_TIME}s)..."
  sysbench oltp_read_only --mysql-host=$DB_HOST --mysql-port=$DB_PORT --mysql-user=$DB_USER --mysql-password=$DB_PASS \
    --mysql-db=$DB_DATABASE --tables=20 --table-size=$TABLE_ROWS --threads=16 --time=$WARMUP_RO_TIME run

  if [ "$IS_READ_ONLY" == "1" ]; then
    echo "Read-only mode enabled, skipping read-write warmup and benchmarks."
    TEST_TYPE="oltp_read_only"
  else
    echo ">>> Warmup B: Dirty Writes (${WARMUP_RW_TIME}s)..."
    sysbench oltp_read_write --mysql-host=$DB_HOST --mysql-port=$DB_PORT --mysql-user=$DB_USER --mysql-password=$DB_PASS \
        --mysql-db=$DB_DATABASE --tables=20 --table-size=$TABLE_ROWS --threads=64 --time=$WARMUP_RW_TIME run
    TEST_TYPE="oltp_read_write"
  fi

  # 3. MEASUREMENT (three runs per thread count for stability)
  for THREAD in "${THREADS[@]}"; do
    #for RUN in 1; do
    for RUN in 1 2 3; do
      FILE_PREFIX="${LOG_DIR}/run${RUN}_Tier${SIZE}G_RW_${THREAD}th"
      echo "   >>> Testing ${THREAD} Threads (run ${RUN}/3)..."

      start_metrics "$FILE_PREFIX"

      sysbench $TEST_TYPE \
        --mysql-host=$DB_HOST \
        --mysql-port=$DB_PORT \
        --mysql-user=$DB_USER \
        --mysql-password=$DB_PASS \
        --mysql-db=$DB_DATABASE \
        --tables=20 \
        --table-size=$TABLE_ROWS \
        --threads=$THREAD \
        --time=$DURATION \
        --report-interval=1 \
        --rand-type=uniform \
        --mysql-ssl=off \
        run > "${FILE_PREFIX}.sysbench.txt"

      stop_metrics
      sleep 10
    done
  done

  copy_server_logs $SIZE "$TIER_DATADIR"

  stop_server
done

echo "============= Finished benchmarks for ${DBMS_NAME}:${DBMS_VER} ============="
