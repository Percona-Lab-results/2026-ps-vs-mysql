# InnoDB Metrics Report Optimization

## Problem
The original `innodb_metrics_report.py` generated HTML files that were **~53 MB** in size, making them slow to load and difficult to work with in browsers.

## Root Cause
The script embedded ALL parsed data directly into the HTML file as a large JavaScript constant:
```javascript
const DATA = {entire_json_object_with_all_data};
```

With ~850 rows per file × multiple servers × multiple runs × 319 metrics, this resulted in massive inline JSON.

## Solution
Refactored to use **dynamic data loading**:

1. **Split data into separate JSON files**: One file per server+run combination
2. **HTML contains only metadata**: A manifest mapping keys to JSON file paths
3. **Load data on-demand**: JavaScript fetches only the required JSON files when user selects servers/runs
4. **Client-side caching**: Loaded data is cached to avoid redundant fetches

## Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **HTML file size** | ~53 MB | 38 KB | **99.93% reduction** |
| **Initial page load** | ~53 MB | 38 KB | ~1400x faster |
| **Data files** | Embedded | 6 × ~9 MB JSON | Separate, cacheable |
| **User experience** | Slow, browser hangs | Fast, responsive | ✅ |

## File Structure

```
2026-ps-vs-mysql/
├── innodb_metrics_report.py          # Optimized script
├── innodb_metrics_optimized.html     # Generated HTML (38 KB)
└── innodb_data/                      # Data directory
    ├── mysql_8_4_8_run1.json         # 8.7 MB
    ├── mysql_8_4_8_run2.json         # 8.7 MB
    ├── mysql_8_4_8_run3.json         # 8.7 MB
    ├── percona-server_8_4_8-8_run1.json  # 8.8 MB
    ├── percona-server_8_4_8-8_run2.json  # 8.8 MB
    └── percona-server_8_4_8-8_run3.json  # 8.8 MB
```

## Key Changes in Code

### Data Export
```python
# OLD: Embed everything
data_by_server_run = {...}  # All data
html = f"const DATA = {json.dumps(data_by_server_run)}"

# NEW: Write separate files and manifest
for each server+run:
    write JSON file to innodb_data/
data_manifest = {key: "path/to/file.json"}
html = f"const DATA_MANIFEST = {json.dumps(data_manifest)}"
```

### Data Loading
```javascript
// NEW: Async loading with caching
async function loadData(key) {
    if (dataCache[key]) return dataCache[key];
    const response = await fetch(DATA_MANIFEST[key]);
    const data = await response.json();
    dataCache[key] = data;
    return data;
}
```

## Benefits

1. **Fast initial load**: HTML loads instantly (38 KB vs 53 MB)
2. **On-demand data**: Only selected combinations are fetched
3. **Browser compatibility**: No more "page unresponsive" warnings
4. **Better caching**: Browser can cache individual JSON files
5. **Network efficiency**: Only load what's needed
6. **Maintainability**: Data files can be regenerated independently

## Usage

```bash
# Generate optimized report
python3 innodb_metrics_report.py benchmark_logs output.html

# This creates:
# - output.html (lightweight HTML page)
# - innodb_data/ (directory with JSON files)

# Both must be kept together for the report to work
```

## Technical Notes

- The HTML must be served from a web server (or opened locally with file://) for fetch() to work
- All JSON files use `separators=(',', ':')` for minimal size
- File naming uses sanitized server names (spaces → underscores, etc.)
- Browser cache stores loaded data in memory during the session
- Loading indicator shows while data is being fetched

## Future Enhancements (Optional)

1. Add gzip compression to JSON files (would reduce to ~1-2 MB each)
2. Implement chart visualization using loaded data
3. Add export functionality for selected data subsets
4. Stream large files instead of loading entirely
5. Add service worker for offline capability
