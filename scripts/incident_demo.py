"""In bảng latency/error TRƯỚC và SAU khi inject sự cố (ảnh 07).

Chạy khi server đang bật:  python scripts/incident_demo.py
"""

import time

import httpx

BASE_URL = "http://127.0.0.1:8000"


def call(message: str) -> tuple[int, int]:
    start = time.perf_counter()
    try:
        r = httpx.post(
            f"{BASE_URL}/chat",
            json={"user_id": "u_demo", "session_id": "s_demo", "feature": "qa", "message": message},
            timeout=20.0,
        )
        return r.status_code, round((time.perf_counter() - start) * 1000)
    except Exception as exc:
        print("Lỗi: không gọi được server. Hãy bật server trước (uvicorn ... --env-file .env).", exc)
        raise SystemExit(1)


def toggle(scenario: str, enable: bool) -> None:
    path = "enable" if enable else "disable"
    httpx.post(f"{BASE_URL}/incidents/{scenario}/{path}", timeout=10.0)


def row(label: str, status: int, latency_ms: int) -> str:
    return f"| {label:<22} | {status:^6} | {latency_ms:>9} |"


def main() -> None:
    print("=" * 50)
    print(" INCIDENT BEFORE / AFTER  (ảnh 07)")
    print("=" * 50)
    print("| Trạng thái             | HTTP   | Latency ms |")
    print("|------------------------|--------|------------|")

    # rag_slow: latency tăng vọt
    s, l = call("monitoring help")
    print(row("BEFORE (bình thường)", s, l))
    toggle("rag_slow", True)
    s, l = call("monitoring help")
    print(row("AFTER  rag_slow ON", s, l))
    toggle("rag_slow", False)

    print("|------------------------|--------|------------|")

    # tool_fail: lỗi 500
    s, l = call("refund policy")
    print(row("BEFORE (bình thường)", s, l))
    toggle("tool_fail", True)
    s, l = call("refund policy")
    print(row("AFTER  tool_fail ON", s, l))
    toggle("tool_fail", False)

    print("=" * 50)
    print("rag_slow  -> latency ~150ms => ~2700ms (RAG span ngủ 2.5s)")
    print("tool_fail -> HTTP 200 => 500 (RuntimeError: Vector store timeout)")


if __name__ == "__main__":
    main()
