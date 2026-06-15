# Day 13 Observability Lab — SOLUTION (tổng hợp toàn bộ)

**Author:** Vu Duy Bao (2A202600565)
**Repo:** https://github.com/PersjaVu/VuDuyBao-2A202600565-Day13
**Date verified:** 2026-06-15
**Environment:** Windows 11, Python 3.13.14, deps from `requirements.txt` in `.venv`

Tài liệu này tổng hợp **đã làm gì**, **làm ở file nào**, **test thật ra sao**, và **kết quả đo được**. Mọi con số bên dưới đều sinh ra từ việc chạy thật app / load test / validator / unit test — không ước lượng.

---

## 0. TL;DR — Kết quả tổng

| Hạng mục | Kết quả | Nguồn |
|---|---|---|
| Unit tests (`pytest`) | **2 passed** | `pytest -q` |
| `validate_logs.py` | **100 / 100** | §4.1 |
| Required/enrichment fields missing | **0 / 0** | validator |
| PII leaks | **0** | validator |
| Live Langfuse traces | **103** (project VinUniDay13, JP region) | §4.2 |
| Dashboard panels | **6 / 6** có unit + SLO line | `docs/dashboard.md` (markdown) + live Chart.js tại `/dashboard` |
| Alert rules | **4** (≥3 yêu cầu) + runbook | `config/alert_rules.yaml` |
| Incidents tái hiện | **3 / 3** (rag_slow, tool_fail, cost_spike) | §4.3 |
| Bonus | cost **−69.9%**, audit logs, automation | §5 |

**Điều kiện đạt (rubric):** validate ≥80 → **100**; ≥10 traces → **103 live**; dashboard 6 panels → ✅; blueprint đủ tên thành viên → ✅. **Tất cả đạt.**

---

## 1. Hoàn thành 8 step của đề (README lab flow)

| # | Step | Trạng thái | File chính |
|---|---|:---:|---|
| 1 | Run starter app | ✅ | `app/main.py` |
| 2 | Correlation IDs | ✅ | `app/middleware.py` |
| 3 | Enrich logs | ✅ | `app/main.py` |
| 4 | PII scrubber | ✅ | `app/pii.py`, `app/logging_config.py` |
| 5 | `validate_logs.py` → 100/100 | ✅ | `scripts/validate_logs.py` |
| 6 | Tracing ≥10 traces (Langfuse) | ✅ (103) | `app/tracing.py`, `app/agent.py` |
| 7 | Dashboard 6 panels | ✅ | `scripts/generate_dashboard.py` |
| 8 | Alert rules + test | ✅ | `config/alert_rules.yaml`, incidents |

---

## 2. Chi tiết phần đã code (lấp các TODO)

### 2.1 Correlation IDs — `app/middleware.py`
- `clear_contextvars()` đầu request (tránh rò rỉ giữa các request).
- Tái dùng `x-request-id` nếu có, không thì sinh `req-<8 hex>` (uuid4).
- `bind_contextvars(correlation_id=...)` → **mọi log** trong request mang id.
- Trả `x-request-id` + `x-response-time-ms` qua response header.
- **Proof:** header `x-request-id: req-375ccada` == body `correlation_id` (trùng khít).

### 2.2 Log enrichment — `app/main.py`
- `bind_contextvars(user_id_hash, session_id, feature, model, env)` trong `chat()`.
- `user_id` được **hash SHA-256 (12 hex)**, không bao giờ log thô.

### 2.3 PII scrubbing — `app/pii.py` + `app/logging_config.py`
- Đăng ký processor `scrub_event` vào pipeline structlog (template để comment).
- Bổ sung patterns: **passport** `[A-Z]\d{7}`, **địa chỉ VN** (`số … đường/phố/ngõ/ngách`), **đơn vị hành chính** (`phường/quận/huyện/tỉnh/thành phố`) — ngoài email, credit_card, cccd, phone_vn.
- **Bug đã sửa:** CCCD 12 số bị `phone_vn` ăn mất 11/12 chữ số → đảo thứ tự cho `cccd` chạy **trước** `phone_vn`.

### 2.4 Tracing — `app/tracing.py` + `app/agent.py`
- **Migrate Langfuse v2 → v3:** template import `langfuse.decorators` (chỉ có ở v2) trong khi `requirements.txt` ghim v3.2.1 → import fail → chạy dummy → 0 trace. Viết lại sang v3 (`from langfuse import observe, get_client`) + shim `langfuse_context` + `flush_traces()`.
- Tự `load_dotenv()` và map `LANGFUSE_BASE_URL → LANGFUSE_HOST` (region JP), strip dấu nháy.

### 2.5 SLO & Alerts — `config/*.yaml` + `docs/alerts.md`
- Điền objective SLO cụ thể (P95<3000ms, error<2%, cost<$2.5/day, quality≥0.75).
- Thêm rule thứ 4 `quality_regression` (P3) + runbook tương ứng.

