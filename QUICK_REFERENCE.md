# InnoDB Metrics Report - Quick Reference Card

## 🚀 Generate Report
```bash
python3 innodb_metrics_report.py benchmark_logs output.html
firefox output.html
```

## 🎯 3-Step Workflow
1. **Select** → Servers, Runs, Metrics (search & multi-select)
2. **Generate** → Click "Generate Report" button
3. **Analyze** → Toggle between Table View and Chart View

## 🔍 Search Tips
| Keyword | Finds |
|---------|-------|
| `buffer` | Buffer pool metrics |
| `read` | Read operations |
| `write` | Write operations |
| `lock` | Lock and deadlock metrics |
| `innodb_rows` | Row CRUD operations |
| `page` | Page-related metrics |
| `log` | Logging metrics |

## 📊 Chart Interpretation

### Thin Lines (1px solid)
- **What**: Per-second measurements
- **Shows**: Spikes, variability, instantaneous values
- **Use for**: Detecting anomalies

### Thick Lines (4px dashed)
- **What**: Per-minute averages
- **Shows**: Trends, patterns, smoothed values
- **Use for**: Overall behavior

### Combined Reading
```
Thin ≈ Thick  → Stable system
Thin >> Thick → High variability, spikes
Thin << Thick → Not typical (check data)
```

## 📈 Common Analysis Tasks

### Buffer Pool Efficiency
**Metrics**: `buffer_pool_read_requests`, `buffer_pool_reads`  
**Look for**: Ratio between requests and actual reads (hit ratio)

### Row Operations
**Metrics**: `innodb_rows_read`, `innodb_rows_inserted`, `innodb_rows_updated`  
**Look for**: Operation rates and patterns over time

### Lock Contention
**Metrics**: `lock_row_lock_waits`, `lock_deadlocks`  
**Look for**: Spikes indicating contention events

### Write Performance
**Metrics**: `innodb_rows_inserted`, `innodb_rows_updated`, `buffer_pool_pages_flushed`  
**Look for**: Sustained write throughput

## 🎨 Interface Elements

### Multi-Select Box
```
┌─────────────────────┐
│ Search metrics...   │ ← Type to filter
├─────────────────────┤
│ ☑ Select All        │ ← Bulk action
│ ☐ metric_name_1     │ ← Individual selection
│ ☐ metric_name_2     │
└─────────────────────┘

[metric_name_1 ×]       ← Visual tags (click × to remove)
```

### View Toggle
```
┌──────────────┬──────────────┐
│ Table View ● │  Chart View  │ ← Switch views
└──────────────┴──────────────┘
```

### Chart Controls
```
Select Metric for Chart: [metric_name ▼] ← Choose which to visualize
```

## ⌨️ Keyboard Shortcuts
- **Enter**: Generate Report
- **Click search box**: Open metric dropdown
- **Click outside**: Close dropdown

## 🎯 Best Practices

### Do This ✅
- Start with 2-3 metrics
- Use search to find related metrics
- Select All filtered results
- Switch between Table and Chart views
- Compare 2-3 server+run combinations at once

### Avoid This ❌
- Don't select 50+ metrics at once (slow)
- Don't skip the search (319 metrics to scroll!)
- Don't forget to generate report first
- Don't ignore thin line spikes
- Don't compare too many combinations (cluttered)

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Chart doesn't show | Generate report first, then switch to Chart View |
| No metrics in dropdown | Check that you generated the report |
| Dropdown won't open | Click inside the search box |
| Chart is cluttered | Reduce server+run combinations to 2-3 |
| No data shown | Verify JSON files exist in `innodb_data/` |

## 📊 File Sizes
- **HTML**: ~109 KB (loads instantly)
- **JSON per run**: ~9 MB (loaded on demand)
- **Total data**: ~54 MB (6 runs)
- **Chart.js**: ~80 KB (from CDN)

## 🎨 Color Legend
Each server+run combination gets a unique color:
- Red, Blue, Yellow, Teal, Purple, Orange, Gray...
- Same color for both thin and thick lines
- Dashed pattern indicates minute average

## 📚 Documentation Files
| File | Purpose |
|------|---------|
| `INNODB_METRICS_README.md` | Complete guide |
| `CHART_VISUALIZATION_GUIDE.md` | Chart details |
| `USAGE_DEMO.md` | Step-by-step examples |
| `MULTISELECT_METRICS_UPDATE.md` | Search features |
| `OPTIMIZATION_NOTES.md` | Technical details |

## 🔧 Advanced Features

### Select All Filtered
1. Type search term (e.g., "buffer")
2. Click "Select All"
3. All visible metrics are selected

### Remove Single Metric
- Click **×** on the blue tag
- Or uncheck in dropdown

### Quick Metric Comparison
1. Search for metric A
2. Select it
3. Search for metric B  
4. Select it
5. Generate → Chart View

## 💡 Pro Tips

1. **Keyword combinations**: Search "buffer read" for buffer read metrics
2. **Use statistics**: Table view shows avg/min/max automatically
3. **Hover tooltips**: Exact values on hover in charts
4. **Multiple runs**: Check consistency across runs 1, 2, 3
5. **Both views**: Use Table for numbers, Chart for patterns

## 🎯 Example Queries

### "What's my buffer pool hit ratio?"
```
Metrics: buffer_pool_read_requests, buffer_pool_reads
View: Table → Calculate ratio from statistics
      Chart → Compare trends visually
```

### "Are there lock contention spikes?"
```
Metrics: lock_row_lock_waits
View: Chart → Look for thin line spikes
```

### "How consistent is write throughput?"
```
Metrics: innodb_rows_updated, innodb_rows_inserted
Runs: Select all (1, 2, 3)
View: Chart → Check if thick lines align across runs
```

### "Compare MySQL vs Percona efficiency"
```
Servers: Both
Runs: Same run number
Metrics: Key metrics (buffer, rows, locks)
View: Chart → Color comparison
```

## 📞 Need Help?

1. Read `INNODB_METRICS_README.md` first
2. Check `CHART_VISUALIZATION_GUIDE.md` for chart help
3. Browse `USAGE_DEMO.md` for examples
4. Review this quick reference
5. Contact maintainer if stuck

---

**Version**: 2.0 | **Date**: 2026-04-27 | **Status**: Production Ready ✅
