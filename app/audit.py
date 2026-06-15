from __future__ import annotations

"""Separate, append-only audit trail (Bonus: audit logs tách riêng).

The main application logs (``data/logs.jsonl``) are operational and may be
rotated/sampled aggressively. Audit logs capture security- and
compliance-relevant events (who did what, when, with which correlation id) and
are written to a *dedicated* file so they can be retained and access-controlled
independently. All free-text fields are PII-scrubbed before they are written.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from structlog.contextvars import get_contextvars

from .pii import scrub_text

AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))


def _sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


def audit(action: str, actor: str | None = None, **fields: Any) -> None:
    """Append one sanitized audit record to the dedicated audit log."""
    ctx = get_contextvars()
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "audit",
        "action": action,
        "actor": actor,
        "correlation_id": ctx.get("correlation_id"),
        "session_id": ctx.get("session_id"),
        "env": os.getenv("APP_ENV", "dev"),
        **_sanitize(fields),
    }
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
