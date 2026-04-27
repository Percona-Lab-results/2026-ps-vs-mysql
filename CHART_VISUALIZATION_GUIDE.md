# Chart Visualization Guide

## Overview

The InnoDB Metrics Report now includes **interactive chart visualization** with dual-line graphs showing:
- **Thin lines**: Per-second measurements (raw data)
- **Thick dashed lines**: Per-minute averages (smoothed trend)

## Features

### 1. Dual-Layer Visualization
Each server+run combination is shown with two lines:
- **Thin solid line (1px)**: Shows every second's measurement
- **Thick dashed line (4px)**: Shows the average for each minute

This allows you to see both:
- **Fine-grained fluctuations**: Spikes, drops, and second-to-second variations
- **Overall trends**: Smoothed patterns over time

### 2. Chart Controls

#### View Toggle
```
┌──────────────┬──────────────┐
│ Table View   │  Chart View  │
└──────────────┴──────────────┘
```
- **Table View**: Shows detailed tabular data
- **Chart View**: Shows graphical visualizations

#### Metric Selector
```
Select Metric for Chart: [innodb_rows_read ▼]
```
- Choose which metric to visualize
- Only metrics you selected will be available
- One chart per metric showing all server+run combinations

### 3. Interactive Features

#### Zoom and Pan
- **Hover**: Shows precise values at any point
- **Tooltip**: Displays time (minutes:seconds) and values
- **Legend**: Color-coded for each server+run combination

#### Color Coding
- Each server+run gets a unique color
- Per-second and per-minute lines share the same color
- Dashed pattern distinguishes minute averages

## Usage Workflow

### Step 1: Select Your Data
1. Select servers (e.g., MySQL 8.4.8, Percona Server 8.4.8-8)
2. Select runs (e.g., Run 1, Run 2, Run 3)
3. Search and select metrics (e.g., "innodb_rows_read", "buffer_pool_reads")
4. Click **"Generate Report"**

### Step 2: Switch to Chart View
1. Click **"Chart View"** button (appears after data is generated)
2. Select a metric from the dropdown
3. The chart will render automatically

### Step 3: Analyze the Visualization
- **Thin lines** show you the raw, per-second behavior
- **Thick dashed lines** show you the overall trend
- **Hover over lines** to see exact values
- **Compare colors** to see differences between servers/runs

## Example Use Cases

### Use Case 1: Buffer Pool Read Patterns
**Goal**: Compare how MySQL vs Percona Server handle buffer pool reads

**Steps**:
1. Select both servers, all runs
2. Select metric: `buffer_pool_reads`
3. Generate Report → Switch to Chart View
4. Select `buffer_pool_reads` from dropdown

**What to Look For**:
- **Thin lines**: Spikes indicate cache misses
- **Thick lines**: Overall read load trend
- **Comparison**: Which server has more stable reads?

### Use Case 2: Row Operation Throughput
**Goal**: Track insert/update rates over time

**Steps**:
1. Select one server, one run
2. Select metrics: `innodb_rows_inserted`, `innodb_rows_updated`
3. Generate Report → Chart View
4. Toggle between metrics in dropdown

**What to Look For**:
- **Thin lines**: Second-to-second variation in operations
- **Thick lines**: Sustained operation rate
- **Patterns**: Warm-up period, steady state, cool-down

### Use Case 3: Lock Contention Analysis
**Goal**: Identify when and where lock waits occur

**Steps**:
1. Select all servers, all runs
2. Select metrics: `lock_row_lock_waits`, `lock_deadlocks`
3. Generate Report → Chart View
4. Compare `lock_row_lock_waits` across servers

**What to Look For**:
- **Spikes in thin lines**: Moments of high contention
- **Thick line elevation**: Sustained contention periods
- **Server comparison**: Which handles locks better?

### Use Case 4: Page Flush Behavior
**Goal**: Understand page flushing patterns

**Steps**:
1. Select both servers, multiple runs
2. Select: `buffer_pool_pages_flushed`
3. Generate Report → Chart View

**What to Look For**:
- **Thin lines**: Individual flush operations
- **Thick lines**: Average flush rate
- **Run consistency**: Are patterns repeatable?

## Chart Interpretation Guide

### Reading Thin Lines (Per-Second)
```
Value
  ^
  |     /\    /\
  |    /  \  /  \     ← Spikes show momentary changes
  |   /    \/    \
  |  /            \
  |_________________> Time
```

**Thin lines are good for**:
- Detecting anomalies and spikes
- Seeing instantaneous behavior
- Understanding variability and volatility

### Reading Thick Lines (Minute Average)
```
Value
  ^
  |     ______
  |    /      \___     ← Smooth trend shows pattern
  |   /           \__
  |  /               \
  |_________________> Time
```

