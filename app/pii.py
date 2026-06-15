from __future__ import annotations

import hashlib
import re

# Order matters: longer / more specific patterns run first so that a 16-digit
# card is not partially eaten by the 12-digit CCCD rule, etc.
PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    # CCCD (exactly 12 digits) must run BEFORE phone_vn: otherwise the phone
    # rule greedily consumes 11 of the 12 digits and leaves a dangling digit.
    "cccd": r"\b\d{12}\b",
    "phone_vn": r"(?:\+84|0)[ \.-]?\d{3}[ \.-]?\d{3}[ \.-]?\d{3,4}", # Matches 090 123 4567, 090.123.4567, etc.
    # Vietnamese passport: one uppercase letter followed by 7 digits (e.g. B1234567, C2345678).
    "passport": r"\b[A-Z]\d{7}\b",
    # Vietnamese street address: "số 12 đường/phố ..." up to the next comma/newline.
    "address_vn": r"(?i)\bsố\s*\d+[^,\n]*?(?:đường|phố|ngõ|ngách)\s+[^,\n]+",
    # Administrative unit references that often carry an address fragment.
    "admin_unit_vn": r"(?i)\b(?:phường|quận|huyện|tỉnh|thành phố)\s+[\wÀ-ỹ]+(?:\s+[\wÀ-ỹ]+){0,2}",
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
