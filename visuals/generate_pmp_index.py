#!/usr/bin/env python3
"""
Generate index-pmp.html with a tree structure of all pt-pmp.txt files
Scans benchmark_logs/ and benchmark_logs_binlog/ directories
"""

import sys
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


def find_pmp_files(base_dir: Path) -> Dict[str, List[Path]]:
    """
    Find all pt-pmp.txt files organized by directory structure
    Returns dict: {benchmark_dir: [pmp_files]}
    """
    structure = defaultdict(lambda: defaultdict(list))

    if not base_dir.exists():
        return {}

    # Scan for .pt-pmp.txt files
    for pmp_file in base_dir.rglob('*.pt-pmp.txt'):
        # Get relative path components
        rel_path = pmp_file.relative_to(base_dir)
        parts = rel_path.parts

        if len(parts) >= 3:  # benchmark_logs/server/version/file
            server = parts[0]  # e.g., "mysql"
            version = parts[1]  # e.g., "8.4.8"
            filename = parts[-1]

            structure[server][version].append({
                'filename': filename,
                'path': pmp_file.relative_to(base_dir.parent)
            })

    # Sort files within each version
    for server in structure:
        for version in structure[server]:
            structure[server][version].sort(key=lambda x: x['filename'])

    return structure


def generate_html(benchmark_dirs: List[Path], output_file: Path):
    """Generate HTML index with tree structure of all pt-pmp.txt files"""

    # Collect all files from all benchmark directories
    all_structures = {}
    for bench_dir in benchmark_dirs:
        if bench_dir.exists():
            all_structures[bench_dir.name] = find_pmp_files(bench_dir)

    # Count total files
    total_files = sum(
        len(files)
        for bench_name, servers in all_structures.items()
        for server, versions in servers.items()
        for version, files in versions.items()
    )

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>pt-pmp Stack Traces Index</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }}
        header h1 {{
            font-size: 36px;
            margin: 0 0 10px 0;
            font-weight: 700;
        }}
        header p {{
            font-size: 16px;
            opacity: 0.9;
            margin: 5px 0;
        }}
        .stats-box {{
            background: rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            color: white;
            margin: 15px auto;
            max-width: 250px;
        }}
        .stats-box .number {{
            font-size: 42px;
            font-weight: bold;
            margin: 0;
        }}
        .stats-box .label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .content {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .tree {{
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.8;
        }}
        .tree-root {{
            margin: 20px 0;
        }}
        .tree-benchmark {{
            margin: 15px 0;
        }}
        .tree-benchmark > .label {{
            font-weight: 700;
            font-size: 18px;
            color: #667eea;
            margin-bottom: 10px;
            cursor: pointer;
            user-select: none;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .tree-benchmark > .label:hover {{
            color: #5566d8;
        }}
        .tree-benchmark > .label .icon {{
            font-size: 14px;
            transition: transform 0.2s;
        }}
        .tree-benchmark.collapsed > .label .icon {{
            transform: rotate(-90deg);
        }}
        .tree-server {{
            margin-left: 20px;
            margin-top: 8px;
        }}
        .tree-server > .label {{
            font-weight: 600;
            font-size: 15px;
            color: #333;
            cursor: pointer;
            user-select: none;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .tree-server > .label:hover {{
            color: #667eea;
        }}
        .tree-server > .label .icon {{
            font-size: 12px;
            transition: transform 0.2s;
        }}
        .tree-server.collapsed > .label .icon {{
            transform: rotate(-90deg);
        }}
        .tree-version {{
            margin-left: 20px;
            margin-top: 5px;
        }}
        .tree-version > .label {{
            font-weight: 600;
            font-size: 14px;
            color: #555;
            cursor: pointer;
            user-select: none;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .tree-version > .label:hover {{
            color: #667eea;
        }}
        .tree-version > .label .icon {{
            font-size: 11px;
            transition: transform 0.2s;
        }}
        .tree-version.collapsed > .label .icon {{
            transform: rotate(-90deg);
        }}
        .tree-files {{
            margin-left: 20px;
            margin-top: 5px;
        }}
        .tree-file {{
            padding: 4px 8px;
            margin: 2px 0;
            border-radius: 4px;
            transition: background 0.15s;
        }}
        .tree-file:hover {{
            background: #f0f0f0;
        }}
        .tree-file a {{
            color: #1a73e8;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .tree-file a:hover {{
            text-decoration: underline;
        }}
        .tree-file .file-icon {{
            color: #999;
        }}
        .collapsed > .tree-server,
        .collapsed > .tree-version,
        .collapsed > .tree-files {{
            display: none;
        }}
        .controls {{
            margin: 20px 0;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .controls button {{
            padding: 8px 16px;
            border: 1px solid #ccc;
            border-radius: 6px;
            background: #f7f7f7;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
        }}
        .controls button:hover {{
            background: #eee;
        }}
        footer {{
            text-align: center;
            color: rgba(255, 255, 255, 0.7);
            margin-top: 30px;
            padding: 20px;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>pt-pmp Stack Traces Index</h1>
            <p>Browse stack trace profiling files from all benchmark runs</p>
            <div class="stats-box">
                <div class="number">{total_files}</div>
                <div class="label">Stack Trace Files</div>
            </div>
        </header>

        <div class="content">
            <div class="controls">
                <button onclick="expandAll()">Expand All</button>
                <button onclick="collapseAll()">Collapse All</button>
            </div>

            <div class="tree">
'''

    # Build tree structure
    for bench_name, servers in sorted(all_structures.items()):
        bench_label = "Binlog Enabled" if "binlog" in bench_name else "Binlog Disabled"
        html += f'''
                <div class="tree-benchmark" id="bench-{bench_name}">
                    <div class="label" onclick="toggleNode('bench-{bench_name}')">
                        <span class="icon">▼</span>
                        <span>📁 {bench_name}/ ({bench_label})</span>
                    </div>
'''

        for server, versions in sorted(servers.items()):
            server_id = f"{bench_name}-{server}"
            html += f'''
                    <div class="tree-server" id="{server_id}">
                        <div class="label" onclick="toggleNode('{server_id}')">
                            <span class="icon">▼</span>
                            <span>📁 {server}/</span>
                        </div>
'''

            for version, files in sorted(versions.items()):
                version_id = f"{server_id}-{version}"
                file_count = len(files)
                html += f'''
                        <div class="tree-version" id="{version_id}">
                            <div class="label" onclick="toggleNode('{version_id}')">
                                <span class="icon">▼</span>
                                <span>📁 {version}/ ({file_count} files)</span>
                            </div>
                            <div class="tree-files">
'''

                for file_info in files:
                    filename = file_info['filename']
                    file_path = file_info['path']
                    html += f'''
                                <div class="tree-file">
                                    <a href="{file_path}" target="_blank" rel="noopener">
                                        <span class="file-icon">📄</span>
                                        <span>{filename}</span>
                                    </a>
                                </div>
'''

                html += '''
                            </div>
                        </div>
'''

            html += '''
                    </div>
'''

        html += '''
                </div>
'''

    html += '''
            </div>
        </div>

        <footer>
            <p>Generated by generate_pmp_index.py</p>
            <p>pt-pmp profiles collected at benchmark midpoint (7.5 minutes into 15-minute runs)</p>
        </footer>
    </div>

    <script>
        function toggleNode(nodeId) {
            const node = document.getElementById(nodeId);
            if (node) {
                node.classList.toggle('collapsed');
            }
        }

        function expandAll() {
            document.querySelectorAll('.tree-benchmark, .tree-server, .tree-version').forEach(node => {
                node.classList.remove('collapsed');
            });
        }

        function collapseAll() {
            document.querySelectorAll('.tree-benchmark, .tree-server, .tree-version').forEach(node => {
                node.classList.add('collapsed');
            });
        }
    </script>
</body>
</html>
'''

    with open(output_file, 'w') as f:
        f.write(html)

    print(f"✓ Generated: {output_file}")
    print(f"  Total pt-pmp files: {total_files}")
    for bench_name, servers in sorted(all_structures.items()):
        bench_count = sum(len(files) for server in servers.values() for files in server.values())
        print(f"    {bench_name}: {bench_count} files")


def main():
    # Find project root (where benchmark_logs directories are)
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent

    # Default benchmark directories
    benchmark_dirs = [
        project_dir / "benchmark_logs",
        project_dir / "benchmark_logs_binlog"
    ]

    output_file = project_dir / "index-pmp.html"

    print("Generating pt-pmp index...")
    print(f"Project directory: {project_dir}")
    print("=" * 60)

    # Filter to existing directories
    existing_dirs = [d for d in benchmark_dirs if d.exists()]

    if not existing_dirs:
        print("Error: No benchmark directories found")
        print("Expected:")
        for d in benchmark_dirs:
            print(f"  - {d}")
        sys.exit(1)

    generate_html(existing_dirs, output_file)

    print("\n" + "=" * 60)
    print(f"Done! Open {output_file.name} in your browser to view the index.")


if __name__ == '__main__':
    main()