**Thick lines are good for**:
- Identifying overall trends
- Filtering out noise
- Comparing sustained performance

### Combined Analysis
```
Value
  ^
  | Thin: /\/\/\/\    ← High variance
  | Thick: ————————   ← Stable average
  |
  | Thin: ___________  ← Low variance
  | Thick: ___________  ← Stable average
  |_________________> Time
```

When **thin and thick lines diverge**:
- **High variability**: Unstable, spiky behavior
- System is reacting to load changes

When **thin and thick lines align**:
- **Low variability**: Stable, predictable behavior
- System is in steady state

## Technical Details

### Per-Second Data
- Raw values from `.innodb.txt` files
- One data point per second
- Shows actual measurements without processing

### Minute Averages
- Calculated by averaging all seconds in each minute
- 60 seconds → 1 average value
- Applied across the entire minute (step function)

### Calculation Example
```
Seconds 0-59:   [120, 130, 125, 135, ...]  → Average: 127.5
Seconds 60-119: [150, 145, 155, 148, ...]  → Average: 149.5
Seconds 120-179: [140, 138, 142, 145, ...] → Average: 141.2
```

The thick line shows: 127.5 for [0-59], 149.5 for [60-119], 141.2 for [120-179]

### Color Palette
- 10 distinct colors rotate for multiple combinations
- Colors: Red, Blue, Yellow, Teal, Purple, Orange, Gray, etc.
- Consistent color per server+run across all charts

### Chart Library
- **Chart.js v4.4.0**: Modern, responsive charting library
- Loaded from CDN: `https://cdn.jsdelivr.net/npm/chart.js@4.4.0`
- Interactive tooltips, zoom, and hover effects

## Performance Considerations

### Data Points
- ~800 seconds per run = ~800 per-second data points
- 6 server+run combinations = ~4,800 thin line points
- 60-second averaging = ~14 thick line segments per run
- Total: ~5,000 data points per chart (very fast)

### Browser Rendering
- Chart.js uses Canvas API (hardware-accelerated)
- Smooth rendering even with thousands of points
- Responsive design adapts to window size

### Memory Usage
- Data already loaded for table view
- Charts reuse the same data (no extra fetch)
- Canvas rendering is memory-efficient

## Tips and Best Practices

### Tip 1: Start with Fewer Metrics
- Select 2-3 metrics first
- Generate and explore charts
- Add more metrics as needed

### Tip 2: Compare Similar Metrics
- Group related metrics together
- Example: All `buffer_pool_*` metrics
- Helps identify correlations

### Tip 3: Use Both Views
- **Table**: For exact numbers and detailed inspection
- **Charts**: For patterns and visual comparison
- Switch between them as needed

### Tip 4: Look for Patterns
- **Ramp-up**: System warming up
- **Steady state**: Normal operation
- **Spikes**: Anomalies or load changes
- **Decline**: Cool-down or degradation

### Tip 5: Compare Across Runs
- Select multiple runs (1, 2, 3)
- Check if patterns are consistent
- Identify outliers or anomalies

## Troubleshooting

### Chart doesn't appear
- Ensure you clicked "Generate Report" first
- Check that you selected at least one metric
- Verify Chart.js loaded (check browser console)

### No data in chart
- Verify the metric has numeric values
- Check that data files loaded successfully
- Ensure selected combinations have data

### Chart looks cluttered
- Reduce number of server+run combinations
- Focus on 2-3 combinations at a time
- Use table view for detailed inspection

### Lines are hard to distinguish
- Hover over lines to highlight them
- Refer to the color legend below chart
- Zoom in on time range of interest

## Keyboard Shortcuts

- **Enter**: Generate Report (when in input fields)
- **Click**: Switch between Table/Chart views
- **Dropdown**: Select different metrics quickly

## Future Enhancements (Possible)

1. **Multiple metrics on one chart**: Overlay different metrics
2. **Y-axis options**: Linear, logarithmic scales
3. **Time range selector**: Zoom into specific periods
4. **Export chart**: Save as PNG/SVG
5. **Comparison mode**: Side-by-side charts
6. **Annotation**: Mark interesting points
7. **Statistical overlays**: Standard deviation bands
8. **Download data**: Export chart data as CSV

## Summary

The chart visualization provides:
- ✅ **Dual-layer view**: Raw data + smoothed trends
- ✅ **Interactive tooltips**: Precise values on hover
- ✅ **Color-coded comparisons**: Easy visual distinction
- ✅ **Fast rendering**: Thousands of points, smooth performance
- ✅ **Flexible analysis**: Switch between table and chart views
- ✅ **Insight discovery**: Patterns, spikes, and trends at a glance

Use charts to **see the big picture**, then use tables to **dig into the details**! 📊
