# Thread Selection Feature - Documentation

## Overview

The InnoDB Metrics Report now includes **thread count selection**, allowing you to filter and analyze performance data by the number of threads used in the benchmark (16, 32, or 64).

## Feature Details

### Thread Count Parsing
- Automatically extracts thread count from filenames
- Format: `run{N}_Tier{M}G_RW_{T}th.innodb.txt`
- Example: `run1_Tier12G_RW_64th.innodb.txt` → 64 threads

### Available Thread Counts
Based on your benchmark data:
- **16 threads**
- **32 threads**
- **64 threads**

### Multi-Select Interface
```
┌─ Threads ────────┐
│ ☑ 16 threads     │
│ ☑ 32 threads     │
│ ☑ 64 threads     │
│                  │
└──────────────────┘
```

## UI Changes

### Controls Layout
The controls now have **4 columns** instead of 3:

```
┌────────────────────────────────────────────────────────────────┐
│  Servers         Runs           Threads        Metrics         │
│  ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌──────────────┐ │
│  │ MySQL   │   │ Run 1   │   │ 16 th    │   │ Search...    │ │
│  │ Percona │   │ Run 2   │   │ 32 th    │   └──────────────┘ │
│  │         │   │ Run 3   │   │ 64 th    │   Selected tags   │
│  └─────────┘   └─────────┘   └──────────┘   below           │
└────────────────────────────────────────────────────────────────┘
```

### Table Headers
Thread count is now shown in the column headers:

**Before**:
```
| Timestamp | MySQL 8.4.8 Run 1 | Percona Server 8.4.8-8 Run 1 |
```

**After**:
```
| Timestamp | MySQL 8.4.8           | Percona Server 8.4.8-8    |
|           | Run 1                 | Run 1                     |
|           | 64 threads            | 64 threads                |
```

### Chart Legends
Thread count is included in all chart labels:

**Before**:
```
━━━ MySQL 8.4.8 Run 1 (per second)
┈┈┈ MySQL 8.4.8 Run 1 (minute avg)
```

**After**:
```
━━━ MySQL 8.4.8 Run 1 64th (per second)
┈┈┈ MySQL 8.4.8 Run 1 64th (minute avg)
```

### Statistics
Thread count is shown in statistics labels:

**Before**:
```
MySQL 8.4.8 Run 1 - innodb_rows_read
Avg: 123,456.78
```

**After**:
```
MySQL 8.4.8 Run 1 (64th) - innodb_rows_read
Avg: 123,456.78
```

## Data Organization

### File Naming Convention
JSON data files now include thread count:

```
{server}_run{N}_{T}th.json
```

**Examples**:
- `mysql_8_4_8_run1_16th.json`
- `mysql_8_4_8_run1_32th.json`
- `mysql_8_4_8_run1_64th.json`
- `percona-server_8_4_8-8_run1_16th.json`
- `percona-server_8_4_8-8_run1_32th.json`
- `percona-server_8_4_8-8_run1_64th.json`

### Data Manifest Keys
Internal keys now include thread count:

```javascript
// Old format
"mysql 8.4.8||1" → "innodb_data/mysql_8_4_8_run1.json"

// New format
"mysql 8.4.8||1||64" → "innodb_data/mysql_8_4_8_run1_64th.json"
```

### Total Files
- **2 servers** (MySQL, Percona Server)
- **3 runs** per server
- **3 thread counts** per run
- **Total: 18 JSON files** (~9 MB each, ~162 MB total)

## Use Cases

### 1. Analyze Performance at Specific Thread Count

**Goal**: Compare MySQL vs Percona at 64 threads

**Steps**:
1. Select both servers
2. Select all runs (1, 2, 3)
3. Select **64 threads** only
4. Select key metrics (locks, I/O, rows)
5. Generate Report → Chart View
6. Analyze differences

### 2. Compare Thread Scaling

**Goal**: See how performance changes from 16 → 32 → 64 threads

**Method A: Sequential Comparison**
1. Select 16 threads → Generate → Note patterns
2. Select 32 threads → Generate → Note patterns
3. Select 64 threads → Generate → Compare

**Method B: Multi-Thread Comparison**
1. Select **all thread counts** (16, 32, 64)
2. Select one server, one run
3. Generate Report → Chart View
4. See 3 lines (one per thread count)

### 3. Find Thread-Specific Bottlenecks

**Goal**: Identify why Percona is slower at 64 threads

**Steps**:
1. Select Percona Server only
2. Select one run
3. Select 32 threads → Generate → Note metrics
4. Select 64 threads → Generate → Compare
5. Look for:
   - Increased lock contention
   - Buffer pool pressure
   - I/O bottlenecks
   - CPU saturation

### 4. Cross-Server Thread Analysis

**Goal**: Find at what thread count Percona becomes slower

