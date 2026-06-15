# Cost Optimization — Before / After (measured)

Same 10 sample queries, run in baseline vs optimize mode against the live app.

Levers: cheap-model routing (Sonnet→Haiku for short Q&A), prompt trimming, output cap (96 tok).

| Metric | Baseline | Optimized | Change |
|---|---:|---:|---:|
| Requests | 10 | 10 | — |
| Input tokens (total) | 340 | 273 | -19.7% |
| Output tokens (total) | 1303 | 930 | -28.6% |
| Total cost (USD) | $0.020565 | $0.006188 | -69.9% |
| Avg cost / req (USD) | $0.002056 | $0.000619 | -69.9% |

**Total cost saving: 69.9%** ($0.020565 → $0.006188).
