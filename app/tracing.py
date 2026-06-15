from __future__ import annotations

import os
from typing import Any

# Load .env even when the app is started without `uvicorn --env-file`, so the
# Langfuse credentials are always picked up. Harmless if the file is absent.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass

# The v3 SDK reads LANGFUSE_HOST. Accept the legacy/alternate LANGFUSE_BASE_URL
# name too, and strip any stray surrounding quotes from the value.
_host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")
if _host:
    os.environ["LANGFUSE_HOST"] = _host.strip().strip('"').strip("'")


try:
    # Langfuse v3 API: `observe` is top-level, the old `langfuse.decorators`
    # module and `langfuse_context` object no longer exist. We expose a thin
    # `langfuse_context` shim so the rest of the app keeps the same call sites.
    from langfuse import get_client, observe  # type: ignore

    class _ContextShim:
        def update_current_trace(self, **kwargs: Any) -> None:
            try:
                get_client().update_current_trace(**kwargs)
            except Exception:  # pragma: no cover - never break a request on tracing
                pass

        def update_current_observation(
            self,
            metadata: dict[str, Any] | None = None,
            usage_details: dict[str, Any] | None = None,
            **kwargs: Any,
        ) -> None:
            # `@observe()` opens a span; usage lives on generations, so we fold
            # usage_details into the span metadata to keep it visible on the trace.
            md = dict(metadata or {})
            if usage_details is not None:
                md.setdefault("usage_details", usage_details)
            try:
                get_client().update_current_span(metadata=md or None, **kwargs)
            except Exception:  # pragma: no cover
                pass

    langfuse_context = _ContextShim()

except Exception:  # pragma: no cover - SDK missing or import error -> no-op tracing
    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyContext:
        def update_current_trace(self, **kwargs: Any) -> None:
            return None

        def update_current_observation(self, **kwargs: Any) -> None:
            return None

    langfuse_context = _DummyContext()


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def flush_traces() -> None:
    """Force-flush buffered spans to Langfuse (call on shutdown / after a batch)."""
    if not tracing_enabled():
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:  # pragma: no cover
        pass
