#!/usr/bin/env python3
"""
mutex_metrics_report.py

Scans benchmark_logs/ for *.mutex_metrics.csv files, parses mutex data, and
generates an interactive HTML with multi-select controls for servers, runs, and mutexes.
Data is split into separate JSON files for dynamic loading.

Usage:
  python3 mutex_metrics_report.py [base_dir] [output_file] [data_dir_suffix]

Defaults:
  base_dir         = "benchmark_logs"
  output_file      = "mutex_metrics_report.html"
  data_dir_suffix  = "" (creates "mutex_data" directory)

Examples:
  python3 mutex_metrics_report.py benchmark_logs report.html
  python3 mutex_metrics_report.py benchmark_logs report.html "_disabled_binlog"
    -> Creates mutex_data_disabled_binlog/ directory
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict


def parse_mutex_file(path: str) -> Optional[Dict]:
    """Parse a single mutex metrics CSV file."""
    parts = Path(path).parts

    # Expected: benchmark_logs/{db_type}/{version}/run{N}_Tier{M}G_RW_{T}th.mutex_metrics.csv
    if len(parts) < 4:
        print(f"  Warning: Skipping unexpected path structure: {path}")
        return None

    db_type = parts[-3]
    version = parts[-2]
    filename = parts[-1]

    # Extract run number and thread count
    # Expected format: run{N}_Tier{M}G_RW_{T}th.mutex_metrics.csv
    run_match = os.path.basename(filename).split('_')[0]
    if not run_match.startswith('run'):
        print(f"  Warning: Cannot parse run number from filename: {filename}")
        return None

    run_number = run_match.replace('run', '')

    # Extract thread count
    import re
    thread_match = re.search(r'_(\d+)th\.', filename)
    if not thread_match:
        print(f"  Warning: Cannot parse thread count from filename: {filename}")
        return None

    threads = thread_match.group(1)
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
    all_mutex_names = set()

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        values = line.split(',')
        if len(values) >= len(header):
            row_dict = {header[i]: values[i] if i < len(values) else '' for i in range(len(header))}
            data_rows.append(row_dict)
            if 'name' in row_dict:
                all_mutex_names.add(row_dict['name'])

    if not data_rows:
        print(f"  Warning: No valid data rows in: {path}")
        return None

    return {
        'server': server,
        'run': run_number,
        'threads': threads,
        'filename': filename,
        'mutex_names': sorted(all_mutex_names),
        'data': data_rows
    }


def sanitize_filename(s: str) -> str:
    """Convert server name to safe filename."""
    return s.replace(' ', '_').replace('/', '-').replace('.', '_')


def main():
    args = sys.argv[1:]
    base_dir = args[0] if len(args) >= 1 else "benchmark_logs"
    default_output = "mutex_metrics_report.html"
    output_file = args[1] if len(args) >= 2 else default_output
    data_dir_suffix = args[2] if len(args) >= 3 else ""

    print(f"Scanning: {base_dir}")
    if data_dir_suffix:
        print(f"Data directory suffix: {data_dir_suffix}")

    # Find all mutex metrics files
    base_path = Path(base_dir)
    if not base_path.exists():
        print(f"Error: Directory '{base_dir}' does not exist")
        sys.exit(1)

    files = list(base_path.rglob("*.mutex_metrics.csv"))

    if len(files) == 0:
        print(f"Error: No .mutex_metrics.csv files found under '{base_dir}'")
        sys.exit(1)

    print(f"Found {len(files)} file(s)")

    # Parse each file
    parsed_files = []
    all_mutex_names = set()
    all_servers = set()
    all_runs = set()
    all_threads = set()

    for filepath in files:
        result = parse_mutex_file(str(filepath))
        if result:
            parsed_files.append(result)
            all_mutex_names.update(result['mutex_names'])
            all_servers.add(result['server'])
            all_runs.add(result['run'])
            all_threads.add(result['threads'])

    if len(parsed_files) == 0:
        print("Error: No valid data could be parsed from the files found.")
        sys.exit(1)

    # Sort for consistent ordering
    servers_sorted = sorted(all_servers)
    runs_sorted = sorted(all_runs, key=lambda x: int(x))
    threads_sorted = sorted(all_threads, key=lambda x: int(x))
    mutex_names_sorted = sorted(all_mutex_names)

    print(f"Parsed {len(parsed_files)} files")
    print(f"  Servers: {', '.join(servers_sorted)}")
    print(f"  Runs: {', '.join(runs_sorted)}")
    print(f"  Threads: {', '.join(threads_sorted)}")
    print(f"  Mutex Names: {len(mutex_names_sorted)}")

    # Create data directory for JSON files
    output_dir = Path(output_file).parent
    data_dir_name = f"mutex_data{data_dir_suffix}"
    data_dir = output_dir / data_dir_name
    data_dir.mkdir(exist_ok=True)

    # Write separate JSON files for each server+run+threads
    data_manifest = {}
    csv_manifest = {}
    for pf in parsed_files:
        server = pf['server']
        run = pf['run']
        threads = pf['threads']
        key = f"{server}||{run}||{threads}"

        # Create safe filename
        safe_name = f"{sanitize_filename(server)}_run{run}_{threads}th.json"
        json_path = data_dir / safe_name

        # Write JSON file
        with open(json_path, 'w') as f:
            json.dump({
                'server': server,
                'run': run,
                'threads': threads,
                'filename': pf['filename'],
                'mutex_names': pf['mutex_names'],
                'data': pf['data']
            }, f, separators=(',', ':'))

        data_manifest[key] = f"{data_dir_name}/{safe_name}"

        # Store CSV path relative to HTML file
        # Find the original CSV file path
        csv_files = list(base_path.rglob(f"*{pf['filename']}"))
        if csv_files:
            csv_path = csv_files[0]
            # Make path relative to output file directory
            try:
                rel_csv_path = os.path.relpath(csv_path, output_dir)
                csv_manifest[key] = rel_csv_path
            except ValueError:
                # If relative path fails, use absolute path
                csv_manifest[key] = str(csv_path)

        print(f"  Written: {json_path} ({os.path.getsize(json_path) / 1024:.1f} KB)")

    # Generate HTML with mutex-specific interface
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>InnoDB Mutex Metrics Analysis</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1600px;
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
            grid-template-columns: 1fr 1fr 1fr 2fr;
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
            font-size: 12px;
        }}
        th {{
            background: #f8f9fa;
            padding: 10px 6px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #dee2e6;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td {{
            padding: 8px 6px;
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
        .mutex-name {{
            font-weight: 600;
            color: #007bff;
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
        .file-size-info {{
            background: #e8f5e9;
            padding: 10px 15px;
            border-radius: 4px;
            border-left: 4px solid #4caf50;
            margin-bottom: 20px;
            font-size: 13px;
            color: #2e7d32;
        }}
        .mutex-multiselect {{
            position: relative;
        }}
        .mutex-search {{
            width: 100%;
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }}
        .mutex-search:focus {{
            outline: none;
            border-color: #007bff;
        }}
        .mutex-dropdown {{
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
        .mutex-dropdown.show {{
            display: block;
        }}
        .mutex-option {{
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .mutex-option:hover {{
            background: #f0f0f0;
        }}
        .mutex-option input[type="checkbox"] {{
            cursor: pointer;
        }}
        .mutex-option.hidden {{
            display: none;
        }}
        .selected-mutexes {{
            margin-top: 8px;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            min-height: 24px;
        }}
        .mutex-tag {{
            background: #007bff;
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .mutex-tag-remove {{
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            line-height: 1;
        }}
        .mutex-tag-remove:hover {{
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
        .view-toggle {{
            display: flex;
            gap: 10px;
            margin-top: 20px;
            justify-content: center;
        }}
        .view-toggle button {{
            margin-top: 0;
        }}
        .view-toggle button.active {{
            background: #0056b3;
        }}
        .chart-container {{
            margin-top: 30px;
            display: none;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .chart-container.show {{
            display: block;
        }}
        .chart-wrapper {{
            position: relative;
            height: 600px;
            margin-bottom: 40px;
        }}
        .chart-title {{
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 15px;
            text-align: center;
        }}
        .legend-custom {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            justify-content: center;
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
        }}
        .legend-color {{
            width: 30px;
            height: 3px;
            border-radius: 2px;
        }}
        .chart-controls {{
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
        }}
        .chart-controls label {{
            margin: 0;
        }}
        .chart-controls select {{
            padding: 6px 10px;
            font-size: 13px;
        }}
        .download-links {{
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
            border-left: 4px solid #28a745;
        }}
        .download-links h3 {{
            margin: 0 0 10px 0;
            font-size: 16px;
            color: #333;
        }}
        .download-link {{
            display: inline-block;
            margin: 5px 10px 5px 0;
            padding: 6px 12px;
            background: #28a745;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 13px;
            transition: background 0.2s;
        }}
        .download-link:hover {{
            background: #218838;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>InnoDB Mutex Metrics Analysis</h1>
        <p class="subtitle">Interactive comparison of mutex metrics (spins, waits, calls) across servers and runs</p>

        <div class="file-size-info">
            <strong>Optimized:</strong> Data is loaded dynamically on demand. Only selected data is fetched from the server.
        </div>

        <div class="info">
            <strong>Instructions:</strong> Select servers, runs, threads, and one or more mutex names to display.
            The table will show spins, waits, and calls for each selected mutex over time.
            Use the search box to filter mutex names.
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
                <label for="threadSelect">Threads</label>
                <select id="threadSelect" multiple size="5">
                    {chr(10).join(f'<option value="{t}">{t} threads</option>' for t in threads_sorted)}
                </select>
            </div>

            <div class="control-group">
                <label for="mutexSearch">Mutex Names (searchable, multi-select)</label>
                <div class="mutex-multiselect">
                    <input type="text" id="mutexSearch" class="mutex-search" placeholder="Search mutex names..." autocomplete="off">
                    <div id="mutexDropdown" class="mutex-dropdown">
                        <div class="select-all-container" onclick="toggleSelectAll()">
                            <input type="checkbox" id="selectAllCheckbox"> Select All / Deselect All
                        </div>
                        <div id="mutexOptions">
                            {chr(10).join(f'<div class="mutex-option" data-mutex="{m}"><input type="checkbox" value="{m}" id="mutex_{i}" onchange="updateSelectedMutexes()"><label for="mutex_{i}">{m}</label></div>' for i, m in enumerate(mutex_names_sorted))}
                        </div>
                        <div id="noResults" class="no-results" style="display: none;">No mutex names found</div>
                    </div>
                    <div id="selectedMutexes" class="selected-mutexes"></div>
                </div>
            </div>
        </div>

        <button id="generateBtn" onclick="generateData()">Generate Report</button>

        <div class="view-toggle" id="viewToggle" style="display: none;">
            <button id="tableViewBtn" class="active" onclick="switchView('table')">Table View</button>
            <button id="chartViewBtn" onclick="switchView('chart')">Chart View</button>
        </div>

        <div class="download-links" id="downloadLinks" style="display: none;">
            <h3>Download Source CSV Files</h3>
            <div id="downloadLinksContainer"></div>
        </div>

        <div class="table-container" id="tableView">
            <div id="tableContent" class="no-data">
                Select servers, runs, threads, and one or more mutex names, then click "Generate Report" to view data.
            </div>
        </div>

        <div class="chart-container" id="chartView">
            <div class="chart-controls">
                <label for="chartMutexSelect">Select Mutex for Chart:</label>
                <select id="chartMutexSelect" onchange="updateChartMutex()">
                    <option value="">-- Select mutex --</option>
                </select>
                <label for="chartMetricSelect">Select Metric:</label>
                <select id="chartMetricSelect" onchange="updateChart()">
                    <option value="spins">Spins</option>
                    <option value="waits">Waits</option>
                    <option value="calls">Calls</option>
                </select>
            </div>
            <div id="chartsContainer"></div>
        </div>
    </div>

    <script>
        // Manifest mapping server+run keys to JSON file paths
        const DATA_MANIFEST = {json.dumps(data_manifest, separators=(',', ':'))};

        // Manifest mapping server+run keys to source CSV file paths
        const CSV_MANIFEST = {json.dumps(csv_manifest, separators=(',', ':'))};

        // Cache for loaded data
        const dataCache = {{}};

        // Mutex multiselect state
        let selectedMutexes = new Set();

        // Chart state
        let chartInstances = {{}};
        let currentView = 'table';
        let loadedCombinations = [];

        // Initialize mutex search and dropdown
        document.addEventListener('DOMContentLoaded', function() {{
            const mutexSearch = document.getElementById('mutexSearch');
            const mutexDropdown = document.getElementById('mutexDropdown');

            // Show dropdown when search box is focused
            mutexSearch.addEventListener('focus', function() {{
                mutexDropdown.classList.add('show');
            }});

            // Filter mutexes on input
            mutexSearch.addEventListener('input', function() {{
                filterMutexes(this.value);
            }});

            // Close dropdown when clicking outside
            document.addEventListener('click', function(e) {{
                if (!e.target.closest('.mutex-multiselect')) {{
                    mutexDropdown.classList.remove('show');
                }}
            }});
        }});

        function filterMutexes(searchTerm) {{
            const options = document.querySelectorAll('.mutex-option');
            const noResults = document.getElementById('noResults');
            let visibleCount = 0;

            searchTerm = searchTerm.toLowerCase();

            options.forEach(option => {{
                const mutexName = option.dataset.mutex.toLowerCase();
                if (mutexName.includes(searchTerm)) {{
                    option.classList.remove('hidden');
                    visibleCount++;
                }} else {{
                    option.classList.add('hidden');
                }}
            }});

            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        }}

        function updateSelectedMutexes() {{
            const checkboxes = document.querySelectorAll('.mutex-option input[type="checkbox"]');
            selectedMutexes.clear();

            checkboxes.forEach(cb => {{
                if (cb.checked) {{
                    selectedMutexes.add(cb.value);
                }}
            }});

            displaySelectedMutexes();
            updateSelectAllCheckbox();
        }}

        function displaySelectedMutexes() {{
            const container = document.getElementById('selectedMutexes');
            container.innerHTML = '';

            if (selectedMutexes.size === 0) {{
                container.innerHTML = '<span style="color: #999; font-size: 12px;">No mutexes selected</span>';
                return;
            }}

            Array.from(selectedMutexes).sort().forEach(mutex => {{
                const tag = document.createElement('div');
                tag.className = 'mutex-tag';
                tag.innerHTML = `
                    <span>${{mutex}}</span>
                    <span class="mutex-tag-remove" onclick="removeMutex('${{mutex}}')">&times;</span>
                `;
                container.appendChild(tag);
            }});
        }}

        function removeMutex(mutex) {{
            selectedMutexes.delete(mutex);
            const checkbox = document.querySelector(`.mutex-option input[value="${{mutex}}"]`);
            if (checkbox) {{
                checkbox.checked = false;
            }}
            displaySelectedMutexes();
            updateSelectAllCheckbox();
        }}

        function toggleSelectAll() {{
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            const visibleCheckboxes = document.querySelectorAll('.mutex-option:not(.hidden) input[type="checkbox"]');
            const allChecked = selectAllCheckbox.checked;

            visibleCheckboxes.forEach(cb => {{
                cb.checked = !allChecked;
            }});

            selectAllCheckbox.checked = !allChecked;
            updateSelectedMutexes();
        }}

        function updateSelectAllCheckbox() {{
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            const visibleCheckboxes = document.querySelectorAll('.mutex-option:not(.hidden) input[type="checkbox"]');
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

        async function generateData() {{
            const serverSelect = document.getElementById('serverSelect');
            const runSelect = document.getElementById('runSelect');
            const threadSelect = document.getElementById('threadSelect');
            const errorMsg = document.getElementById('errorMsg');
            const tableContent = document.getElementById('tableContent');
            const generateBtn = document.getElementById('generateBtn');

            // Get selected values
            const selectedServers = Array.from(serverSelect.selectedOptions).map(o => o.value);
            const selectedRuns = Array.from(runSelect.selectedOptions).map(o => o.value);
            const selectedThreads = Array.from(threadSelect.selectedOptions).map(o => o.value);
            const selectedMutexList = Array.from(selectedMutexes);

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
            if (selectedThreads.length === 0) {{
                errorMsg.textContent = 'Please select at least one thread count.';
                errorMsg.style.display = 'block';
                return;
            }}
            if (selectedMutexList.length === 0) {{
                errorMsg.textContent = 'Please select at least one mutex name.';
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
                    for (const threads of selectedThreads) {{
                        const key = `${{server}}||${{run}}||${{threads}}`;
                        if (DATA_MANIFEST[key]) {{
                            combinations.push({{ server, run, threads, key }});
                            loadPromises.push(loadData(key));
                        }}
                    }}
                }}
            }}

            if (combinations.length === 0) {{
                tableContent.innerHTML = '<div class="no-data">No data available for the selected combination.</div>';
                generateBtn.disabled = false;
                return;
            }}

            // Wait for all data to load
            const loadedData = await Promise.all(loadPromises);
            generateBtn.disabled = false;

            // Build table with mutex data
            let html = '<table><thead><tr>';
            html += '<th>Timestamp</th>';
            html += '<th>Mutex Name</th>';

            const validCombinations = [];
            for (let i = 0; i < combinations.length; i++) {{
                if (loadedData[i]) {{
                    validCombinations.push({{ ...combinations[i], data: loadedData[i] }});
                    html += `<th colspan="3">${{combinations[i].server}}<br/>Run ${{combinations[i].run}}<br/>${{combinations[i].threads}} threads</th>`;
                }}
            }}

            html += '</tr><tr>';
            html += '<th></th><th></th>';

            // Add metric headers (spins, waits, calls) for each combination
            for (const combo of validCombinations) {{
                html += '<th style="font-size: 11px;">Spins</th>';
                html += '<th style="font-size: 11px;">Waits</th>';
                html += '<th style="font-size: 11px;">Calls</th>';
            }}

            html += '</tr></thead><tbody>';

            if (validCombinations.length === 0) {{
                tableContent.innerHTML = '<div class="no-data">Failed to load data for selected combinations.</div>';
                return;
            }}

            // Organize data by timestamp and mutex name
            const timestampMap = {{}};

            for (const combo of validCombinations) {{
                for (const row of combo.data.data) {{
                    const timestamp = row.timestamp_human || row.timestamp_unix;
                    const mutexName = row.name;

                    if (!selectedMutexList.includes(mutexName)) {{
                        continue;
                    }}

                    if (!timestampMap[timestamp]) {{
                        timestampMap[timestamp] = {{}};
                    }}
                    if (!timestampMap[timestamp][mutexName]) {{
                        timestampMap[timestamp][mutexName] = {{}};
                    }}

                    const comboKey = `${{combo.server}}||${{combo.run}}||${{combo.threads}}`;
                    timestampMap[timestamp][mutexName][comboKey] = {{
                        spins: row.spins || '',
                        waits: row.waits || '',
                        calls: row.calls || ''
                    }};
                }}
            }}

            // Build rows
            const sortedTimestamps = Object.keys(timestampMap).sort();

            for (const timestamp of sortedTimestamps) {{
                const mutexes = timestampMap[timestamp];
                const sortedMutexNames = Object.keys(mutexes).sort();

                for (let i = 0; i < sortedMutexNames.length; i++) {{
                    const mutexName = sortedMutexNames[i];
                    html += '<tr>';

                    if (i === 0) {{
                        html += `<td class="timestamp" rowspan="${{sortedMutexNames.length}}">${{timestamp}}</td>`;
                    }}

                    html += `<td class="mutex-name">${{mutexName}}</td>`;

                    for (const combo of validCombinations) {{
                        const comboKey = `${{combo.server}}||${{combo.run}}||${{combo.threads}}`;
                        const data = mutexes[mutexName][comboKey] || {{ spins: '-', waits: '-', calls: '-' }};

                        html += `<td class="metric-value">${{data.spins}}</td>`;
                        html += `<td class="metric-value">${{data.waits}}</td>`;
                        html += `<td class="metric-value">${{data.calls}}</td>`;
                    }}

                    html += '</tr>';
                }}
            }}

            html += '</tbody></table>';
            tableContent.innerHTML = html;

            // Store loaded combinations for chart generation
            loadedCombinations = validCombinations;

            // Populate chart mutex selector
            const chartMutexSelect = document.getElementById('chartMutexSelect');
            chartMutexSelect.innerHTML = '<option value="">-- Select mutex --</option>';
            selectedMutexList.forEach(mutex => {{
                const option = document.createElement('option');
                option.value = mutex;
                option.textContent = mutex;
                chartMutexSelect.appendChild(option);
            }});

            // Show view toggle
            document.getElementById('viewToggle').style.display = 'flex';

            // Populate download links
            const downloadLinksContainer = document.getElementById('downloadLinksContainer');
            const downloadLinksSection = document.getElementById('downloadLinks');
            downloadLinksContainer.innerHTML = '';

            let hasDownloadLinks = false;
            for (const combo of validCombinations) {{
                const comboKey = `${{combo.server}}||${{combo.run}}||${{combo.threads}}`;
                const csvPath = CSV_MANIFEST[comboKey];
                if (csvPath) {{
                    const link = document.createElement('a');
                    link.href = csvPath;
                    link.className = 'download-link';
                    link.download = '';
                    link.textContent = `${{combo.server}} Run ${{combo.run}} ${{combo.threads}}th`;
                    downloadLinksContainer.appendChild(link);
                    hasDownloadLinks = true;
                }}
            }}

            if (hasDownloadLinks) {{
                downloadLinksSection.style.display = 'block';
            }} else {{
                downloadLinksSection.style.display = 'none';
            }}
        }}

        function switchView(view) {{
            currentView = view;
            const tableView = document.getElementById('tableView');
            const chartView = document.getElementById('chartView');
            const tableBtn = document.getElementById('tableViewBtn');
            const chartBtn = document.getElementById('chartViewBtn');

            if (view === 'table') {{
                tableView.style.display = 'block';
                chartView.classList.remove('show');
                tableBtn.classList.add('active');
                chartBtn.classList.remove('active');
            }} else {{
                tableView.style.display = 'none';
                chartView.classList.add('show');
                tableBtn.classList.remove('active');
                chartBtn.classList.add('active');
                updateChart();
            }}
        }}

        function updateChartMutex() {{
            updateChart();
        }}

        function generateColorPalette(count) {{
            const colors = [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
            ];
            const palette = [];
            for (let i = 0; i < count; i++) {{
                palette.push(colors[i % colors.length]);
            }}
            return palette;
        }}

        function updateChart() {{
            const selectedMutex = document.getElementById('chartMutexSelect').value;
            const selectedMetric = document.getElementById('chartMetricSelect').value;

            if (!selectedMutex || !selectedMetric || loadedCombinations.length === 0) {{
                return;
            }}

            // Clear existing charts
            Object.values(chartInstances).forEach(chart => chart.destroy());
            chartInstances = {{}};

            const chartsContainer = document.getElementById('chartsContainer');
            chartsContainer.innerHTML = '';

            const colors = generateColorPalette(loadedCombinations.length);

            // Create chart
            const chartWrapper = document.createElement('div');
            chartWrapper.className = 'chart-wrapper';

            const chartTitle = document.createElement('div');
            chartTitle.className = 'chart-title';
            chartTitle.textContent = `${{selectedMutex}} - ${{selectedMetric.charAt(0).toUpperCase() + selectedMetric.slice(1)}}`;

            const canvas = document.createElement('canvas');
            canvas.id = `chart_${{selectedMutex}}_${{selectedMetric}}`;

            chartWrapper.appendChild(chartTitle);
            chartWrapper.appendChild(canvas);
            chartsContainer.appendChild(chartWrapper);

            const datasets = [];
            const legendItems = [];

            loadedCombinations.forEach((combo, idx) => {{
                const color = colors[idx];
                const data = combo.data.data;

                // Filter for selected mutex and extract metric values
                const mutexData = data.filter(row => row.name === selectedMutex);
                const metricValues = mutexData.map(row => {{
                    const value = parseFloat(row[selectedMetric]);
                    return isNaN(value) ? null : value;
                }});

                if (metricValues.length > 0) {{
                    datasets.push({{
                        label: `${{combo.server}} Run ${{combo.run}} ${{combo.threads}}th`,
                        data: metricValues,
                        borderColor: color,
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 3,
                        tension: 0.1,
                        spanGaps: true
                    }});

                    legendItems.push({{
                        label: `${{combo.server}} Run ${{combo.run}} ${{combo.threads}}th`,
                        color: color
                    }});
                }}
            }});

            if (datasets.length === 0) {{
                chartsContainer.innerHTML = '<div class="no-data">No data available for selected mutex and metric.</div>';
                return;
            }}

            const maxLength = Math.max(...datasets.map(ds => ds.data.length));

            const ctx = canvas.getContext('2d');
            chartInstances[`${{selectedMutex}}_${{selectedMetric}}`] = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: Array.from({{ length: maxLength }}, (_, i) => i),
                    datasets: datasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{
                        mode: 'index',
                        intersect: false
                    }},
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        tooltip: {{
                            callbacks: {{
                                title: function(context) {{
                                    const index = context[0].label;
                                    return `Data Point: ${{index}}`;
                                }},
                                label: function(context) {{
                                    const label = context.dataset.label || '';
                                    const value = context.parsed.y;
                                    return `${{label}}: ${{value !== null ? value.toLocaleString() : 'N/A'}}`;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            type: 'linear',
                            title: {{
                                display: true,
                                text: 'Sample Index'
                            }}
                        }},
                        y: {{
                            title: {{
                                display: true,
                                text: selectedMetric.charAt(0).toUpperCase() + selectedMetric.slice(1)
                            }},
                            ticks: {{
                                callback: function(value) {{
                                    return value.toLocaleString();
                                }}
                            }}
                        }}
                    }}
                }}
            }});

            // Add custom legend
            const legend = document.createElement('div');
            legend.className = 'legend-custom';
            legendItems.forEach(item => {{
                const legendItem = document.createElement('div');
                legendItem.className = 'legend-item';
                legendItem.innerHTML = `
                    <div class="legend-color" style="background: ${{item.color}};"></div>
                    <span>${{item.label}}</span>
                `;
                legend.appendChild(legendItem);
            }});
            chartWrapper.appendChild(legend);
        }}

        // Allow Enter key to trigger generation
        document.addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                generateData();
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
    print(f"  HTML size: {html_size / 1024:.1f} KB")
    print(f"  Data files: {len(data_manifest)} JSON files in {data_dir}")
    print(f"Open in browser: file://{os.path.abspath(output_file)}")


if __name__ == '__main__':
    main()
