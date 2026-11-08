"""Login identifier rules. Mirrors frontend/src/lib/validators.ts exactly."""

import re
from typing import Literal

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
PHONE_RE = re.compile(r"^(?:0|\+94|94)?7\d{8}$")

IdentifierKind = Literal["email", "phone"]


def normalise_identifier(raw: str) -> tuple[IdentifierKind, str] | None:
    """Return (kind, normalised value), or None when it is neither email nor phone.

    Email: trimmed and lower-cased. Phone: +947XXXXXXXXX.
    """
    value = (raw or "").strip()
    if not value:
        return None
    if EMAIL_RE.match(value):
        return "email", value.lower()
    digits = re.sub(r"[\s-]", "", value)
    if PHONE_RE.match(digits):
        national = re.sub(r"^(?:0|\+94|94)", "", digits)
        return "phone", f"+94{national}"
    return None
