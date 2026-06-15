from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from .incidents import STATE


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class FakeResponse:
    text: str
    usage: FakeUsage
    model: str


def _base_output_tokens(prompt: str) -> int:
    # Deterministic across processes/runs (unlike random + PYTHONHASHSEED) so the
    # cost benchmark is reproducible: same prompt -> same base output tokens.
    digest = int(hashlib.md5(prompt.encode("utf-8")).hexdigest()[:8], 16)
    return 80 + (digest % 101)  # 80..180


class FakeLLM:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> FakeResponse:
        time.sleep(0.15)
        used_model = model or self.model
        input_tokens = max(20, len(prompt) // 4)
        output_tokens = _base_output_tokens(prompt)
        if STATE["cost_spike"]:
            output_tokens *= 4
        if max_output_tokens is not None:
            output_tokens = min(output_tokens, max_output_tokens)
        answer = (
            "Starter answer. Teams should improve this output logic and add better quality checks. "
            "Use retrieved context and keep responses concise."
        )
        return FakeResponse(text=answer, usage=FakeUsage(input_tokens, output_tokens), model=used_model)
