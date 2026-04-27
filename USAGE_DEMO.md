# InnoDB Metrics Report - Usage Demo

## Quick Start

1. **Generate the report:**
   ```bash
   cd ~/2026-ps-vs-mysql
   python3 innodb_metrics_report.py benchmark_logs innodb_metrics_report.html
   ```

2. **Open in browser:**
   ```bash
   firefox innodb_metrics_report.html
   # or
   google-chrome innodb_metrics_report.html
   ```

## Interface Walkthrough

### Step 1: Select Servers
```
┌─ Servers ─────────────────┐
│ ☑ mysql 8.4.8            │
│ ☑ percona-server 8.4.8-8 │
│                          │
│                          │
│                          │
└──────────────────────────┘
```
- Hold Ctrl/Cmd to select multiple servers
- Selected servers will be highlighted

### Step 2: Select Runs
```
┌─ Runs ────────────────────┐
│ ☑ Run 1                   │
│ ☑ Run 2                   │
│ ☑ Run 3                   │
│                           │
│                           │
└───────────────────────────┘
```
- Select one or more benchmark runs
- Compare different runs side-by-side

### Step 3: Search and Select Metrics
```
┌─ Metrics (searchable, multi-select) ─────────┐
│ Search metrics...                             │
└───────────────────────────────────────────────┘
┌─ Selected Metrics ────────────────────────────┐
│ [buffer_pool_bytes_data ×]                    │
│ [innodb_rows_read ×]                          │
│ [innodb_rows_updated ×]                       │
└───────────────────────────────────────────────┘
```

#### Search Example 1: Buffer Pool Metrics
Type "buffer_pool" in the search box:
```
┌─────────────────────────────────────────────┐
│ ☑ Select All / Deselect All                │
├─────────────────────────────────────────────┤
│ ☐ buffer_pool_bytes_data                   │
│ ☐ buffer_pool_bytes_dirty                  │
│ ☐ buffer_pool_pages_data                   │
│ ☐ buffer_pool_pages_dirty                  │
│ ☐ buffer_pool_pages_flushed                │
│ ☐ buffer_pool_pages_free                   │
│ ☐ buffer_pool_pages_misc                   │
│ ☐ buffer_pool_pages_total                  │
│ ☐ buffer_pool_read_ahead                   │
│ ☐ buffer_pool_read_ahead_evicted           │
│ ☐ buffer_pool_read_ahead_rnd               │
│ ☐ buffer_pool_read_requests                │
│ ☐ buffer_pool_reads                        │
│ ☐ buffer_pool_size                         │
│ ☐ buffer_pool_wait_free                    │
│ ☐ buffer_pool_write_requests               │
└─────────────────────────────────────────────┘
```

#### Search Example 2: Row Operations
Type "innodb_rows" in the search box:
```
┌─────────────────────────────────────────────┐
│ ☑ Select All / Deselect All                │
├─────────────────────────────────────────────┤
│ ☐ innodb_rows_deleted                      │
│ ☐ innodb_rows_inserted                     │
│ ☐ innodb_rows_read                         │
│ ☐ innodb_rows_updated                      │
└─────────────────────────────────────────────┘
```

### Step 4: Generate Table
Click the **"Generate Table"** button

The page will:
1. Show "Loading data..." while fetching JSON files
2. Display a multi-column table with your selections
3. Show statistics for each metric

## Example Output

### Table Header Structure
```
┌───────────┬──────────────────────────────────┬──────────────────────────────────┐
│           │     MySQL 8.4.8 Run 1            │   Percona Server 8.4.8-8 Run 1   │
│ Timestamp ├──────────┬──────────┬────────────┼──────────┬──────────┬────────────┤
│           │  metric1 │  metric2 │  metric3   │  metric1 │  metric2 │  metric3   │
├───────────┼──────────┼──────────┼────────────┼──────────┼──────────┼────────────┤
│ 00:00:10  │  12,345  │  67,890  │  1,234,567 │  12,890  │  69,000  │  1,250,000 │
│ 00:00:20  │  13,456  │  68,901  │  1,345,678 │  13,901  │  70,111  │  1,361,111 │
│ 00:00:30  │  14,567  │  69,012  │  1,456,789 │  14,012  │  71,222  │  1,472,222 │
│   ...     │   ...    │   ...    │    ...     │   ...    │   ...    │    ...     │
└───────────┴──────────┴──────────┴────────────┴──────────┴──────────┴────────────┘
```

