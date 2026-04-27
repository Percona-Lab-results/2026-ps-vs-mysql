#!/usr/bin/env python3
"""
Scans benchmark_logs/<server>/<version>/ for run<R>_Tier<M>G_RW_<T>th.sysbench.txt
files (R=1,2,3), parses TPS/QPS, and generates interactive Plotly HTML.

Usage:
    python3 throughput_report.py [base_dir] [output_file] [test_type] [mode]

Defaults:
    base_dir    = "benchmark_logs"
    output_file = "<base_dir>/sysbench_interactive_comparison.html"
    test_type   = "OLTP Read-Write"
    mode        = "average"

Mode:
    individual - Show each run separately (e.g., "run1-mysql-8.4.8", "run2-mysql-8.4.8")
    average    - Average runs together (e.g., "mysql-8.4.8") [default]
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

FILENAME_RE = re.compile(
    r"^run(?P<run>[123])_Tier(?P<mem>\d+)G_RW_(?P<threads>\d+)th\.sysbench\.txt$"
)
TPS_RE = re.compile(r"transactions:\s*\d+\s*\(([0-9.]+)\s*per sec\.\)")
QPS_RE = re.compile(r"queries:\s*\d+\s*\(([0-9.]+)\s*per sec\.\)")

TEMPLATE_PATH = Path(__file__).resolve().parent / "visual_template.html.in"


def extract_rates(path: Path):
    text = path.read_text(errors="replace")
    tps_match = TPS_RE.search(text)
    qps_match = QPS_RE.search(text)
    if not tps_match or not qps_match:
        return None
    return float(tps_match.group(1)), float(qps_match.group(1))


def scan_individual(base_dir: Path):
    """Return list of dicts with one entry per run (no averaging)."""
    rows = []

    for server_dir in sorted(p for p in base_dir.iterdir() if p.is_dir()):
        for version_dir in sorted(p for p in server_dir.iterdir() if p.is_dir()):
            for f in sorted(version_dir.glob("run*_Tier*G_RW_*th.sysbench.txt")):
                m = FILENAME_RE.match(f.name)
                if not m:
                    continue
                rates = extract_rates(f)
                if rates is None:
                    print(f"  NA result (skipped): {f}", file=sys.stderr)
                    continue
                tps, qps = rates
                run_num = m.group("run")
                server_name = f"run{run_num}-{server_dir.name}-{version_dir.name}"

                rows.append({
                    "server": server_name,
                    "mem_gb": int(m.group("mem")),
                    "threads": int(m.group("threads")),
                    "tps": round(tps, 2),
                    "qps": round(qps, 2),
                })

    rows.sort(key=lambda r: (r["server"], r["mem_gb"], r["threads"]))
    return rows


def scan_average(base_dir: Path):
    """Return list of dicts with averaged tps/qps per (server, mem, threads)."""
    buckets = defaultdict(lambda: {"tps": [], "qps": []})

    for server_dir in sorted(p for p in base_dir.iterdir() if p.is_dir()):
        for version_dir in sorted(p for p in server_dir.iterdir() if p.is_dir()):
            for f in sorted(version_dir.glob("run*_Tier*G_RW_*th.sysbench.txt")):
                m = FILENAME_RE.match(f.name)
                if not m:
                    continue
                rates = extract_rates(f)
                if rates is None:
                    print(f"  NA result (skipped): {f}", file=sys.stderr)
                    continue
                tps, qps = rates
                key = (
                    f"{server_dir.name} {version_dir.name}",
                    int(m.group("mem")),
                    int(m.group("threads")),
                )
                buckets[key]["tps"].append(tps)
                buckets[key]["qps"].append(qps)

    rows = []
    for (server, mem, threads), vals in buckets.items():
        rows.append(
            {
                "server": server,
                "mem_gb": mem,
                "threads": threads,
                "tps": round(sum(vals["tps"]) / len(vals["tps"]), 2),
                "qps": round(sum(vals["qps"]) / len(vals["qps"]), 2),
                "runs": len(vals["tps"]),
            }
        )
    rows.sort(key=lambda r: (r["server"], r["mem_gb"], r["threads"]))
    return rows


def build_data_block(rows, mode):
    if mode == "average":
        data_rows = [
            {k: v for k, v in r.items() if k != "runs"} for r in rows
        ]
    else:
        data_rows = rows

    servers_sorted = sorted({r["server"] for r in rows})
    mems_sorted = sorted({r["mem_gb"] for r in rows})
    threads_sorted = sorted({r["threads"] for r in rows})

    return (
        f"const DATA = {json.dumps(data_rows)};\n"
        f"const SERVERS = {json.dumps(servers_sorted)};\n"
        f"const MEMS = {json.dumps(mems_sorted)};\n"
        f"const THREADS = {json.dumps(threads_sorted)};"
    ), servers_sorted, mems_sorted, threads_sorted


def main():
    base_dir = Path(sys.argv[1]) if len(sys.argv) >= 2 else Path("benchmark_logs")
    default_output = base_dir.resolve().parent / "sysbench_interactive_comparison.html"
    output_file = Path(sys.argv[2]) if len(sys.argv) >= 3 else default_output
    test_type = sys.argv[3] if len(sys.argv) >= 4 else "OLTP Read-Write"
    mode = sys.argv[4].lower() if len(sys.argv) >= 5 else "average"

    if mode not in ["individual", "average"]:
        sys.exit(f"Invalid mode '{mode}'. Must be 'individual' or 'average'")

    if not base_dir.is_dir():
        sys.exit(f"base_dir not found: {base_dir}")
    if not TEMPLATE_PATH.is_file():
        sys.exit(f"Template not found: {TEMPLATE_PATH}")

    print(f"Scanning: {base_dir}")
    print(f"Mode: {mode}")

    if mode == "individual":
        rows = scan_individual(base_dir)
    else:
        rows = scan_average(base_dir)

    if not rows:
        sys.exit(f"No valid sysbench data found under '{base_dir}'")

    if mode == "average":
        incomplete = [r for r in rows if r["runs"] < 3]
        for r in incomplete:
            print(
                f"  warning: only {r['runs']} run(s) for "
                f"{r['server']} mem={r['mem_gb']}G threads={r['threads']}",
                file=sys.stderr,
            )

    data_block, servers, mems, threads = build_data_block(rows, mode)

    threads_js_vals = "[" + ",".join(str(t) for t in threads) + "]"
    threads_js_text = "[" + ",".join(f'"{t}"' for t in threads) + "]"

    tmpl = TEMPLATE_PATH.read_text()
    if "{{DATA_BLOCK}}" not in tmpl:
        sys.exit(f"Template '{TEMPLATE_PATH}' is missing the {{DATA_BLOCK}} placeholder.")

    out = tmpl.replace("{{DATA_BLOCK}}", data_block)
    out = out.replace("{{BASE_URL}}", str(base_dir))
    out = out.replace("{{TEST_TYPE}}", test_type)

    out = re.sub(
        r'tickvals: \(xMode === "threads"\) \? \[.*?\] : undefined,',
        f'tickvals: (xMode === "threads") ? {threads_js_vals} : undefined,',
        out,
    )
    out = re.sub(
        r'ticktext: \(xMode === "threads"\) \? \[.*?\] : undefined,',
        f'ticktext: (xMode === "threads") ? {threads_js_text} : undefined,',
        out,
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(out)

    print(f"Done. Report written to: {output_file}")
    print(f"  Servers : {len(servers)}")
    print(f"  Memories: {', '.join(str(m) for m in mems)}")
    print(f"  Threads : {', '.join(str(t) for t in threads)}")
    if mode == "average":
        print(f"  Records : {len(rows)} (averaged over up to 3 runs each)")
    else:
        print(f"  Records : {len(rows)} (individual runs)")


if __name__ == "__main__":
    main()