---

## 3. Danh mục toàn bộ file (đã thêm / đã sửa)

### `app/` — mã nguồn
| File | Trạng thái | Nội dung |
|---|---|---|
| `middleware.py` | sửa | Correlation ID middleware |
| `main.py` | sửa | Log enrichment, audit hooks, endpoint `/_flush`, shutdown flush, `optimize` flag |
| `logging_config.py` | sửa | Đăng ký `scrub_event` |
| `pii.py` | sửa | Thêm patterns PII + sửa bug thứ tự CCCD |
| `tracing.py` | sửa | Migrate Langfuse v3, load_dotenv, normalize host, flush |
| `schemas.py` | sửa | Thêm field `optimize` vào ChatRequest |
| `agent.py` | sửa | Nhánh `optimize`, pricing theo model, trả `model` |
| `mock_llm.py` | sửa | Nhận `model`/`max_output_tokens`, token deterministic |
| `audit.py` | **mới** | Audit log tách riêng (bonus) |
| `optimization.py` | **mới** | Pricing + model router + prompt trim (bonus cost) |
| `dashboard.py` | **mới** | HTML dashboard chuyên nghiệp (Chart.js) phục vụ ở `/dashboard` (bonus) |

### `scripts/` — công cụ
| File | Trạng thái | Nội dung |
|---|---|---|
| `validate_logs.py` | gốc | Chấm điểm log (100/100) |
| `load_test.py` | gốc | Sinh traffic |
| `inject_incident.py` | gốc | Bật/tắt sự cố |
| `generate_dashboard.py` | **mới** | Sinh dashboard 6 panel từ `/metrics` (bonus automation) |
| `cost_benchmark.py` | **mới** | Đo cost trước/sau (bonus) |
| `incident_demo.py` | **mới** | In bảng before/after incident (cho ảnh 07) |

### `config/`
| File | Trạng thái | Nội dung |
|---|---|---|
| `slo.yaml` | sửa | SLO objective cụ thể |
| `alert_rules.yaml` | sửa | 4 alert rules + runbook |
| `logging_schema.json` | gốc | Schema log |

### `docs/`
| File | Trạng thái | Nội dung |
|---|---|---|
| `blueprint-template.md` | điền đầy đủ | Báo cáo nộp (đã điền + nhúng 9 ảnh) |
| `alerts.md` | sửa | Thêm runbook rule thứ 4 |
| `dashboard.md` | **mới (auto)** | Dashboard 6 panel |
| `cost-optimization.md` | **mới (auto)** | Bảng cost −69.9% |
| `evidence/` | **mới** | 9 ảnh screenshot + README checklist |

### Tài liệu gốc dự án
| File | Nội dung |
|---|---|
| `SOLUTION.md` | tài liệu này |
| `data/metrics.json` | snapshot /metrics (auto) |

> `.gitignore` đã loại trừ `.env`, `data/logs.jsonl`, `data/audit.jsonl`, `.venv/` → secret key không bị commit.

---

## 4. Kết quả test thật

### 4.1 `validate_logs.py` → 100/100
```
Total log records analyzed: 33
Records with missing required fields: 0
Records with missing enrichment (context): 0
Unique correlation IDs found: 19
Potential PII leaks detected: 0
+ [PASSED] Basic JSON schema
+ [PASSED] Correlation ID propagation
+ [PASSED] Log enrichment
+ [PASSED] PII scrubbing
Estimated Score: 100/100
```

### 4.2 Tracing — 103 live traces trên Langfuse
```
auth_check(): True   |   LANGFUSE_HOST: https://jp.cloud.langfuse.com
GET /api/public/traces -> totalItems: 103
trace 42e5d39c... name=run user=58335a0a668e session=s_slow latency=2.65s
  observation metadata: {doc_count:1, query_preview, usage_details{input,output}}
```
Mỗi trace có hashed `userId`, `sessionId`, tags `[lab, feature, model]`, token usage. Trace tối ưu mang thêm tag `optimized` + `claude-haiku-4-5`.

### 4.3 Incident Response — 3/3 tái hiện
| Scenario | Triệu chứng đo được | Root cause | Fix |
|---|---|---|---|
| `rag_slow` | latency ~150ms → **2794ms** | `mock_rag.retrieve()` sleep 2.5s | tắt toggle / fallback retrieval |
| `tool_fail` | HTTP 200 → **500** `RuntimeError` | `retrieve()` raise "Vector store timeout" | tắt tool / retry + circuit breaker |
| `cost_spike` | tokens_out ×4, cost tăng vọt | `FakeLLM` nhân output ×4 | prompt ngắn / model rẻ |

**Flow điều tra:** Metrics (error >2%) → Traces (run lỗi, không có span LLM) → Logs (`RuntimeError: Vector store timeout`).

