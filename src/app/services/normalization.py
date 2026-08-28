"""Input and result normalization utilities."""

from __future__ import annotations

import re

import phonenumbers

from app.schemas.results import OSINTResult

# ── Input normalization ──────────────────────────────────────────────


def normalize_email(email: str) -> str:
    """Normalize an email address: lowercase, strip whitespace."""
    return email.strip().lower()


def normalize_username(username: str) -> str:
    """Normalize a username: strip whitespace and leading @ symbols."""
    return username.strip().lstrip("@")


def normalize_phone(phone: str) -> str:
    """Normalize a phone number to E.164 format.

    Attempts to parse with phonenumbers library.  Falls back to
    stripping non-digit characters (keeping a leading +) when parsing
    fails.
    """
    raw = phone.strip()
    try:
        parsed = phonenumbers.parse(raw, None)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
    except phonenumbers.NumberParseException:
        pass

    # Fallback: strip non-digit chars but keep leading +
    cleaned = re.sub(r"[^\d+]", "", raw)
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def normalize_target(target_type: str, value: str) -> str:
    """Dispatch to the appropriate normalizer based on target type."""
    normalizers = {
        "email": normalize_email,
        "username": normalize_username,
        "phone": normalize_phone,
    }
    normalizer = normalizers.get(target_type)
    if normalizer is None:
        return value.strip()
    return normalizer(value)


# ── Input validation ─────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9._\-]{1,64}$")
_PHONE_RE = re.compile(r"^\+?\d{7,15}$")


def validate_target(target_type: str, value: str) -> tuple[bool, str]:
    """Validate a target value. Returns (is_valid, error_message)."""
    validators = {
        "email": (_EMAIL_RE, "Invalid email format"),
        "username": (
            _USERNAME_RE,
            "Invalid username format (1-64 alphanumeric, dots, underscores, hyphens)",
        ),
        "phone": (_PHONE_RE, "Invalid phone number format (7-15 digits, optional leading +)"),
    }
    pattern, error = validators.get(target_type, (None, ""))
    if pattern is None:
        return False, f"Unknown target type: {target_type}"
    if not pattern.match(value):
        return False, error
    return True, ""


# ── Result normalization ─────────────────────────────────────────────


def normalize_url(url: str | None) -> str | None:
    """Normalize a URL: strip trailing slashes, lowercase the scheme/host."""
    if not url:
        return url
    url = url.strip().rstrip("/")
    # Lowercase scheme and host only
    if "://" in url:
        scheme, rest = url.split("://", 1)
        if "/" in rest:
            host, path = rest.split("/", 1)
            url = f"{scheme.lower()}://{host.lower()}/{path}"
        else:
            url = f"{scheme.lower()}://{rest.lower()}"
    return url


def normalize_results(results: list[OSINTResult]) -> list[OSINTResult]:
    """Normalize a list of OSINT results: clean URLs, enforce bounds."""
    normalized = []
    for result in results:
        normalized.append(
            result.model_copy(
                update={
                    "url": normalize_url(result.url),
                    "confidence": max(0.0, min(1.0, result.confidence)),
                    "value": result.value.strip() if result.value else result.value,
                }
            )
        )
    return normalized
