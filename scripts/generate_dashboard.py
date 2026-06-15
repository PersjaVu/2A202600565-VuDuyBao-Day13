"""Generate a 6-panel observability dashboard from the live /metrics snapshot.

Bonus: automation / custom script. Without a hosted Grafana the team still needs
the required 6 Layer-2 panels (latency, traffic, error rate, cost, tokens,
quality) with units and SLO threshold lines. This script pulls the in-memory
metrics from the running app and renders a self-contained Markdown dashboard
with ASCII bars, so the evidence is reproducible and version-controlled.

Usage:
    python scripts/generate_dashboard.py                 # fetch from running app
    python scripts/generate_dashboard.py --from-file data/metrics.json
"""

import argparse
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
OUT_PATH = Path("docs/dashboard.md")

# SLO thresholds (mirror config/slo.yaml) used to draw the threshold lines.
SLO = {
    "latency_p95_ms": 3000,
    "error_rate_pct": 2.0,
    "daily_cost_usd": 2.5,
    "quality_score_avg": 0.75,
}


def _bar(value: float, maximum: float, width: int = 30) -> str:
    if maximum <= 0:
        return " " * width
    filled = int(min(1.0, value / maximum) * width)
    return "#" * filled + "." * (width - filled)


def fetch_metrics(from_file: str | None) -> dict:
    if from_file:
        return json.loads(Path(from_file).read_text(encoding="utf-8"))
    import httpx

    return httpx.get(f"{BASE_URL}/metrics", timeout=10.0).json()


def render(m: dict) -> str:
    traffic = m.get("traffic", 0)
    errors = m.get("error_breakdown", {})
    total_errors = sum(errors.values())
    error_rate = (total_errors / traffic * 100) if traffic else 0.0
    tokens_in = m.get("tokens_in_total", 0)
    tokens_out = m.get("tokens_out_total", 0)

    lines = []
    lines.append("# Observability Dashboard (auto-generated)")
    lines.append("")
    lines.append(f"> Source: `{BASE_URL}/metrics` | window: live session | refresh: regenerate to update")
    lines.append("")

    # Panel 1: Latency P50/P95/P99 (ms)
    lines.append("## Panel 1 — Latency P50 / P95 / P99 (ms)")
    p50, p95, p99 = m["latency_p50"], m["latency_p95"], m["latency_p99"]
    scale = max(p99, SLO["latency_p95_ms"], 1)
    lines.append("```")
    lines.append(f"P50 {p50:8.0f} ms |{_bar(p50, scale)}|")
    lines.append(f"P95 {p95:8.0f} ms |{_bar(p95, scale)}|  SLO line: {SLO['latency_p95_ms']} ms")
    lines.append(f"P99 {p99:8.0f} ms |{_bar(p99, scale)}|")
    breach = "BREACH" if p95 > SLO["latency_p95_ms"] else "OK"
    lines.append(f"P95 vs SLO(<{SLO['latency_p95_ms']}ms): {breach}")
    lines.append("```")
    lines.append("")

    # Panel 2: Traffic
    lines.append("## Panel 2 — Traffic (total requests)")
    lines.append("```")
    lines.append(f"requests: {traffic}")
    lines.append("```")
    lines.append("")

    # Panel 3: Error rate with breakdown
    lines.append("## Panel 3 — Error rate (%) with breakdown")
    lines.append("```")
    lines.append(f"error_rate: {error_rate:5.2f} %   SLO line: {SLO['error_rate_pct']} %  "
                 f"({'BREACH' if error_rate > SLO['error_rate_pct'] else 'OK'})")
    if errors:
        for etype, count in errors.items():
            lines.append(f"  - {etype}: {count}")
    else:
        lines.append("  - (no errors recorded)")
    lines.append("```")
    lines.append("")

    # Panel 4: Cost over time
    lines.append("## Panel 4 — Cost (USD)")
    lines.append("```")
    lines.append(f"total_cost:  ${m['total_cost_usd']:.4f}")
    lines.append(f"avg_cost:    ${m['avg_cost_usd']:.4f} / request")
    lines.append(f"daily SLO line: ${SLO['daily_cost_usd']} / day")
    lines.append("```")
    lines.append("")

    # Panel 5: Tokens in/out
    lines.append("## Panel 5 — Tokens in / out")
    tmax = max(tokens_in, tokens_out, 1)
    lines.append("```")
    lines.append(f"tokens_in  {tokens_in:8d} |{_bar(tokens_in, tmax)}|")
    lines.append(f"tokens_out {tokens_out:8d} |{_bar(tokens_out, tmax)}|")
    lines.append("```")
    lines.append("")

    # Panel 6: Quality proxy
    lines.append("## Panel 6 — Quality proxy (heuristic 0..1)")
    q = m.get("quality_avg", 0.0)
    lines.append("```")
    lines.append(f"quality_avg: {q:.3f} |{_bar(q, 1.0)}|  SLO line: {SLO['quality_score_avg']}  "
                 f"({'BREACH' if q < SLO['quality_score_avg'] else 'OK'})")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-file", default=None, help="Read metrics JSON from file instead of HTTP")
    args = parser.parse_args()

    metrics = fetch_metrics(args.from_file)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render(metrics), encoding="utf-8")
    print(f"Dashboard written to {OUT_PATH} (6 panels)")


if __name__ == "__main__":
    main()
