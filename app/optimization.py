from __future__ import annotations

"""Cost-optimization levers (Bonus: tối ưu chi phí, có số liệu trước/sau).

Three independent, measurable levers are applied when a request runs in
``optimize`` mode:

1. **Model routing** — simple/short Q&A is routed to a cheaper model
   (Haiku) instead of always using Sonnet.
2. **Prompt trimming** — only the single most relevant retrieved doc is kept
   and over-long text is truncated, cutting input tokens.
3. **Output capping** — answers are capped to a concise length, cutting
   output tokens (and also blunting the ``cost_spike`` incident).

Each lever lowers a real, attributable number; ``scripts/cost_benchmark.py``
runs the same queries with and without optimize and reports the delta.
"""

# Illustrative lab pricing in USD per 1,000,000 tokens (input, output).
# Cheaper tier (haiku) is what the router falls back to for easy traffic.
PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (0.80, 4.0),
}

CHEAP_MODEL = "claude-haiku-4-5"

# Concise answers in optimized mode: cap output tokens.
OPTIMIZED_MAX_OUTPUT = 96

# A short Q&A query does not need the premium model.
SHORT_QUERY_CHARS = 120
# Trim long context/questions before they reach the prompt.
MAX_DOC_CHARS = 200
MAX_MESSAGE_CHARS = 200


def price_per_million(model: str) -> tuple[float, float]:
    return PRICING.get(model, PRICING["claude-sonnet-4-5"])


def route_model(feature: str, message: str, default: str) -> str:
    """Send short single-turn Q&A to the cheap model; keep summaries premium."""
    if feature == "qa" and len(message) <= SHORT_QUERY_CHARS:
        return CHEAP_MODEL
    return default


def optimize_prompt(feature: str, docs: list[str], message: str) -> str:
    """Keep only the top doc, truncate long text, drop verbose scaffolding."""
    top_doc = docs[0][:MAX_DOC_CHARS] if docs else ""
    short_message = message[:MAX_MESSAGE_CHARS]
    # Compact single-line prompt (no multi-line "Feature=/Docs=/Question=" labels).
    return f"{feature}|{top_doc}|{short_message}"
