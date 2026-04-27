#!/usr/bin/env python3
"""
innodb_metrics_report.py

Scans benchmark_logs/ for *.innodb.txt files, parses InnoDB metrics, and
generates an interactive HTML with multi-select controls for servers and runs.
Data is split into separate JSON files for dynamic loading.

Usage:
  python3 innodb_metrics_report.py [base_dir] [output_file]

Defaults:
  base_dir    = "benchmark_logs"
  output_file = "innodb_metrics_report.html"
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict


def parse_innodb_file(path: str) -> Optional[Dict]:
    """Parse a single InnoDB metrics file."""
    parts = Path(path).parts

    # Expected: benchmark_logs/{db_type}/{version}/run{N}_Tier{M}G_RW_{T}th.innodb.txt
    if len(parts) < 4:
        print(f"  Warning: Skipping unexpected path structure: {path}")
        return None

    db_type = parts[-3]
    version = parts[-2]
    filename = parts[-1]

    # Extract run number
    run_match = os.path.basename(filename).split('_')[0]
    if not run_match.startswith('run'):
        print(f"  Warning: Cannot parse run number from filename: {filename}")
        return None

    run_number = run_match.replace('run', '')
    server = f"{db_type} {version}"

    # Read CSV file
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  Warning: Failed to read {path}: {e}")
        return None

    if len(lines) < 2:
        print(f"  Warning: File has insufficient data: {path}")
        return None

    # Parse header and data
    header = lines[0].strip().split(',')
    data_rows = []

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        values = line.split(',')
        if len(values) == len(header):
            row_dict = {header[i]: values[i] for i in range(len(header))}
            data_rows.append(row_dict)

    if not data_rows:
        print(f"  Warning: No valid data rows in: {path}")
        return None

    return {
        'server': server,
        'run': run_number,
        'filename': filename,
        'metrics': header,
        'data': data_rows
    }


def sanitize_filename(s: str) -> str:
    """Convert server name to safe filename."""
    return s.replace(' ', '_').replace('/', '-').replace('.', '_')


def main():
    args = sys.argv[1:]
    base_dir = args[0] if len(args) >= 1 else "benchmark_logs"
    default_output = "innodb_metrics_report.html"
    output_file = args[1] if len(args) >= 2 else default_output

    print(f"Scanning: {base_dir}")

    # Find all InnoDB files
    base_path = Path(base_dir)
    if not base_path.exists():
        print(f"Error: Directory '{base_dir}' does not exist")
        sys.exit(1)

    files = list(base_path.rglob("*.innodb.txt"))

    if len(files) == 0:
        print(f"Error: No .innodb.txt files found under '{base_dir}'")
        sys.exit(1)

    print(f"Found {len(files)} file(s)")

    # Parse each file
    parsed_files = []
    all_metrics = set()
    all_servers = set()
    all_runs = set()

    for filepath in files:
        result = parse_innodb_file(str(filepath))
        if result:
            parsed_files.append(result)
            all_metrics.update(result['metrics'])
            all_servers.add(result['server'])
            all_runs.add(result['run'])

    if len(parsed_files) == 0:
        print("Error: No valid data could be parsed from the files found.")
        sys.exit(1)

    # Sort for consistent ordering
    servers_sorted = sorted(all_servers)
    runs_sorted = sorted(all_runs, key=lambda x: int(x))
    metrics_sorted = sorted(all_metrics)

    print(f"Parsed {len(parsed_files)} files")
    print(f"  Servers: {', '.join(servers_sorted)}")
    print(f"  Runs: {', '.join(runs_sorted)}")
    print(f"  Metrics: {len(metrics_sorted)}")

    # Create data directory for JSON files
    output_dir = Path(output_file).parent
    data_dir = output_dir / "innodb_data"
    data_dir.mkdir(exist_ok=True)

    # Write separate JSON files for each server+run
    data_manifest = {}
    for pf in parsed_files:
        server = pf['server']
        run = pf['run']
        key = f"{server}||{run}"

        # Create safe filename
        safe_name = f"{sanitize_filename(server)}_run{run}.json"
        json_path = data_dir / safe_name

        # Write JSON file
        with open(json_path, 'w') as f:
            json.dump({
                'server': server,
                'run': run,
                'filename': pf['filename'],
                'metrics': pf['metrics'],
                'data': pf['data']
            }, f, separators=(',', ':'))

        data_manifest[key] = f"innodb_data/{safe_name}"
        print(f"  Written: {json_path} ({os.path.getsize(json_path) / 1024:.1f} KB)")

    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>InnoDB Metrics Analysis</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 30px;
        }}
        .controls {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .control-group {{
            display: flex;
            flex-direction: column;
        }}
        label {{
            font-weight: 600;
            margin-bottom: 8px;
            color: #444;
            font-size: 14px;
        }}
        select {{
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            background: white;
            cursor: pointer;
            transition: border-color 0.2s;
        }}
        select:hover {{
            border-color: #007bff;
        }}
        select:focus {{
            outline: none;
            border-color: #007bff;
        }}
        button {{
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            margin-top: 24px;
        }}
        button:hover {{
            background: #0056b3;
        }}
        button:disabled {{
            background: #ccc;
            cursor: not-allowed;
        }}
        .table-container {{
            overflow-x: auto;
            margin-top: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th {{
            background: #f8f9fa;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #dee2e6;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td {{
            padding: 10px 8px;
            border-bottom: 1px solid #dee2e6;
            font-family: 'Monaco', 'Courier New', monospace;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .timestamp {{
            color: #666;
            white-space: nowrap;
        }}
        .metric-value {{
            text-align: right;
        }}
        .info {{
            background: #e7f3ff;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #007bff;
            margin-bottom: 20px;
        }}
        .error {{
            background: #ffe7e7;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #dc3545;
            margin-bottom: 20px;
            display: none;
        }}
        .no-data {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #007bff;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #007bff;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 20px;
            font-weight: 600;
            color: #333;
        }}
        .file-size-info {{
            background: #e8f5e9;
            padding: 10px 15px;
            border-radius: 4px;
            border-left: 4px solid #4caf50;
            margin-bottom: 20px;
            font-size: 13px;
            color: #2e7d32;
        }}
        .metric-multiselect {{
            position: relative;
        }}
        .metric-search {{
            width: 100%;
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }}
        .metric-search:focus {{
            outline: none;
            border-color: #007bff;
        }}
        .metric-dropdown {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 2px solid #007bff;
            border-top: none;
            border-radius: 0 0 4px 4px;
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .metric-dropdown.show {{
            display: block;
        }}
        .metric-option {{
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .metric-option:hover {{
            background: #f0f0f0;
        }}
        .metric-option input[type="checkbox"] {{
            cursor: pointer;
        }}
        .metric-option.hidden {{
            display: none;
        }}
        .selected-metrics {{
            margin-top: 8px;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            min-height: 24px;
        }}
        .metric-tag {{
            background: #007bff;
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .metric-tag-remove {{
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            line-height: 1;
        }}
        .metric-tag-remove:hover {{
            color: #ffcccc;
        }}
        .select-all-container {{
            padding: 8px 12px;
            border-bottom: 2px solid #ddd;
            background: #f8f9fa;
            font-weight: 600;
            cursor: pointer;
        }}
        .select-all-container:hover {{
            background: #e9ecef;
        }}
        .no-results {{
            padding: 12px;
            text-align: center;
            color: #999;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>InnoDB Metrics Analysis</h1>
        <p class="subtitle">Interactive comparison of InnoDB metrics across servers and runs</p>

        <div class="file-size-info">
            <strong>Optimized:</strong> Data is loaded dynamically on demand. Only selected data is fetched from the server.
        </div>

        <div class="info">
            <strong>Instructions:</strong> Select one or more servers, one or more runs, and one or more metrics to display.
            The table will show the selected metric values over time for each server+run combination.
            Use the search box to filter metrics by name.
        </div>

        <div class="error" id="errorMsg"></div>

        <div class="controls">
            <div class="control-group">
                <label for="serverSelect">Servers</label>
                <select id="serverSelect" multiple size="5">
                    {chr(10).join(f'<option value="{s}">{s}</option>' for s in servers_sorted)}
                </select>
            </div>

            <div class="control-group">
                <label for="runSelect">Runs</label>
                <select id="runSelect" multiple size="5">
                    {chr(10).join(f'<option value="{r}">Run {r}</option>' for r in runs_sorted)}
                </select>
            </div>

            <div class="control-group">
                <label for="metricSearch">Metrics (searchable, multi-select)</label>
                <div class="metric-multiselect">
                    <input type="text" id="metricSearch" class="metric-search" placeholder="Search metrics..." autocomplete="off">
                    <div id="metricDropdown" class="metric-dropdown">
                        <div class="select-all-container" onclick="toggleSelectAll()">
                            <input type="checkbox" id="selectAllCheckbox"> Select All / Deselect All
                        </div>
                        <div id="metricOptions">
                            {chr(10).join(f'<div class="metric-option" data-metric="{m}"><input type="checkbox" value="{m}" id="metric_{i}" onchange="updateSelectedMetrics()"><label for="metric_{i}">{m}</label></div>' for i, m in enumerate(metrics_sorted))}
                        </div>
                        <div id="noResults" class="no-results" style="display: none;">No metrics found</div>
                    </div>
                    <div id="selectedMetrics" class="selected-metrics"></div>
                </div>
            </div>
        </div>

        <button id="generateBtn" onclick="generateTable()">Generate Table</button>

        <div id="statsContainer" style="display: none;">
            <h3 style="margin-top: 30px;">Statistics</h3>
            <div class="stats" id="stats"></div>
        </div>

        <div class="table-container">
            <div id="tableContent" class="no-data">
                Select servers, runs, and one or more metrics, then click "Generate Table" to view data.
            </div>
        </div>
    </div>

    <script>
        // Manifest mapping server+run keys to JSON file paths
        const DATA_MANIFEST = {json.dumps(data_manifest, separators=(',', ':'))};

        // Cache for loaded data
        const dataCache = {{}};

        // Metric multiselect state
        let selectedMetrics = new Set();

        // Initialize metric search and dropdown
        document.addEventListener('DOMContentLoaded', function() {{
            const metricSearch = document.getElementById('metricSearch');
            const metricDropdown = document.getElementById('metricDropdown');

            // Show dropdown when search box is focused
            metricSearch.addEventListener('focus', function() {{
                metricDropdown.classList.add('show');
            }});

            // Filter metrics on input
            metricSearch.addEventListener('input', function() {{
                filterMetrics(this.value);
            }});

            // Close dropdown when clicking outside
            document.addEventListener('click', function(e) {{
                if (!e.target.closest('.metric-multiselect')) {{
                    metricDropdown.classList.remove('show');
                }}
            }});
        }});

        function filterMetrics(searchTerm) {{
            const options = document.querySelectorAll('.metric-option');
            const noResults = document.getElementById('noResults');
            let visibleCount = 0;

            searchTerm = searchTerm.toLowerCase();

            options.forEach(option => {{
                const metricName = option.dataset.metric.toLowerCase();
                if (metricName.includes(searchTerm)) {{
                    option.classList.remove('hidden');
                    visibleCount++;
                }} else {{
                    option.classList.add('hidden');
                }}
            }});

            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        }}

        function updateSelectedMetrics() {{
            const checkboxes = document.querySelectorAll('.metric-option input[type="checkbox"]');
            selectedMetrics.clear();

            checkboxes.forEach(cb => {{
                if (cb.checked) {{
                    selectedMetrics.add(cb.value);
                }}
            }});

            displaySelectedMetrics();
            updateSelectAllCheckbox();
        }}

        function displaySelectedMetrics() {{
            const container = document.getElementById('selectedMetrics');
            container.innerHTML = '';

            if (selectedMetrics.size === 0) {{
                container.innerHTML = '<span style="color: #999; font-size: 12px;">No metrics selected</span>';
                return;
            }}

            Array.from(selectedMetrics).sort().forEach(metric => {{
                const tag = document.createElement('div');
                tag.className = 'metric-tag';
                tag.innerHTML = `
                    <span>${{metric}}</span>
                    <span class="metric-tag-remove" onclick="removeMetric('${{metric}}')">&times;</span>
                `;
                container.appendChild(tag);
            }});
        }}

        function removeMetric(metric) {{
            selectedMetrics.delete(metric);
            const checkbox = document.querySelector(`.metric-option input[value="${{metric}}"]`);
            if (checkbox) {{
                checkbox.checked = false;
            }}
            displaySelectedMetrics();
            updateSelectAllCheckbox();
        }}

        function toggleSelectAll() {{
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            const visibleCheckboxes = document.querySelectorAll('.metric-option:not(.hidden) input[type="checkbox"]');
            const allChecked = selectAllCheckbox.checked;

            visibleCheckboxes.forEach(cb => {{
                cb.checked = !allChecked;
            }});

            selectAllCheckbox.checked = !allChecked;
            updateSelectedMetrics();
        }}

        function updateSelectAllCheckbox() {{
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            const visibleCheckboxes = document.querySelectorAll('.metric-option:not(.hidden) input[type="checkbox"]');
            const checkedCount = Array.from(visibleCheckboxes).filter(cb => cb.checked).length;

            selectAllCheckbox.checked = checkedCount === visibleCheckboxes.length && visibleCheckboxes.length > 0;
        }}

        async function loadData(key) {{
            if (dataCache[key]) {{
                return dataCache[key];
            }}

            const filePath = DATA_MANIFEST[key];
            if (!filePath) {{
                return null;
            }}

            try {{
                const response = await fetch(filePath);
                if (!response.ok) {{
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}
                const data = await response.json();
                dataCache[key] = data;
                return data;
            }} catch (error) {{
                console.error(`Failed to load data for ${{key}}:`, error);
                return null;
            }}
        }}

        async function generateTable() {{
            const serverSelect = document.getElementById('serverSelect');
            const runSelect = document.getElementById('runSelect');
            const errorMsg = document.getElementById('errorMsg');
            const tableContent = document.getElementById('tableContent');
            const statsContainer = document.getElementById('statsContainer');
            const statsDiv = document.getElementById('stats');
            const generateBtn = document.getElementById('generateBtn');

            // Get selected values
            const selectedServers = Array.from(serverSelect.selectedOptions).map(o => o.value);
            const selectedRuns = Array.from(runSelect.selectedOptions).map(o => o.value);
            const selectedMetricsList = Array.from(selectedMetrics);

            // Validation
            errorMsg.style.display = 'none';
            if (selectedServers.length === 0) {{
                errorMsg.textContent = 'Please select at least one server.';
                errorMsg.style.display = 'block';
                return;
            }}
            if (selectedRuns.length === 0) {{
                errorMsg.textContent = 'Please select at least one run.';
                errorMsg.style.display = 'block';
                return;
            }}
            if (selectedMetricsList.length === 0) {{
                errorMsg.textContent = 'Please select at least one metric.';
                errorMsg.style.display = 'block';
                return;
            }}

            // Show loading state
            tableContent.innerHTML = '<div class="loading">Loading data...</div>';
            generateBtn.disabled = true;

            // Load data for selected combinations
            const combinations = [];
            const loadPromises = [];

            for (const server of selectedServers) {{
                for (const run of selectedRuns) {{
                    const key = `${{server}}||${{run}}`;
                    if (DATA_MANIFEST[key]) {{
                        combinations.push({{ server, run, key }});
                        loadPromises.push(loadData(key));
                    }}
                }}
            }}

            if (combinations.length === 0) {{
                tableContent.innerHTML = '<div class="no-data">No data available for the selected combination.</div>';
                statsContainer.style.display = 'none';
                generateBtn.disabled = false;
                return;
            }}

            // Wait for all data to load
            const loadedData = await Promise.all(loadPromises);
            generateBtn.disabled = false;

            // Build table with multi-metric support
            let html = '<table><thead><tr>';
            html += '<th rowspan="2">Timestamp</th>';

            const validCombinations = [];
            for (let i = 0; i < combinations.length; i++) {{
                if (loadedData[i]) {{
                    validCombinations.push({{ ...combinations[i], data: loadedData[i] }});
                    html += `<th colspan="${{selectedMetricsList.length}}">${{combinations[i].server}}<br/>Run ${{combinations[i].run}}</th>`;
                }}
            }}

            html += '</tr><tr>';

            // Add metric headers for each combination
            for (const combo of validCombinations) {{
                for (const metric of selectedMetricsList) {{
                    html += `<th style="font-size: 11px;">${{metric}}</th>`;
                }}
            }}

            html += '</tr></thead><tbody>';

            if (validCombinations.length === 0) {{
                tableContent.innerHTML = '<div class="no-data">Failed to load data for selected combinations.</div>';
                statsContainer.style.display = 'none';
                return;
            }}

            // Find max rows
            let maxRows = 0;
            for (const combo of validCombinations) {{
                const rows = combo.data.data.length;
                if (rows > maxRows) maxRows = rows;
            }}

            // Calculate statistics for each metric
            const stats = {{}};
            for (const combo of validCombinations) {{
                for (const metric of selectedMetricsList) {{
                    const values = combo.data.data
                        .map(row => parseFloat(row[metric]))
                        .filter(v => !isNaN(v));

                    if (values.length > 0) {{
                        const sum = values.reduce((a, b) => a + b, 0);
                        const avg = sum / values.length;
                        const min = Math.min(...values);
                        const max = Math.max(...values);
                        const key = `${{combo.server}} Run ${{combo.run}} - ${{metric}}`;
                        stats[key] = {{ avg, min, max }};
                    }}
                }}
            }}

            // Build rows
            for (let i = 0; i < maxRows; i++) {{
                html += '<tr>';

                // Get timestamp from first available combo
                let timestamp = '';
                for (const combo of validCombinations) {{
                    if (combo.data.data[i]) {{
                        timestamp = combo.data.data[i].timestamp || i;
                        break;
                    }}
                }}
                html += `<td class="timestamp">${{timestamp}}</td>`;

                // Add metric values for each combination and metric
                for (const combo of validCombinations) {{
                    const row = combo.data.data[i];
                    for (const metric of selectedMetricsList) {{
                        if (row && row[metric] !== undefined) {{
                            const value = parseFloat(row[metric]);
                            const displayValue = isNaN(value) ? row[metric] : value.toLocaleString();
                            html += `<td class="metric-value">${{displayValue}}</td>`;
                        }} else {{
                            html += '<td class="metric-value">-</td>';
                        }}
                    }}
                }}

                html += '</tr>';
            }}

            html += '</tbody></table>';
            tableContent.innerHTML = html;

            // Display statistics
            let statsHtml = '';
            for (const [label, values] of Object.entries(stats)) {{
                statsHtml += `
                    <div class="stat-card">
                        <div class="stat-label">${{label}}</div>
                        <div class="stat-value">Avg: ${{values.avg.toFixed(2)}}</div>
                        <div style="font-size: 12px; color: #666; margin-top: 5px;">
                            Min: ${{values.min.toLocaleString()}} | Max: ${{values.max.toLocaleString()}}
                        </div>
                    </div>
                `;
            }}
            statsDiv.innerHTML = statsHtml;
            statsContainer.style.display = 'block';
        }}

        // Allow Enter key to trigger generation
        document.addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                generateTable();
            }}
        }});
    </script>
</body>
</html>
"""

    # Write output
    with open(output_file, 'w') as f:
        f.write(html_content)

    html_size = os.path.getsize(output_file)
    print(f"\nDone. Report written to: {output_file}")
    print(f"  HTML size: {html_size / 1024:.1f} KB (was ~53 MB)")
    print(f"  Data files: {len(data_manifest)} JSON files in {data_dir}")
    print(f"Open in browser: file://{os.path.abspath(output_file)}")


if __name__ == '__main__':
    main()
