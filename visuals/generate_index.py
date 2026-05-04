#!/usr/bin/env python3
"""
Generate index.html for all benchmark HTML reports
Scans current directory for generated HTML files and creates organized navigation
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


def find_html_reports(base_dir: Path) -> Dict[str, List[Tuple[str, Path, str]]]:
    """
    Find all HTML reports in the directory and categorize them
    Returns dict of {category: [(title, filepath, description)]}
    """
    reports = {
        'performance': [],
        'innodb': [],
        'variables': []
    }

    for html_file in base_dir.glob('*.html'):
        filename = html_file.name

        # Skip index.html itself
        if filename == 'index.html':
            continue

        # Categorize by filename patterns
        if 'sysbench' in filename.lower():
            # Detect binlog status from filename
            if 'enabled_binlog' in filename.lower() or 'enabled-binlog' in filename.lower():
                binlog_desc = 'Binary logging enabled'
            elif 'disabled_binlog' in filename.lower() or 'disabled-binlog' in filename.lower():
                binlog_desc = 'Binary logging disabled'
            elif 'binlog' in filename.lower():
                binlog_desc = 'Binary logging enabled'
            else:
                binlog_desc = 'Binary logging disabled'

            if 'average' in filename.lower():
                title = 'Sysbench Results - Averaged Across Runs'
                reports['performance'].append((title, html_file, binlog_desc))
            elif 'individual' in filename.lower():
                title = 'Sysbench Results - Individual Runs'
                reports['performance'].append((title, html_file, binlog_desc))
            else:
                title = filename.replace('.html', '').replace('_', ' ').title()
                reports['performance'].append((title, html_file, binlog_desc))

        elif 'innodb_metrics' in filename.lower():
            # Detect binlog status from filename
            if 'enabled_binlog' in filename.lower() or 'enabled-binlog' in filename.lower():
                title = 'InnoDB Metrics Analyzer (Binlog Enabled)'
                desc = '319 InnoDB metrics with binary logging enabled'
            elif 'disabled_binlog' in filename.lower() or 'disabled-binlog' in filename.lower():
                title = 'InnoDB Metrics Analyzer (Binlog Disabled)'
                desc = '319 InnoDB metrics with binary logging disabled'
            elif 'binlog' in filename.lower():
                title = 'InnoDB Metrics Analyzer (Binlog Enabled)'
                desc = '319 InnoDB metrics with binary logging enabled'
            else:
                title = 'InnoDB Metrics Analyzer (Binlog Disabled)'
                desc = '319 InnoDB metrics with binary logging disabled'
            reports['innodb'].append((title, html_file, desc))

        elif 'variable' in filename.lower() or 'status' in filename.lower():
            # Parse variable comparison files - check for specific patterns
            if 'enabled_binlog' in filename.lower() or 'enabled-binlog' in filename.lower():
                prefix = 'Binlog Enabled - '
                binlog_desc = 'Configuration with binary logging enabled'
            elif 'disabled_binlog' in filename.lower() or 'disabled-binlog' in filename.lower():
                prefix = 'Binlog Disabled - '
                binlog_desc = 'Configuration with binary logging disabled'
            elif 'binlog enabled' in filename.lower():
                prefix = 'Binlog Enabled - '
                binlog_desc = 'Configuration with binary logging enabled'
            else:
                prefix = ''
                binlog_desc = 'Configuration with binary logging disabled'

            if 'system_variable' in filename.lower():
                title = f'{prefix}System Variables Comparison'
            elif 'status_variable' in filename.lower():
                title = f'{prefix}Status Variables Comparison'
            else:
                title = filename.replace('.html', '').replace('_', ' ').title()

            reports['variables'].append((title, html_file, binlog_desc))

        else:
            # Unknown report type, add to variables as fallback
            title = filename.replace('.html', '').replace('_', ' ').title()
            reports['variables'].append((title, html_file, ''))

    # Sort each category
    for category in reports:
        reports[category].sort(key=lambda x: x[0])

    return reports


def generate_index_html(reports: Dict[str, List[Tuple[str, Path, str]]], output_file: Path, base_dir: Path):
    """Generate index.html with organized links to all reports"""

    total_reports = sum(len(r) for r in reports.values())
    generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>MySQL vs Percona Server Benchmark Reports</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        header {{
            text-align: center;
            color: white;
            margin-bottom: 50px;
        }}
        header h1 {{
            font-size: 42px;
            margin: 0 0 10px 0;
            font-weight: 700;
        }}
        header p {{
            font-size: 18px;
            opacity: 0.9;
            margin: 5px 0;
        }}
        .meta {{
            text-align: center;
            color: rgba(255, 255, 255, 0.8);
            font-size: 14px;
            margin-top: 15px;
        }}
        .section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}
        .section h2 {{
            margin: 0 0 20px 0;
            color: #333;
            font-size: 24px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        .section p {{
            color: #666;
            line-height: 1.6;
            margin: 0 0 20px 0;
        }}
        .report-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        .report-card {{
            background: #f8f9fa;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            transition: all 0.3s ease;
            text-decoration: none;
            color: inherit;
            display: block;
        }}
        .report-card:hover {{
            border-color: #667eea;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            transform: translateY(-2px);
        }}
        .report-card h3 {{
            margin: 0 0 10px 0;
            color: #667eea;
            font-size: 18px;
            font-weight: 600;
        }}
        .report-card .filename {{
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #999;
            word-break: break-all;
        }}
        .report-card .description {{
            font-size: 13px;
            color: #666;
            margin-top: 8px;
            line-height: 1.4;
        }}
        .empty-state {{
            text-align: center;
            color: #999;
            font-style: italic;
            padding: 20px;
        }}
        .stats-box {{
            background: rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            color: white;
            margin: 20px auto;
            max-width: 300px;
        }}
        .stats-box .number {{
            font-size: 48px;
            font-weight: bold;
            margin: 0;
        }}
        .stats-box .label {{
            font-size: 16px;
            opacity: 0.9;
            margin-top: 5px;
        }}
        footer {{
            text-align: center;
            color: rgba(255, 255, 255, 0.7);
            margin-top: 50px;
            padding: 20px;
            font-size: 14px;
        }}
        .icon {{
            display: inline-block;
            width: 20px;
            height: 20px;
            margin-right: 8px;
            vertical-align: middle;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>MySQL vs Percona Server</h1>
            <p>Performance Benchmark Reports</p>
            <p style="font-size: 14px; opacity: 0.8;">MySQL 8.4.8 vs Percona Server 8.4.8-8</p>

            <div class="stats-box">
                <div class="number">{total_reports}</div>
                <div class="label">Interactive Reports Available</div>
            </div>

            <div class="meta">
                Generated: {generated_time}
            </div>
        </header>
'''

    # Performance Reports Section
    if reports['performance']:
        html += '''
        <div class="section">
            <h2>📊 Performance Reports</h2>
            <p>Sysbench OLTP Read-Write workload results comparing transaction throughput (TPS), queries per second (QPS), and latency metrics across different thread counts.</p>
            <div class="report-grid">
'''
        for title, filepath, description in reports['performance']:
            html += f'''
                <a href="{filepath.name}" class="report-card">
                    <h3>{title}</h3>
                    <div class="description">{description}</div>
                    <div class="filename">{filepath.name}</div>
                </a>
'''
        html += '''
            </div>
        </div>
'''

    # InnoDB Metrics Section
    if reports['innodb']:
        html += '''
        <div class="section">
            <h2>🔍 InnoDB Metrics Analysis</h2>
            <p>Deep-dive into 319 InnoDB internal metrics sampled every second during benchmark runs. Interactive charts show time-series data with per-second measurements and per-minute averages.</p>
            <div class="report-grid">
'''
        for title, filepath, description in reports['innodb']:
            html += f'''
                <a href="{filepath.name}" class="report-card">
                    <h3>{title}</h3>
                    <div class="description">{description}</div>
                    <div class="filename">{filepath.name}</div>
                </a>
'''
        html += '''
            </div>
        </div>
'''

    # Variable Comparisons Section
    if reports['variables']:
        html += '''
        <div class="section">
            <h2>⚙️ Configuration Comparisons</h2>
            <p>Side-by-side comparison of system variables and status variables between MySQL and Percona Server. Highlights differences in configuration and runtime state.</p>
            <div class="report-grid">
'''
        for title, filepath, description in reports['variables']:
            html += f'''
                <a href="{filepath.name}" class="report-card">
                    <h3>{title}</h3>
                    <div class="description">{description}</div>
                    <div class="filename">{filepath.name}</div>
                </a>
'''
        html += '''
            </div>
        </div>
'''

    # Stack Traces Section
    pmp_index = base_dir / 'index-pmp.html'
    offcpu_index = base_dir / 'index-offcpu.html'

    if pmp_index.exists() or offcpu_index.exists():
        html += '''
        <div class="section">
            <h2>🔬 Stack Trace Analysis</h2>
            <p>Browse pt-pmp stack profiling and off-CPU flame graphs collected during benchmark runs. View thread blocking patterns and contention hotspots.</p>
            <div class="report-grid">
'''

        if pmp_index.exists():
            html += '''
                <a href="index-pmp.html" class="report-card">
                    <h3>pt-pmp Stack Traces Index</h3>
                    <div class="description">Tree view of all stack trace files across all runs</div>
                    <div class="filename">index-pmp.html</div>
                </a>
'''

        if offcpu_index.exists():
            html += '''
                <a href="index-offcpu.html" class="report-card">
                    <h3>Off-CPU Flame Graphs</h3>
                    <div class="description">Interactive flame graphs showing thread blocking and contention</div>
                    <div class="filename">index-offcpu.html</div>
                </a>
'''

        html += '''
            </div>
        </div>
'''

    # No reports found
    if total_reports == 0:
        html += '''
        <div class="section">
            <div class="empty-state">
                <p>No HTML reports found in this directory.</p>
                <p>Run benchmark scripts and generate reports first.</p>
            </div>
        </div>
'''

    html += '''
        <footer>
            <p>Generated by generate_index.py</p>
            <p>Benchmark Suite: 2026-ps-vs-mysql</p>
        </footer>
    </div>
</body>
</html>
'''

    with open(output_file, 'w') as f:
        f.write(html)

    print(f"✓ Generated: {output_file}")
    print(f"  Total reports: {total_reports}")
    print(f"    Performance: {len(reports['performance'])}")
    print(f"    InnoDB: {len(reports['innodb'])}")
    print(f"    Variables: {len(reports['variables'])}")


def main():
    # Scan current directory by default
    base_dir = Path('.')

    # Allow optional directory argument
    if len(sys.argv) > 1:
        base_dir = Path(sys.argv[1])
        if not base_dir.exists():
            print(f"Error: Directory not found: {base_dir}")
            sys.exit(1)

    print("Generating index.html for benchmark reports...")
    print(f"Scanning: {base_dir.absolute()}")
    print("=" * 60)

    reports = find_html_reports(base_dir)
    generate_index_html(reports, base_dir / 'index.html', base_dir)

    print("\n" + "=" * 60)
    print("Done! Open index.html in your browser to view all reports.")


if __name__ == '__main__':
    main()
