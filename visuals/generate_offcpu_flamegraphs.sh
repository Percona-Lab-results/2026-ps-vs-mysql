#!/bin/bash

# Generate off-CPU flame graphs from .offcpu.txt files
# Flame graphs visualize where threads spend time off-CPU (blocking on locks, I/O, etc.)
# Wide towers ending in futex_wait/pthread_mutex_lock/__lll_lock_wait are contention hotspots

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
FLAMEGRAPH_REPO="https://github.com/brendangregg/FlameGraph.git"
FLAMEGRAPH_DIR="${SCRIPT_DIR}/FlameGraph"

# Check if flamegraph.pl exists, if not download it
if [ ! -f "${FLAMEGRAPH_DIR}/flamegraph.pl" ]; then
    echo "FlameGraph toolkit not found. Downloading..."
    cd "$SCRIPT_DIR"
    git clone "$FLAMEGRAPH_REPO"
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to clone FlameGraph repository"
        exit 1
    fi
    echo "FlameGraph toolkit downloaded successfully"
fi

FLAMEGRAPH_PL="${FLAMEGRAPH_DIR}/flamegraph.pl"

if [ ! -x "$FLAMEGRAPH_PL" ]; then
    chmod +x "$FLAMEGRAPH_PL"
fi

echo "Generating off-CPU flame graphs..."
echo "=" | tr '=' '=' | head -c 70; echo

# Find all .offcpu.txt files in benchmark directories
OFFCPU_FILES=$(find "$PROJECT_DIR" -name "*.offcpu.txt" -type f 2>/dev/null | sort)

if [ -z "$OFFCPU_FILES" ]; then
    echo "No .offcpu.txt files found in project directory"
    exit 0
fi

TOTAL_FILES=$(echo "$OFFCPU_FILES" | wc -l)
CURRENT=0

echo "Found $TOTAL_FILES off-CPU profile files"
echo ""

# Array to store SVG file paths for index generation
declare -a SVG_PATHS

for OFFCPU_FILE in $OFFCPU_FILES; do
    CURRENT=$((CURRENT + 1))

    # Get relative path from project root for display
    REL_PATH="${OFFCPU_FILE#$PROJECT_DIR/}"

    # Generate output SVG filename (replace .offcpu.txt with .offcpu.svg)
    SVG_FILE="${OFFCPU_FILE%.txt}.svg"

    echo "[$CURRENT/$TOTAL_FILES] Processing: $REL_PATH"

    # Check if file has actual data (skip if only header/waiting message)
    DATA_LINES=$(grep -v "^Waiting\|^Starting\|^Target PID\|^Duration\|^Off-CPU profiling\|^====\|^$" "$OFFCPU_FILE" | wc -l)

    if [ "$DATA_LINES" -lt 5 ]; then
        echo "  ⚠ Skipping: No profiling data (only $DATA_LINES data lines)"
        echo ""
        continue
    fi

    # Extract server name and configuration from path for title
    # Path format: benchmark_logs[_binlog][_bpN]/server/version/runN_TierXG_RW_Yth.offcpu.txt
    DIR_PATH=$(dirname "$REL_PATH")
    FILENAME=$(basename "$REL_PATH")

    # Parse benchmark directory name
    BENCH_DIR=$(echo "$DIR_PATH" | cut -d'/' -f1)
    BINLOG_STATUS="Binlog Disabled"
    BP_INSTANCES=""

    if [[ "$BENCH_DIR" == *"binlog"* && "$BENCH_DIR" != *"_bp"* ]]; then
        BINLOG_STATUS="Binlog Enabled"
    elif [[ "$BENCH_DIR" =~ _bp([0-9]+)$ ]]; then
        BP_NUM="${BASH_REMATCH[1]}"
        BP_INSTANCES=", ${BP_NUM} BP Instances"
        if [[ "$BENCH_DIR" == *"binlog"* ]]; then
            BINLOG_STATUS="Binlog Enabled"
        fi
    fi

    # Parse filename: run1_Tier12G_RW_64th.offcpu.txt
    RUN_NUM=$(echo "$FILENAME" | grep -oP 'run\K[0-9]+')
    THREADS=$(echo "$FILENAME" | grep -oP '[0-9]+(?=th)')

    # Get server from path
    SERVER=$(echo "$DIR_PATH" | cut -d'/' -f2)
    VERSION=$(echo "$DIR_PATH" | cut -d'/' -f3)

    # Extract context from offcpu.txt file
    TARGET_PID=$(grep "^Target PID:" "$OFFCPU_FILE" | head -1 | sed 's/Target PID: //')
    DURATION=$(grep "^Duration:" "$OFFCPU_FILE" | head -1 | sed 's/Duration: //')
    START_TIME=$(grep "^Starting off-CPU profiling at" "$OFFCPU_FILE" | head -1 | sed 's/Starting off-CPU profiling at //')

    # Create title with context
    TITLE="Off-CPU Profile: ${SERVER^^} ${VERSION} - Run ${RUN_NUM}, ${THREADS} threads ($BINLOG_STATUS$BP_INSTANCES)"

    # Create subtitle with additional context
    if [ -n "$TARGET_PID" ] && [ -n "$DURATION" ]; then
        SUBTITLE="PID: ${TARGET_PID} | ${DURATION} | Captured: ${START_TIME}"
    else
        SUBTITLE="Off-CPU time profiling"
    fi

    # Generate flame graph
    # Color scheme: blue (default for off-CPU) - cold colors indicate blocking/waiting
    # The --title sets the graph title
    # --countname sets the units (microseconds for off-CPU time)
    # --subtitle adds additional context below the title
    # --width sets overall width, --minwidth sets minimum frame width (helps text fit)
    # --fontsize controls font size (default 12)
    # --fontwidth controls character width
    # Remove --height to let flamegraph.pl auto-calculate based on stack depth
    cat "$OFFCPU_FILE" | \
        grep -v "^Waiting\|^Starting\|^Target PID\|^Duration\|^Off-CPU profiling\|^====\|^$" | \
        "$FLAMEGRAPH_PL" \
            --title "$TITLE" \
            --subtitle "$SUBTITLE" \
            --countname "microseconds" \
            --colors blue \
            --width 2400 \
            --minwidth 2 \
            --fontsize 12 \
            > "$SVG_FILE"

    if [ $? -eq 0 ]; then
        echo "  ✓ Generated: $(basename "$SVG_FILE")"
        FILE_SIZE=$(du -h "$SVG_FILE" | cut -f1)
        echo "  📊 Size: $FILE_SIZE, Data lines: $DATA_LINES"

        # Store SVG path for index generation
        SVG_PATHS+=("$SVG_FILE")
    else
        echo "  ✗ Failed to generate flame graph"
    fi

    echo ""
