"""Email address validation.

Public email addresses are validated with ``email_validator`` (the same rules
``pydantic.EmailStr`` applies). One deliberate exception: an on-premise
procurement deployment legitimately uses intranet addresses such as
``admin@epi.local``, and ``email_validator`` 2.x rejects special-use/reserved
names. Those are accepted *only* when the domain still has a well-formed shape,
so a real typo is still rejected while ``admin@epi.local`` keeps working.
"""

from __future__ import annotations

import re
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import BeforeValidator, StringConstraints

_EMAIL_SHAPE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z0-9-]{2,}$", re.IGNORECASE)
_SPECIAL_USE_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")


def normalize_email(value: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError("An email address is required.")
    try:
        return validate_email(text, check_deliverability=False).normalized
    except EmailNotValidError as exc:
        message = str(exc)
        special_use = "special-use" in message or "reserved" in message
        if special_use and _EMAIL_SHAPE_RE.match(text):
            local, _, domain = text.lower().rpartition("@")
            if local and _SPECIAL_USE_RE.match(domain):
                # Intranet domain (e.g. corp.local): keep it, lower-cased.
                return f"{local}@{domain}".lower()
        raise ValueError(message) from exc


EmailAddress = Annotated[
    str,
    BeforeValidator(normalize_email),
    StringConstraints(max_length=320),
]
