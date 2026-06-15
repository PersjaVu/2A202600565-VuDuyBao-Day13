# Day 13 Observability Lab — SOLUTION

**Author:** Vu Duy Bao (2A202600565)
**Repo:** https://github.com/PersjaVu/VuDuyBao-2A202600565-Day13
**Date verified:** 2026-06-15
**Environment:** Windows 11, Python 3.13.14, all deps from `requirements.txt` installed in `.venv`

This document records **what was implemented**, **how it was tested for real**, and the **measured results**. Every number below was produced by actually running the app, the load generator, the validator, and the unit tests in this repo — not estimated.

---

## 0. TL;DR — Headline Results

| Check | Result | Source |
|---|---|---|
| Unit tests (`pytest`) | **2 passed** | `pytest -q` |
| `validate_logs.py` score | **100 / 100** | section 3 |
| Required log fields missing | **0** | validator |
| Enrichment fields missing | **0** | validator |
| Unique correlation IDs | **19** | validator |
| PII leaks detected | **0** | validator |
| Live Langfuse traces | **20** traces confirmed via Langfuse REST API (JP region) | section 4 |
| Dashboard panels | **6 / 6** with units + SLO lines | `docs/dashboard.md` |
| Alert rules | **4** (≥3 required) with runbooks | `config/alert_rules.yaml` |
| Incidents reproduced | **3 / 3** (rag_slow, tool_fail, cost_spike) | section 5 |
| Bonus items | Audit logs, automation script, cost evidence | section 7 |

**Passing criteria (rubric):** VALIDATE_LOGS_SCORE ≥ 80 → got **100**; ≥10 traces → **20 live traces in Langfuse**; dashboard 6 panels → done; blueprint with member names → `docs/blueprint-template.md`. ✅ All met.

---

## 1. What Was Implemented (the TODO gaps)

### 1.1 Correlation IDs — `app/middleware.py`
Implemented `CorrelationIdMiddleware.dispatch`:
- `clear_contextvars()` at request start to prevent cross-request leakage.
- Reuse inbound `x-request-id` if present, else generate `req-<8-hex>` (`uuid4`).
- `bind_contextvars(correlation_id=...)` so **every** log in the request carries it.
- Echo `x-request-id` and `x-response-time-ms` back as response headers.

**Proof (live):**
```
x-request-id      : req-375ccada
x-response-time-ms: 151.86
body.correlation  : req-375ccada      <-- header == response body, end-to-end
```

### 1.2 Log enrichment — `app/main.py`
In `chat()`, `bind_contextvars(user_id_hash, session_id, feature, model, env)`.
`user_id` is **hashed** (SHA-256, 12 hex) and never logged raw.

**Proof (one real `data/logs.jsonl` line):**
```json
{
  "service": "api",
  "payload": { "message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]" },
  "event": "request_received",
  "session_id": "s01",
  "model": "claude-sonnet-4-5",
  "correlation_id": "req-fa788fbd",
  "user_id_hash": "2055254ee30a",
  "feature": "qa",
  "env": "dev",
  "level": "info",
  "ts": "2026-06-15T05:47:34.194106Z"
}
```

### 1.3 PII scrubbing — `app/pii.py` + `app/logging_config.py`
- Registered the `scrub_event` processor in the structlog pipeline (was commented out).
- Extended `PII_PATTERNS`: added **passport** (`[A-Z]\d{7}`), **Vietnamese street address** (`số … đường/phố/ngõ/ngách …`), and **administrative unit** (`phường/quận/huyện/tỉnh/thành phố …`) on top of email, credit_card, cccd, phone_vn.
- **Bug fixed during testing:** a 12-digit CCCD was being partially consumed by `phone_vn` (left a dangling `1`). Reordered so the exact-12-digit `cccd` rule runs **before** `phone_vn`.

**Proof (real scrubber output):**
```
'Email me at student@vinuni.edu.vn'                 -> 'Email me at [REDACTED_EMAIL]'
'My phone 0987654321 and card 4111 1111 1111 1111'  -> 'My phone [REDACTED_PHONE_VN] and card [REDACTED_CREDIT_CARD]'
'CCCD 012345678901 passport B1234567'               -> 'CCCD [REDACTED_CCCD] passport [REDACTED_PASSPORT]'
'... số 12 đường Láng, phường Láng Thượng, quận Đống Đa'
                                                    -> '... [REDACTED_ADDRESS_VN], [REDACTED_ADMIN_UNIT_VN], [REDACTED_ADMIN_UNIT_VN]'
'Explain why metrics traces and logs work together' -> (unchanged — no over-redaction)
```