done

# Generate index-offcpu.html
echo "=" | tr '=' '=' | head -c 70; echo
echo "Generating index-offcpu.html..."

INDEX_FILE="${PROJECT_DIR}/index-offcpu.html"

cat > "$INDEX_FILE" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Off-CPU Flame Graphs Index</title>
    <style>
        body {
            font-family: system-ui, -apple-system, Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        header h1 {
            font-size: 36px;
            margin: 0 0 10px 0;
            font-weight: 700;
        }
        header p {
            font-size: 16px;
            opacity: 0.9;
            margin: 5px 0;
        }
        .stats-box {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            color: white;
            margin: 15px auto;
            max-width: 250px;
        }
        .stats-box .number {
            font-size: 42px;
            font-weight: bold;
            margin: 0;
        }
        .stats-box .label {
            font-size: 14px;
            opacity: 0.9;
        }
        .content {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .intro {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px 20px;
            margin-bottom: 30px;
            border-radius: 4px;
        }
        .intro h3 {
            margin: 0 0 10px 0;
            color: #667eea;
            font-size: 16px;
        }
        .intro p {
            margin: 5px 0;
            line-height: 1.6;
            color: #555;
        }
        .intro ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        .intro li {
            margin: 5px 0;
            color: #555;
        }
        .flame-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .flame-card {
            background: #f8f9fa;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            transition: all 0.3s ease;
            text-decoration: none;
            color: inherit;
            display: block;
        }
        .flame-card:hover {
            border-color: #667eea;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            transform: translateY(-2px);
        }
        .flame-card .server {
            font-weight: 700;
            font-size: 16px;
            color: #667eea;
            margin-bottom: 8px;
        }
        .flame-card .details {
            font-size: 13px;
            color: #666;
            margin: 4px 0;
        }
        .flame-card .path {
            font-family: 'Courier New', monospace;
            font-size: 11px;
            color: #999;
            margin-top: 8px;
            word-break: break-all;
        }
        .flame-card .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 6px;
            margin-top: 6px;
        }
        .badge-binlog {
            background: #fff3cd;
            color: #856404;
        }
        .badge-bp {
            background: #d1ecf1;
            color: #0c5460;
        }
        .badge-search {
            background: #d4edda;
            color: #155724;
        }
        footer {
            text-align: center;
            color: rgba(255, 255, 255, 0.7);
            margin-top: 30px;
            padding: 20px;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Off-CPU Flame Graphs</h1>
            <p>Interactive visualization of thread blocking patterns</p>
            <div class="stats-box">
                <div class="number">FLAME_COUNT</div>
                <div class="label">Flame Graphs</div>
            </div>
        </header>

        <div class="content">
            <div class="intro">
                <h3>📊 How to Read Off-CPU Flame Graphs</h3>
                <p>Off-CPU flame graphs show where threads spend time blocked (waiting), not executing:</p>
                <ul>
                    <li><strong>Wide towers</strong> = High off-CPU time (major contention hotspots)</li>
                    <li><strong>futex_wait</strong> = Waiting on futex (mutex/condition variable)</li>
                    <li><strong>pthread_mutex_lock</strong> = Waiting to acquire mutex</li>
                    <li><strong>__lll_lock_wait</strong> = Low-level lock wait</li>
                </ul>
                <p><strong>Auto-search:</strong> Each link opens with <code>?s=futex_wait</code> to automatically highlight futex_wait frames.</p>
            </div>

FLAME_SECTIONS
        </div>

        <footer>
            <p>Generated by generate_offcpu_flamegraphs.sh</p>
            <p>Off-CPU profiling collected with offcputime-bpfcc</p>
        </footer>
    </div>
</body>
</html>
EOF

# Group flame graphs by threads and BP instances
declare -A GROUPED_SVGS

for SVG_FILE in "${SVG_PATHS[@]}"; do
    # Get relative path from project root
    REL_SVG_PATH="${SVG_FILE#$PROJECT_DIR/}"

    # Parse path components
    DIR_PATH=$(dirname "$REL_SVG_PATH")
    FILENAME=$(basename "$REL_SVG_PATH")

    # Parse benchmark directory
    BENCH_DIR=$(echo "$DIR_PATH" | cut -d'/' -f1)

    # Parse filename for threads
    THREADS=$(echo "$FILENAME" | grep -oP '[0-9]+(?=th)')

    # Determine BP instances
    BP_NUM=""
    if [[ "$BENCH_DIR" =~ _bp([0-9]+) ]]; then
        BP_NUM="${BASH_REMATCH[1]}"
    fi

    # Determine binlog status
    BINLOG_STATUS="disabled"
    if [[ "$BENCH_DIR" == *"binlog"* ]]; then
        BINLOG_STATUS="enabled"
    fi

    # Create group key: threads_bpN_binlogStatus
    GROUP_KEY="${THREADS}th"
    if [ -n "$BP_NUM" ]; then
        GROUP_KEY="${GROUP_KEY}_bp${BP_NUM}"
    fi
    GROUP_KEY="${GROUP_KEY}_binlog${BINLOG_STATUS}"

    # Append to group
    if [ -z "${GROUPED_SVGS[$GROUP_KEY]}" ]; then
        GROUPED_SVGS[$GROUP_KEY]="$SVG_FILE"
    else
        GROUPED_SVGS[$GROUP_KEY]="${GROUPED_SVGS[$GROUP_KEY]}|$SVG_FILE"
    fi
done

# Generate sections HTML
SECTIONS_HTML=""

# Sort group keys
SORTED_KEYS=($(for key in "${!GROUPED_SVGS[@]}"; do echo "$key"; done | sort))

for GROUP_KEY in "${SORTED_KEYS[@]}"; do
    # Parse group key
    THREADS=$(echo "$GROUP_KEY" | grep -oP '^[0-9]+')
    BP_NUM=""
    if [[ "$GROUP_KEY" =~ _bp([0-9]+) ]]; then
        BP_NUM="${BASH_REMATCH[1]}"
    fi
    BINLOG_STATUS=$(echo "$GROUP_KEY" | grep -oP 'binlog\K(enabled|disabled)')

    # Create section title
    SECTION_TITLE="${THREADS} Threads"
    if [ -n "$BP_NUM" ]; then
        SECTION_TITLE="${SECTION_TITLE}, ${BP_NUM} BP Instances"
    fi
    if [ "$BINLOG_STATUS" = "enabled" ]; then
        SECTION_TITLE="${SECTION_TITLE} (Binlog Enabled)"
    else
        SECTION_TITLE="${SECTION_TITLE} (Binlog Disabled)"
    fi

    # Start section
    SECTIONS_HTML+="            <h3 style=\"margin-top:30px; padding-top:20px; border-top:2px solid #e0e0e0; color:#333;\">${SECTION_TITLE}</h3>
            <div class=\"flame-grid\">
"

    # Split SVG files and generate cards
    IFS='|' read -ra SVG_FILES <<< "${GROUPED_SVGS[$GROUP_KEY]}"
    for SVG_FILE in "${SVG_FILES[@]}"; do
        # Get relative path from project root
        REL_SVG_PATH="${SVG_FILE#$PROJECT_DIR/}"

        # Parse path components
        DIR_PATH=$(dirname "$REL_SVG_PATH")
        FILENAME=$(basename "$REL_SVG_PATH")

        # Parse benchmark directory
        BENCH_DIR=$(echo "$DIR_PATH" | cut -d'/' -f1)
        SERVER=$(echo "$DIR_PATH" | cut -d'/' -f2)
        VERSION=$(echo "$DIR_PATH" | cut -d'/' -f3)

        # Parse filename
        RUN_NUM=$(echo "$FILENAME" | grep -oP 'run\K[0-9]+')

        # Determine badges
        BINLOG_BADGE=""
        BP_BADGE=""

        if [[ "$BENCH_DIR" == *"binlog"* && "$BENCH_DIR" != *"_bp"* ]]; then
            BINLOG_BADGE='<span class="badge badge-binlog">Binlog Enabled</span>'
        fi

        if [[ "$BENCH_DIR" =~ _bp([0-9]+) ]]; then
            BP_NUM_DISPLAY="${BASH_REMATCH[1]}"
            BP_BADGE="<span class=\"badge badge-bp\">BP: ${BP_NUM_DISPLAY}</span>"
        fi

        # Create display name
        SERVER_DISPLAY=$(echo "$SERVER" | tr '[:lower:]' '[:upper:]')

        # Add card
        SECTIONS_HTML+="                <a href=\"${REL_SVG_PATH}?s=futex_wait\" class=\"flame-card\">
                    <div class=\"server\">${SERVER_DISPLAY} ${VERSION}</div>
                    <div class=\"details\">Run ${RUN_NUM}</div>
                    <div>
                        ${BINLOG_BADGE}${BP_BADGE}<span class=\"badge badge-search\">🔍 futex_wait</span>
                    </div>
                    <div class=\"path\">${REL_SVG_PATH}</div>
                </a>
"
    done

    # Close section
    SECTIONS_HTML+="            </div>
"
done

# Replace placeholders using temporary file to avoid sed delimiter issues
TEMP_FILE="${INDEX_FILE}.tmp"
FLAME_COUNT="${#SVG_PATHS[@]}"

# Read template and replace using bash parameter expansion
TEMPLATE_CONTENT=$(<"$INDEX_FILE")
TEMPLATE_CONTENT="${TEMPLATE_CONTENT//FLAME_COUNT/$FLAME_COUNT}"
TEMPLATE_CONTENT="${TEMPLATE_CONTENT//FLAME_SECTIONS/$SECTIONS_HTML}"
echo "$TEMPLATE_CONTENT" > "$TEMP_FILE"
mv "$TEMP_FILE" "$INDEX_FILE"

echo "✓ Generated: index-offcpu.html"
echo "  Total flame graphs: ${#SVG_PATHS[@]}"

echo ""
echo "=" | tr '=' '=' | head -c 70; echo
echo "✓ All flame graphs generated successfully!"
echo ""
echo "📋 Quick Access:"
echo "  Open: index-offcpu.html (navigation page for all flame graphs)"
echo "  Direct: Open any .offcpu.svg file in a web browser"
echo ""
echo "🔍 Auto-search enabled:"
echo "  All links include ?s=futex_wait to highlight contention points"
echo ""
echo "📊 Flame Graph Interpretation:"
echo "  🔥 Wide towers = high off-CPU time (contention hotspots)"
echo "  🔍 Look for stacks ending in:"
echo "     - futex_wait: waiting on futex (mutex/condition variable)"
echo "     - pthread_mutex_lock: waiting to acquire mutex"
echo "     - __lll_lock_wait: low-level lock wait"
echo "  📈 The stacks above these show which code path is contending"
echo "=" | tr '=' '=' | head -c 70; echo