### Statistics Section
```
┌─ Statistics ──────────────────────────────────────────────────┐
│                                                                │
│  MySQL 8.4.8 Run 1 - innodb_rows_read                         │
│  Avg: 123,456.78                                               │
│  Min: 100,000 | Max: 150,000                                   │
│                                                                │
│  MySQL 8.4.8 Run 1 - innodb_rows_updated                       │
│  Avg: 45,678.90                                                │
│  Min: 40,000 | Max: 50,000                                     │
│                                                                │
│  Percona Server 8.4.8-8 Run 1 - innodb_rows_read              │
│  Avg: 125,678.12                                               │
│  Min: 102,000 | Max: 155,000                                   │
│                                                                │
│  Percona Server 8.4.8-8 Run 1 - innodb_rows_updated           │
│  Avg: 46,789.01                                                │
│  Min: 41,000 | Max: 52,000                                     │
└────────────────────────────────────────────────────────────────┘
```

## Common Use Cases

### 1. Compare Buffer Pool Efficiency
**Goal**: See how MySQL vs Percona Server handle buffer pool

**Steps**:
1. Select both servers
2. Select all runs (1, 2, 3)
3. Search for "buffer_pool"
4. Select: `buffer_pool_read_requests`, `buffer_pool_reads`, `buffer_pool_pages_data`
5. Generate Table

**Analysis**: Compare read requests vs actual reads to calculate hit ratio

### 2. Monitor Row Operations Over Time
**Goal**: Track insert/update/delete patterns

**Steps**:
1. Select one server
2. Select one run
3. Search for "innodb_rows"
4. Select all: `innodb_rows_read`, `innodb_rows_inserted`, `innodb_rows_updated`, `innodb_rows_deleted`
5. Generate Table

**Analysis**: See the workload distribution over the benchmark duration

### 3. Analyze Lock Contention
**Goal**: Identify locking issues

**Steps**:
1. Select all servers
2. Select all runs
3. Search for "lock"
4. Select: `lock_deadlocks`, `lock_row_lock_waits`, `lock_row_lock_time`
5. Generate Table

**Analysis**: Compare lock behavior between MySQL and Percona Server

### 4. Check Adaptive Hash Index Usage
**Goal**: Evaluate AHI effectiveness

**Steps**:
1. Select all servers and runs
2. Search for "adaptive_hash"
3. Click "Select All" to select all adaptive hash metrics
4. Generate Table

**Analysis**: Monitor searches, hits, and memory usage

## Tips and Tricks

### Tip 1: Use Keywords for Quick Selection
- **"read"** - All read-related metrics
- **"write"** - All write-related metrics
- **"page"** - All page-related metrics
- **"lock"** - All locking metrics
- **"buffer"** - Buffer pool metrics
- **"log"** - Log-related metrics

### Tip 2: Select All Filtered Metrics
1. Type a search term
2. Click "Select All / Deselect All"
3. All visible (filtered) metrics are selected instantly

### Tip 3: Quick Metric Removal
- Click the **×** on any blue tag to remove that metric
- Or uncheck it in the dropdown

### Tip 4: Keyboard Shortcuts
- **Enter** - Trigger "Generate Table" button
- **Escape** - Close dropdown (planned feature)

### Tip 5: Keep Related Metrics Together
When selecting metrics, think about relationships:
- Buffer pool reads + write requests = I/O pattern
- Row operations (CRUD) = workload profile
- Lock waits + deadlocks = contention analysis

## Performance Notes

- **Initial load**: ~38-96 KB (HTML only)
- **Per server+run**: ~9 MB JSON (loaded on demand)
- **Typical usage**: Loads 2-4 JSON files (18-36 MB)
- **Browser memory**: Caches loaded data in JavaScript
- **Large selections**: 6 servers × 3 runs × 10 metrics = 180 columns (works fine)

## Troubleshooting

### "No data available"
- Check that JSON files exist in `innodb_data/` directory
- Verify file paths in browser console

### Dropdown doesn't show
- Click inside the search box to activate
- Check browser console for JavaScript errors

### Metrics not filtering
- Clear the search box and try again
- Check that JavaScript is enabled

### Table is too wide
- Select fewer metrics or servers
- Use browser zoom (Ctrl + Mouse Wheel)
- Scroll horizontally in the table container

## Summary

This tool provides a powerful, flexible way to analyze InnoDB metrics:
- ✅ **319 metrics** available
- ✅ **Search** to find what you need
- ✅ **Multi-select** for comparisons
- ✅ **Dynamic loading** for speed
- ✅ **Rich statistics** for analysis
- ✅ **Responsive UI** that scales

Enjoy your analysis! 🚀