### 1.4 SLO & Alerts — `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md`
- Filled concrete SLO objectives + notes (P95<3000ms, error<2%, cost<$2.5/day, quality≥0.75).
- Added a 4th alert rule `quality_regression` (P3) with a matching runbook section `docs/alerts.md#4-quality-regression`.

---

## 2. How To Reproduce (exact commands)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt

# unit tests
.venv/Scripts/python -m pytest -q

# start app (set UTF-8 for Vietnamese PII test data on Windows)
PYTHONUTF8=1 .venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# generate traffic + incidents + dashboard
.venv/Scripts/python scripts/load_test.py --concurrency 5
.venv/Scripts/python scripts/inject_incident.py --scenario rag_slow
.venv/Scripts/python scripts/validate_logs.py
.venv/Scripts/python scripts/generate_dashboard.py
```

---

## 3. Test: `validate_logs.py` — 100/100 (real output)

```
--- Lab Verification Results ---
Total log records analyzed: 33
Records with missing required fields: 0
Records with missing enrichment (context): 0
Unique correlation IDs found: 19
Potential PII leaks detected: 0

--- Grading Scorecard (Estimates) ---
+ [PASSED] Basic JSON schema
+ [PASSED] Correlation ID propagation
+ [PASSED] Log enrichment
+ [PASSED] PII scrubbing

Estimated Score: 100/100
```

---

## 4. Test: Tracing (Langfuse) — 20 LIVE traces confirmed

Langfuse keys were added to `.env`. Two code/config fixes were required before traces would actually flow (see also §10):

1. **SDK v3 migration.** The template imported `from langfuse.decorators import observe, langfuse_context` — that module only exists in Langfuse **v2**, but `requirements.txt` pins **v3 (3.2.1)**, so the import failed and the app silently ran the no-op dummy decorator. Rewrote `app/tracing.py` to the v3 API (`from langfuse import observe, get_client`) with a thin `langfuse_context` shim, plus `flush_traces()`.
2. **Env loading + host var.** The app never called `load_dotenv()`, and `.env` used `LANGFUSE_BASE_URL` (JP region) while the SDK reads `LANGFUSE_HOST`. `app/tracing.py` now loads `.env` and normalizes `LANGFUSE_BASE_URL → LANGFUSE_HOST` (and strips quotes).

**Auth check (real):**
```
tracing_enabled(): True
LANGFUSE_HOST resolved: https://jp.cloud.langfuse.com
observe is real (not dummy): langfuse._client.observe
auth_check(): True
```

**Traces pulled back from the Langfuse REST API after a 20-request load test:**
```
GET https://jp.cloud.langfuse.com/api/public/traces  ->  HTTP 200
TOTAL traces returned: 20   meta: {page:1, totalItems:20, totalPages:1}
  id=a1c7c248..  name=run  user=105a9cef3903  tags=['claude-sonnet-4-5','lab','qa']  session=s10
  id=237204..    name=run  user=4d14d5d4f719  tags=['claude-sonnet-4-5','lab','qa']  session=s09
  ...
```

**One full trace (observation metadata is rich, as required):**
```
trace a1c7c248220ecdba299d65870bc6e7f4  name=run  user=105a9cef3903  session=s10
  observation "run" metadata:
    {"doc_count": 1, "query_preview": "How should alerts be designed?",
     "usage_details": {"input": 29, "output": 162}}
