#!/usr/bin/env python3
"""
Generate HTML comparison reports for MySQL system and status variables
Compares MySQL, Percona Server, and Percona Server (Legacy) configurations
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple


def parse_vars_file(filepath: Path) -> Dict[str, str]:
    """Parse variables file (tab-separated) into dict"""
    variables = {}

    with open(filepath, 'r') as f:
        for line in f:
            line = line.rstrip('\n')
            if '\t' in line:
                parts = line.split('\t', 1)
                var_name = parts[0]
                var_value = parts[1] if len(parts) > 1 else ''
                variables[var_name] = var_value

    return variables


def parse_status_file(filepath: Path) -> Dict[str, str]:
    """Parse status file into dict, handling multi-line values"""
    variables = {}
    current_var = None
    current_val = []

    with open(filepath, 'r') as f:
        for line in f:
            # Check if line starts with a variable name (no leading whitespace, has tab)
            if '\t' in line and not line.startswith(' ') and not line.startswith('\n'):
                # Save previous variable if exists
                if current_var:
                    variables[current_var] = '\n'.join(current_val)

                # Parse new variable
                parts = line.rstrip('\n').split('\t', 1)
                current_var = parts[0]
                current_val = [parts[1] if len(parts) > 1 else '']
            elif current_var:
                # Continuation of multi-line value
                current_val.append(line.rstrip('\n'))

        # Save last variable
        if current_var:
            variables[current_var] = '\n'.join(current_val)

    return variables


def find_variable_files(base_dir: Path, filename: str) -> List[Tuple[str, Path]]:
    """
    Find all variable files in benchmark_logs structure
    Returns list of (server_label, file_path) tuples
    """
    files = []

    # Expected structure: benchmark_logs/{server}/{version}/Tier12G.{vars|status}.txt
    for server_dir in base_dir.iterdir():
        if not server_dir.is_dir():
            continue

        for version_dir in server_dir.iterdir():
            if not version_dir.is_dir():
                continue

            target_file = version_dir / filename
            if target_file.exists():
                # Create label: "MySQL 8.4.8" or "Percona Server 8.4.8-8-legacy"
                server_name = server_dir.name.replace('-', ' ').title()
                version = version_dir.name

                # Special handling for legacy
                if '-legacy' in version:
                    version_clean = version.replace('-legacy', '')
                    label = f"{server_name} {version_clean} (Legacy)"
                else:
                    label = f"{server_name} {version}"

                files.append((label, target_file))

    return sorted(files)


def generate_html(var_type: str, data: Dict[str, Dict[str, str]],
                  all_vars: List[str], output_file: Path, prefix: str = ""):
    """
    Generate HTML comparison for variables

    Args:
        var_type: "System Variables" or "Status Variables"
        data: dict of {server_label: {var_name: value}}
        all_vars: sorted list of all variable names
        output_file: output HTML file path
        prefix: optional prefix for title (e.g., "MySQL 8.4.8")
    """

    servers = sorted(data.keys())
    total_vars = len(all_vars)

    # Build title with optional prefix
    if prefix:
        title = f"{prefix} - {var_type} Comparison"
        h1_title = f"{prefix}: {var_type} Comparison"
    else:
        title = f"{var_type} Comparison - MySQL vs Percona Server"
        h1_title = f"{var_type} Comparison: {' vs '.join(servers)}"

    # Calculate statistics
    common_to_all = sorted([v for v in all_vars
                            if all(v in data[s] for s in servers)])

    # Find which have different values
    different_vals = []
    for var in common_to_all:
        values = [data[s][var] for s in servers]
        if len(set(values)) > 1:  # More than one unique value
            different_vals.append(var)

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #1a73e8;
            padding-bottom: 10px;
        }}
        .summary {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary h2 {{
            margin-top: 0;
            color: #1a73e8;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }}
        .stat-box {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #1a73e8;
        }}
        .stat-box .label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-box .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
            margin-top: 5px;
        }}
        .controls {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .controls label {{
            font-weight: 600;
            color: #333;
        }}
        .controls input {{
            padding: 8px 12px;
            border: 1px solid #ccc;
            border-radius: 6px;
            font-size: 14px;
            flex: 1;
            min-width: 250px;
        }}
        .controls select {{
            padding: 8px 12px;
            border: 1px solid #ccc;
            border-radius: 6px;
            font-size: 14px;
        }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        th {{
            background: #1a73e8;
            color: white;
            padding: 10px 8px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td {{
            padding: 8px;
            border-bottom: 1px solid #e0e0e0;
            vertical-align: top;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .var-name {{
            font-family: 'Courier New', monospace;
            font-weight: 600;
            color: #1a73e8;
            white-space: nowrap;
        }}
        .value-cell {{
            font-family: 'Courier New', monospace;
            font-size: 11px;
            word-break: break-word;
        }}
        .different {{
            background: #fff3e0;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 600;
            margin-left: 6px;
        }}
        .badge-diff {{
            background: #ff9800;
            color: white;
        }}
        .hidden {{
            display: none;
        }}
        .count-badge {{
            background: #666;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <h1>{h1_title}</h1>

    <div class="summary">
        <h2>Overview</h2>
        <div class="stats">
            <div class="stat-box">
                <div class="label">Total Variables</div>
                <div class="value">{total_vars}</div>
            </div>
            <div class="stat-box">
                <div class="label">Common to All</div>
                <div class="value">{len(common_to_all)}</div>
            </div>
            <div class="stat-box">
                <div class="label">Different Values</div>
                <div class="value">{len(different_vals)}</div>
            </div>
        </div>
        <p><strong>Configuration:</strong> Tier 12G (innodb_buffer_pool_size = 12GB)</p>
        <p><strong>Servers:</strong></p>
        <ul>
'''

    for server in servers:
        html += f'            <li><strong>{server}</strong></li>\n'

    html += '''        </ul>
    </div>

    <div class="controls">
        <label for="search">Search variables:</label>
        <input type="text" id="search" placeholder="Type to filter variables (e.g., innodb, buffer, thread)">

        <label for="filter">Filter:</label>
        <select id="filter">
            <option value="all">All Variables</option>
            <option value="different">Variables with Different Values</option>
            <option value="same">Variables with Same Values</option>
        </select>
    </div>
'''

    # Build table
    html += f'''
    <div class="section">
        <h2>All {var_type} <span class="count-badge" id="visibleCount">{total_vars} variables</span></h2>
        <table id="mainTable">
            <thead>
                <tr>
                    <th style="width: {100 // (len(servers) + 1)}%">Variable Name</th>
'''

    for server in servers:
        html += f'                    <th style="width: {100 // (len(servers) + 1)}%">{server}</th>\n'

    html += '''                </tr>
            </thead>
            <tbody>
'''

    # Add all variables
    for var in all_vars:
        # Get values for all servers
        values = [data[s].get(var, '') for s in servers]

        # Filter out empty values
        non_empty_values = [v for v in values if v]

        # Determine if different
        if not non_empty_values:
            # All are N/A - treat as same (not different)
            all_same = True
            any_different = False
        elif len(non_empty_values) != len(values):
            # Mix of N/A and actual values - mark as different
            all_same = False
            any_different = True
        else:
            # All have values - check if values are identical
            all_same = len(set(values)) == 1
            any_different = not all_same

        row_class = 'different' if any_different else ''
        badge = '<span class="badge badge-diff">DIFFERENT</span>' if any_different else ''
        category = 'same' if all_same else 'different'

        html += f'''
                <tr class="var-row {row_class}" data-var="{var.lower()}" data-category="{category}">
                    <td class="var-name">{var}{badge}</td>
'''

        for server in servers:
            value = data[server].get(var, '')
            display = value if value else '<em style="color:#999">N/A</em>'

            # Escape HTML
            if display != '<em style="color:#999">N/A</em>':
                display = display.replace('<', '&lt;').replace('>', '&gt;')

            # Truncate long values
            if len(display) > 200:
                display = display[:200] + '...'

            html += f'                    <td class="value-cell">{display}</td>\n'

        html += '                </tr>\n'

    html += '''
            </tbody>
        </table>
    </div>

    <script>
        const searchInput = document.getElementById('search');
        const filterSelect = document.getElementById('filter');
        const rows = document.querySelectorAll('.var-row');
        const countBadge = document.getElementById('visibleCount');

        function applyFilters() {
            const searchTerm = searchInput.value.toLowerCase();
            const filterValue = filterSelect.value;
            let visibleCount = 0;

            rows.forEach(row => {
                const varName = row.dataset.var;
                const category = row.dataset.category;

                // Check search match
                const matchesSearch = !searchTerm || varName.includes(searchTerm);

                // Check filter match
                let matchesFilter = true;
                if (filterValue === 'same') {
                    matchesFilter = category === 'same';
                } else if (filterValue === 'different') {
                    matchesFilter = category === 'different';
                }

                // Show/hide row
                if (matchesSearch && matchesFilter) {
                    row.classList.remove('hidden');
                    visibleCount++;
                } else {
                    row.classList.add('hidden');
                }
            });

            countBadge.textContent = visibleCount + ' variables';
        }

        searchInput.addEventListener('input', applyFilters);
        filterSelect.addEventListener('change', applyFilters);
    </script>
</body>
</html>
'''

    # Write to file
    with open(output_file, 'w') as f:
        f.write(html)

    print(f"✓ Generated: {output_file}")
    print(f"  Total variables: {total_vars}")
    print(f"  Common to all: {len(common_to_all)}")
    print(f"  Different values: {len(different_vals)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_variable_comparisons.py <benchmark_logs_dir> [prefix]")
        print("\nGenerates:")
        print("  <prefix>_system_variables.html")
        print("  <prefix>_status_variables.html")
        print("\nIf prefix is not provided, generates:")
        print("  system_variables_comparison.html")
        print("  status_variables_comparison.html")
        sys.exit(1)

    base_dir = Path(sys.argv[1])
    prefix = sys.argv[2] if len(sys.argv) > 2 else ""

    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}")
        sys.exit(1)

    print("Generating variable comparison reports...")
    print("=" * 60)

    # Generate System Variables comparison
    print("\n1. System Variables (Tier12G.vars.txt)")
    print("-" * 60)

    vars_files = find_variable_files(base_dir, "Tier12G.vars.txt")

    if not vars_files:
        print("  Warning: No Tier12G.vars.txt files found")
    else:
        vars_data = {}
        for label, filepath in vars_files:
            print(f"  Reading: {label} from {filepath}")
            vars_data[label] = parse_vars_file(filepath)

        all_vars = sorted(set().union(*[set(d.keys()) for d in vars_data.values()]))

        # Build output filename
        if prefix:
            output_file = Path(f"{prefix}_system_variables.html")
        else:
            output_file = Path("system_variables_comparison.html")

        generate_html(
            "System Variables",
            vars_data,
            all_vars,
            output_file,
            prefix
        )

    # Generate Status Variables comparison
    print("\n2. Status Variables (Tier12G.status.txt)")
    print("-" * 60)

    status_files = find_variable_files(base_dir, "Tier12G.status.txt")

    if not status_files:
        print("  Warning: No Tier12G.status.txt files found")
    else:
        status_data = {}
        for label, filepath in status_files:
            print(f"  Reading: {label} from {filepath}")
            status_data[label] = parse_status_file(filepath)

        all_status = sorted(set().union(*[set(d.keys()) for d in status_data.values()]))

        # Build output filename
        if prefix:
            output_file = Path(f"{prefix}_status_variables.html")
        else:
            output_file = Path("status_variables_comparison.html")

        generate_html(
            "Status Variables",
            status_data,
            all_status,
            output_file,
            prefix
        )

    print("\n" + "=" * 60)
    print("Done! Generated comparison reports in current directory.")


if __name__ == '__main__':
    main()