**Steps**:
1. Select both servers
2. Select all runs
3. Start with 16 threads → Generate
4. Switch to 32 threads → Regenerate
5. Switch to 64 threads → Regenerate
6. Identify the inflection point

## Key Metrics for Thread Analysis

### Lock Contention
- `lock_row_lock_waits` - Row lock wait events
- `lock_deadlocks` - Deadlock occurrences
- `lock_row_lock_time` - Time spent waiting
- `lock_row_lock_current_waits` - Current waiters

### Buffer Pool Pressure
- `buffer_pool_wait_free` - Waiting for free pages
- `buffer_pool_pages_flushed` - Flush activity
- `buffer_pool_reads` - Physical reads (cache misses)
- `buffer_pool_read_requests` - Logical reads (cache hits)

### Row Operations
- `innodb_rows_read` - Rows read
- `innodb_rows_inserted` - Rows inserted
- `innodb_rows_updated` - Rows updated
- `innodb_rows_deleted` - Rows deleted

### I/O Activity
- `os_log_pending_writes` - Log write backlog
- `os_data_reads` - Data file reads
- `os_data_writes` - Data file writes

## Analysis Patterns

### High Thread Contention Indicators

**Pattern 1: Lock Wait Spike**
```
Thin line (per-second):  /\  /\  /\/\/\/\
Thick line (minute avg): ————————————————

→ Frequent, short-lived lock waits
→ High contention, good resolution
```

**Pattern 2: Sustained Lock Waits**
```
Thin line (per-second):  ————————————————
Thick line (minute avg): ————————————————

→ Constant lock pressure
→ Severe contention issue
```

**Pattern 3: Increasing Lock Waits**
```
Thin line (per-second):      ╱
Thick line (minute avg):    ╱

→ Worsening contention over time
→ System degradation
```

### Thread Scaling Issues

**Good Scaling (16 → 32 → 64 threads)**
```
Throughput:
16th: ━━━━━━━━━━━━ 10K ops/sec
32th: ━━━━━━━━━━━━━━━━━━━━━━ 20K ops/sec
64th: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 40K ops/sec

→ Linear scaling
→ No contention
```

**Poor Scaling (16 → 32 → 64 threads)**
```
Throughput:
16th: ━━━━━━━━━━━━ 10K ops/sec
32th: ━━━━━━━━━━━━━━━ 15K ops/sec
64th: ━━━━━━━━━━━━━━━━━ 16K ops/sec

→ Diminishing returns
→ Contention/bottleneck at high thread count
```

## Validation

### Verify Thread Selection Works
1. Generate report with default settings
2. Check console output shows: `Threads: 16, 32, 64`
3. Select 64 threads in UI
4. Generate Report
5. Table headers should show "64 threads"
6. Chart legends should show "64th"

### Check Data Files
```bash
ls innodb_data/*.json | grep "64th"
# Should show:
# mysql_8_4_8_run1_64th.json
# mysql_8_4_8_run2_64th.json
# ...etc
```

## Troubleshooting

### Thread selector is empty
**Cause**: Script couldn't parse thread count from filenames  
**Fix**: Verify filenames match pattern `*_64th.innodb.txt`

### No data after selecting threads
**Cause**: No data files exist for selected combination  
**Fix**: Check that JSON files were generated with thread suffix

### Chart shows wrong thread count
**Cause**: Old cached data  
**Fix**: Regenerate HTML from scratch with new script

## Technical Implementation

### Parser Changes
```python
# Extract thread count from filename
import re
thread_match = re.search(r'_(\d+)th\.', filename)
threads = thread_match.group(1)  # "64"
```

### Manifest Key Format
```python
# Include threads in key
key = f"{server}||{run}||{threads}"
# "mysql 8.4.8||1||64"
```

### JavaScript Changes
```javascript
// Add thread select
const threadSelect = document.getElementById('threadSelect');
const selectedThreads = Array.from(threadSelect.selectedOptions).map(o => o.value);

// Build combinations with threads
for (const threads of selectedThreads) {
    const key = `${server}||${run}||${threads}`;
    // ...
}
```

## Performance Impact

### File Size
- **HTML**: 110 KB (was 109 KB, +1 KB for thread selector)
- **JSON**: Same size per file (~9 MB)
- **Total data**: 162 MB (18 files vs 54 MB for 6 files)

### Loading Speed
- Same performance (lazy loading)
- Only selected thread counts are fetched

### Browser Memory
- Slightly more data if all threads selected
- Negligible impact (< 50 MB difference)

## Summary

The thread selection feature enables:
- ✅ Filter benchmarks by thread count
- ✅ Compare performance at different thread levels
- ✅ Identify thread-specific bottlenecks
- ✅ Analyze scaling behavior
- ✅ Pinpoint the root cause of contention issues

This is especially useful for analyzing why **Percona Server is slower at 64 threads** compared to MySQL.

---

**Version**: 2.1 (Thread Selection)  
**Date**: 2026-04-27  
**Status**: Production Ready ✅