### 4.4 Dashboard — 6 panels (`docs/dashboard.md`)
Latency P50/95/99 · Traffic · Error rate + breakdown · Cost · Tokens in/out · Quality — mỗi panel có đơn vị + đường SLO. Sinh tự động từ `/metrics`.

---

## 5. Bonus (self ~ +7)

- **Cost optimization −69.9% (đo thật):** chế độ `optimize` (`app/optimization.py`) = route Sonnet→Haiku + trim prompt + cap output 96 token.

  | Metric | Baseline | Optimized | Change |
  |---|---:|---:|---:|
  | Input tokens | 340 | 273 | **−19.7%** |
  | Output tokens | 1303 | 930 | **−28.6%** |
  | Total cost | $0.020565 | $0.006188 | **−69.9%** |

  → `docs/cost-optimization.md`, verify qua trace tag `optimized`.
- **Dashboard chuyên nghiệp (live):** `app/dashboard.py` phục vụ tại **`GET /dashboard`** — 6 panel bằng Chart.js (dark theme, đường SLO dạng nét đứt, gauge error/quality, auto-refresh 5s, time-series tích lũy ~1h), cùng origin với `/metrics` nên không vướng CORS.
- **Audit logs tách riêng:** `app/audit.py` → `data/audit.jsonl` (PII-scrubbed, độc lập với log vận hành).
- **Automation:** `scripts/generate_dashboard.py` + `scripts/cost_benchmark.py` tự sinh dashboard markdown & đo cost.

---

## 6. Bằng chứng ảnh (`docs/evidence/`)

| File | Nội dung |
|---|---|
| `01-correlation-id.png` | 1 correlation_id xuyên suốt request_received → response_sent |
| `02-pii-redaction.png` | log có `[REDACTED_EMAIL]` |
| `03-langfuse-trace-list.png` | danh sách traces trên Langfuse |
| `04-trace-waterfall.png` | 1 trace mở ra (timeline, latency 2.65s dưới rag_slow) |
| `05-dashboard-6-panels.png` | dashboard 6 panel |
| `06-alert-rules.png` | 4 alert rules + runbook |
| `07-incident-before-after.png` | latency/error trước–sau inject |
| `08-cost-optimization.png` | bảng cost −69.9% |
| `09-langfuse-optimized-tags.png` | trace tag `optimized` + `claude-haiku-4-5` |
| `10-dashboard-live.png` | dashboard Chart.js 6 panel live tại `/dashboard` |

Tất cả đã được nhúng vào `docs/blueprint-template.md`.

---

## 7. Rubric Self-Assessment (60/40)

| Hạng mục | Max | Self | Căn cứ |
|---|---:|---:|---|
| GROUP — Implementation | 30 | 30 | validate 100/100; correlation IDs; PII redact; 4 alerts; 103 traces |
| GROUP — Incident Debug | 10 | 10 | 3/3 incident, root cause chứng minh |
| GROUP — Live Demo | 20 | (live) | app chạy sạch (0 lỗi runtime); trình bày trực tiếp |
| INDIVIDUAL — Report | 20 | (chấm) | `docs/blueprint-template.md` đầy đủ + giải thích sâu |
| INDIVIDUAL — Git Evidence | 20 | (chấm) | commit + ownership từng file |
| Bonus | 10 | +9~10 | cost −69.9% (+3), live Chart.js dashboard đẹp (+3), automation (+2), audit logs (+2) |

---

## 8. Biến môi trường (checklist)

| Biến | Bắt buộc? | Ghi chú |
|---|---|---|
| `APP_ENV`, `APP_NAME`, `LOG_LEVEL`, `LOG_PATH`, `AUDIT_LOG_PATH` | optional | đều có default |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | **bắt buộc cho trace** | `pk-lf-...` / `sk-lf-...` |
| `LANGFUSE_HOST` | **bắt buộc cho trace** | URL region; **`LANGFUSE_BASE_URL` cũng được chấp nhận** (auto map). Repo dùng JP: `https://jp.cloud.langfuse.com` |

App tự `load_dotenv()` nên chỉ cần điền `.env`. Khởi động với key:
`uvicorn app.main:app --env-file .env`.

---

## 9. Tái lập nhanh

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest -q                          # unit tests

# Terminal 1: server (cần key trong .env de co trace)
PYTHONUTF8=1 .venv/Scripts/python -m uvicorn app.main:app --env-file .env

# Terminal 2:
.venv/Scripts/python scripts/load_test.py --concurrency 5  # sinh traffic + traces
.venv/Scripts/python scripts/validate_logs.py              # -> 100/100
.venv/Scripts/python scripts/generate_dashboard.py         # -> docs/dashboard.md
.venv/Scripts/python scripts/cost_benchmark.py             # -> -69.9%
# live dashboard: mo trinh duyet http://127.0.0.1:8000/dashboard
.venv/Scripts/python scripts/incident_demo.py              # before/after incident
```
