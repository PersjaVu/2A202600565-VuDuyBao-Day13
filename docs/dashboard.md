# Observability Dashboard (auto-generated)

> Source: `http://127.0.0.1:8000/metrics` | window: live session | refresh: regenerate to update

## Panel 1 — Latency P50 / P95 / P99 (ms)
```
P50      150 ms |#.............................|
P95      150 ms |#.............................|  SLO line: 3000 ms
P99      150 ms |#.............................|
P95 vs SLO(<3000ms): OK
```

## Panel 2 — Traffic (total requests)
```
requests: 20
```

## Panel 3 — Error rate (%) with breakdown
```
error_rate:  0.00 %   SLO line: 2.0 %  (OK)
  - (no errors recorded)
```

## Panel 4 — Cost (USD)
```
total_cost:  $0.0408
avg_cost:    $0.0020 / request
daily SLO line: $2.5 / day
```

## Panel 5 — Tokens in / out
```
tokens_in       680 |#######.......................|
tokens_out     2587 |##############################|
```

## Panel 6 — Quality proxy (heuristic 0..1)
```
quality_avg: 0.880 |##########################....|  SLO line: 0.75  (OK)
```
