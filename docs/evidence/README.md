# Evidence Screenshots — checklist chụp ảnh

Thư mục này chứa **ảnh chụp màn hình** dùng làm bằng chứng nộp bài. Ảnh KHÔNG tự sinh
ra được — bạn phải tự chụp theo checklist dưới đây, lưu **đúng tên file** để khớp với
đường dẫn đã ghi trong `docs/blueprint-template.md`.

> Chụp màn hình trên Windows: phím **Win + Shift + S** (Snipping Tool) → dán vào Paint
> → Save As PNG vào thư mục này.

## Bắt buộc (Rubric A1 + grading-evidence.md)

| Tên file | Chụp cái gì | Lấy ở đâu |
|---|---|---|
| `01-correlation-id.png` | 1 dòng log JSON có `correlation_id` | chạy lệnh ở DEMO mục 3, chụp terminal; hoặc mở `data/logs.jsonl` |
| `02-pii-redaction.png` | dòng log có `[REDACTED_EMAIL]` | DEMO mục 3 (lệnh xem log redacted) |
| `03-langfuse-trace-list.png` | danh sách ≥10 traces | Langfuse → trang **Tracing** (KHÔNG phải Home) |
| `04-trace-waterfall.png` | 1 trace mở ra, thấy span `run` + metadata | Langfuse → bấm vào 1 trace |
| `05-dashboard-6-panels.png` | đủ 6 panel | mở `docs/dashboard.md` (preview Markdown trong VS Code) |
| `06-alert-rules.png` | 4 alert rule + dòng `runbook:` | mở `config/alert_rules.yaml` |

## Tùy chọn (Bonus — tăng điểm)

| Tên file | Chụp cái gì | Lấy ở đâu |
|---|---|---|
| `07-incident-before-after.png` | latency/error trước–sau khi inject | terminal DEMO mục 8, hoặc dashboard 2 lần |
| `08-cost-optimization.png` | bảng cost −69.9% | mở `docs/cost-optimization.md`, hoặc output `cost_benchmark.py` |
| `09-langfuse-optimized-tags.png` | trace có tag `optimized` + `claude-haiku-4-5` | Langfuse, lọc tag `optimized` |

## Sau khi chụp xong

Mở `docs/blueprint-template.md` mục 3 — các đường dẫn ảnh đã được điền sẵn trỏ về
`docs/evidence/<tên-file>.png`. Chỉ cần lưu ảnh đúng tên là khớp, không cần sửa gì thêm.