```

**Result: 20 live traces in Langfuse with hashed user_id, session_id, tags, and token usage — exceeds the 10-trace requirement.** Reproduce: `uvicorn app.main:app --env-file .env`, run `scripts/load_test.py`, then `POST /_flush`.

---

## 5. Test: Incident Response (all 3 scenarios reproduced)

| Scenario | Symptom observed (measured) | Root cause (proved by) | Fix |
|---|---|---|---|
| `rag_slow` | latency **2810 ms** vs ~150 ms baseline; `x-response-time-ms: 2652` | RAG span sleeps 2.5s in `app/mock_rag.py retrieve()` | disable toggle / fallback retrieval |
| `tool_fail` | HTTP **500** `{"detail":"RuntimeError"}`; `error_breakdown: {"RuntimeError": 1}` | `retrieve()` raises `RuntimeError("Vector store timeout")`; log `request_failed` with `error_type` | disable tool / retry+circuit breaker |
| `cost_spike` | `tokens_out` **664** (≈5×) and `cost_usd 0.0100` vs baseline avg **0.0020** | `FakeLLM.generate` multiplies output tokens ×4 in `app/mock_llm.py` | shorter prompts / cheaper model route |

**Debugging flow demonstrated (Metrics → Traces → Logs):**
1. **Metrics** `/metrics` → error rate panel breaches 2% (Panel 3 shows `RuntimeError: 1`).
2. **Traces** → the failing run's root span has no LLM child (failure happened in the RAG step).
3. **Logs** → `event:request_failed, error_type:"RuntimeError", payload.detail:"Vector store timeout"` pinpoints the exact cause.

---

## 6. Test: Dashboard — 6 panels (`docs/dashboard.md`)

Auto-generated by `scripts/generate_dashboard.py` from the live `/metrics` snapshot (`data/metrics.json`). Each panel has **units** and a **visible SLO threshold line**:

| # | Panel | Value (this session) | SLO line |
|---|---|---|---|
| 1 | Latency P50/P95/P99 (ms) | 150 / 2651 / 2651 | < 3000 ms → OK |
| 2 | Traffic (requests) | 13 | — |
| 3 | Error rate (%) + breakdown | 7.69% (`RuntimeError:1`) | < 2% → BREACH (by design, injected) |
| 4 | Cost (USD) | total $0.0342, avg $0.0026/req | < $2.5/day → OK |
| 5 | Tokens in/out | 440 / 2190 | — |
| 6 | Quality proxy (0..1) | 0.869 | ≥ 0.75 → OK |

---

## 7. Bonus Items

- **Audit logs (separate file):** `app/audit.py` writes an append-only, PII-scrubbed trail to `data/audit.jsonl` (verified **19 records**: `chat_completed`, `incident_enabled/disabled`), independent of operational `data/logs.jsonl`.
- **Automation / custom script:** `scripts/generate_dashboard.py` renders the 6-panel SLO dashboard straight from `/metrics` — reproducible, version-controlled, no manual Grafana needed.
- **Cost optimization evidence:** baseline avg **$0.0020/req** vs `cost_spike` **$0.0100/req** (~5×), with mitigation documented in `docs/alerts.md#3-cost-budget-spike`.

---

## 8. Files Changed / Added

**Implemented gaps:** `app/middleware.py`, `app/main.py`, `app/logging_config.py`, `app/pii.py`, `app/tracing.py` (v3 migration), `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md`.
**Added:** `app/audit.py`, `scripts/generate_dashboard.py`, `docs/dashboard.md`, `data/metrics.json`, this `SOLUTION.md`.
**Filled report:** `docs/blueprint-template.md`.

---

## 9. Rubric Self-Assessment (60/40)

| Category | Max | Self | Basis |
|---|---:|---:|---|
| **GROUP — Implementation** | 30 | 30 | validate_logs 100/100; correlation IDs; PII fully redacted; 4 alert rules; **20 live Langfuse traces** |
| **GROUP — Incident Debug** | 10 | 10 | all 3 incidents reproduced with measured symptoms + proven root cause |
| **GROUP — Live Demo** | 20 | n/a | requires live presentation (app runs clean: 0 unexpected runtime errors) |
| **INDIVIDUAL — Report** | 20 | — | `docs/blueprint-template.md` filled with explanations (PII regex ordering, P95, trace waterfall) |
| **INDIVIDUAL — Git Evidence** | 20 | — | per-file ownership listed in blueprint §5; ready to commit |
| **Bonus** | 10 | +6 | audit logs (+2), automation script (+2), cost optimization evidence (+3, capped) |

> Group technical (auto-verifiable) portion is fully green; Demo and Git-evidence/Individual-report points depend on the live presentation and commit history at grading time.

---

## 10. Environment Variables — full checklist

The app reads these (all but the Langfuse trio have safe defaults):

| Variable | Required? | Notes |
|---|---|---|
| `APP_ENV` | optional | default `dev` |
| `APP_NAME` | optional | default `day13-observability-lab` |
| `LOG_LEVEL` | optional | default `INFO` |
| `LOG_PATH` | optional | default `data/logs.jsonl` |
| `AUDIT_LOG_PATH` | optional | default `data/audit.jsonl` (bonus audit trail) |
| `LANGFUSE_PUBLIC_KEY` | **required for traces** | `pk-lf-...` |
| `LANGFUSE_SECRET_KEY` | **required for traces** | `sk-lf-...` |
| `LANGFUSE_HOST` | **required for traces** | region URL. **`LANGFUSE_BASE_URL` is also accepted** and normalized to `LANGFUSE_HOST` (this repo's `.env` uses the JP region `https://jp.cloud.langfuse.com`). |

Notes that previously blocked tracing and are now handled:
- `app/tracing.py` calls `load_dotenv()`, so `.env` is picked up even without `uvicorn --env-file`.
- `LANGFUSE_BASE_URL` is auto-mapped to `LANGFUSE_HOST` and surrounding quotes are stripped.
- The SDK was migrated from v2 to v3, so the keys now actually produce traces.
