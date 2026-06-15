"""Measure real before/after cost of the optimization levers (Bonus +3).

Runs every sample query twice against the live app — once in baseline mode and
once in optimize mode — then reports the token/cost delta. Writes a Markdown
table to docs/cost-optimization.md so the saving is evidenced, not asserted.

Usage:
    python scripts/cost_benchmark.py
"""

import json
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"
QUERIES = Path("data/sample_queries.jsonl")
OUT_PATH = Path("docs/cost-optimization.md")


def run_mode(client: httpx.Client, payloads: list[dict], optimize: bool) -> dict:
    tin = tout = 0
    cost = 0.0
    n = 0
    for p in payloads:
        body = {**p, "optimize": optimize}
        r = client.post(f"{BASE_URL}/chat", json=body)
        r.raise_for_status()
        j = r.json()
        tin += j["tokens_in"]
        tout += j["tokens_out"]
        cost += j["cost_usd"]
        n += 1
    return {
        "requests": n,
        "tokens_in": tin,
        "tokens_out": tout,
        "total_cost": round(cost, 6),
        "avg_cost": round(cost / n, 6) if n else 0.0,
    }


def pct(before: float, after: float) -> float:
    return round((before - after) / before * 100, 1) if before else 0.0


def main() -> None:
    payloads = [json.loads(l) for l in QUERIES.read_text(encoding="utf-8").splitlines() if l.strip()]

    with httpx.Client(timeout=30.0) as client:
        base = run_mode(client, payloads, optimize=False)
        opt = run_mode(client, payloads, optimize=True)

    rows = [
        ("Requests", base["requests"], opt["requests"], "—"),
        ("Input tokens (total)", base["tokens_in"], opt["tokens_in"], f"-{pct(base['tokens_in'], opt['tokens_in'])}%"),
        ("Output tokens (total)", base["tokens_out"], opt["tokens_out"], f"-{pct(base['tokens_out'], opt['tokens_out'])}%"),
        ("Total cost (USD)", f"${base['total_cost']:.6f}", f"${opt['total_cost']:.6f}", f"-{pct(base['total_cost'], opt['total_cost'])}%"),
        ("Avg cost / req (USD)", f"${base['avg_cost']:.6f}", f"${opt['avg_cost']:.6f}", f"-{pct(base['avg_cost'], opt['avg_cost'])}%"),
    ]

    lines = ["# Cost Optimization — Before / After (measured)", ""]
    lines.append(f"Same {base['requests']} sample queries, run in baseline vs optimize mode against the live app.")
    lines.append("")
    lines.append("Levers: cheap-model routing (Sonnet→Haiku for short Q&A), prompt trimming, output cap (96 tok).")
    lines.append("")
    lines.append("| Metric | Baseline | Optimized | Change |")
    lines.append("|---|---:|---:|---:|")
    for name, b, o, d in rows:
        lines.append(f"| {name} | {b} | {o} | {d} |")
    lines.append("")
    lines.append(f"**Total cost saving: {pct(base['total_cost'], opt['total_cost'])}%** "
                 f"(${base['total_cost']:.6f} → ${opt['total_cost']:.6f}).")
    lines.append("")
    report = "\n".join(lines)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nWritten to {OUT_PATH}")


if __name__ == "__main__":
    main()
