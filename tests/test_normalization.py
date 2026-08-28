"""Tests for normalization and deduplication services."""

from __future__ import annotations

from app.schemas.results import OSINTResult, ResultCategory, ResultStatus
from app.services.deduplication import deduplicate
from app.services.normalization import (
    normalize_email,
    normalize_phone,
    normalize_results,
    normalize_target,
    normalize_url,
    normalize_username,
    validate_target,
)

# ── Input normalization ──────────────────────────────────────────


class TestNormalizeEmail:
    def test_lowercase(self):
        assert normalize_email("User@Example.COM") == "user@example.com"

    def test_strips_whitespace(self):
        assert normalize_email("  user@test.com  ") == "user@test.com"


class TestNormalizeUsername:
    def test_strips_at(self):
        assert normalize_username("@testuser") == "testuser"

    def test_strips_whitespace(self):
        assert normalize_username("  testuser  ") == "testuser"

    def test_preserves_case(self):
        assert normalize_username("TestUser") == "TestUser"


class TestNormalizePhone:
    def test_e164_format(self):
        result = normalize_phone("+1 (555) 123-4567")
        assert result.startswith("+")
        assert " " not in result

    def test_plain_digits(self):
        result = normalize_phone("15551234567")
        assert "+" in result

    def test_already_e164(self):
        result = normalize_phone("+15551234567")
        assert result == "+15551234567"


class TestNormalizeTarget:
    def test_email_dispatch(self):
        assert normalize_target("email", "A@B.COM") == "a@b.com"

    def test_username_dispatch(self):
        assert normalize_target("username", "@user") == "user"

    def test_phone_dispatch(self):
        result = normalize_target("phone", "+1234567890")
        assert result.startswith("+")

    def test_unknown_type_strips(self):
        assert normalize_target("unknown", "  val  ") == "val"


# ── Input validation ────────────────────────────────────────────


class TestValidateTarget:
    def test_valid_email(self):
        ok, _ = validate_target("email", "test@example.com")
        assert ok

    def test_invalid_email(self):
        ok, msg = validate_target("email", "not-an-email")
        assert not ok
        assert "email" in msg.lower()

    def test_valid_username(self):
        ok, _ = validate_target("username", "testuser")
        assert ok

    def test_invalid_username_special_chars(self):
        ok, _ = validate_target("username", "test user!")
        assert not ok

    def test_valid_phone(self):
        ok, _ = validate_target("phone", "+1234567890")
        assert ok

    def test_invalid_phone_too_short(self):
        ok, _ = validate_target("phone", "123")
        assert not ok

    def test_unknown_type(self):
        ok, _ = validate_target("other", "value")
        assert not ok


# ── URL normalization ────────────────────────────────────────────


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com/user/") == "https://example.com/user"

    def test_lowercases_scheme_and_host(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/Path") == "https://example.com/Path"

    def test_none_passthrough(self):
        assert normalize_url(None) is None

    def test_empty_string(self):
        assert normalize_url("") == ""


# ── Result normalization ─────────────────────────────────────────


class TestNormalizeResults:
    def test_clamps_confidence(self):
        result = OSINTResult(
            source="test",
            category=ResultCategory.USERNAME,
            status=ResultStatus.FOUND,
            value="user",
            confidence=1.5,
        )
        normalized = normalize_results([result])
        assert normalized[0].confidence == 1.0

    def test_strips_value(self):
        result = OSINTResult(
            source="test",
            category=ResultCategory.USERNAME,
            status=ResultStatus.FOUND,
            value="  user  ",
            confidence=0.5,
        )
        normalized = normalize_results([result])
        assert normalized[0].value == "user"


# ── Deduplication ────────────────────────────────────────────────


class TestDeduplicate:
    def test_removes_exact_duplicates_keeps_higher_confidence(self):
        r1 = OSINTResult(
            source="provider_a",
            category=ResultCategory.USERNAME,
            status=ResultStatus.FOUND,
            value="user",
            url="https://example.com/user",
            confidence=0.7,
        )
        r2 = OSINTResult(
            source="provider_b",
            category=ResultCategory.USERNAME,
            status=ResultStatus.FOUND,
            value="user",
            url="https://example.com/user",
            confidence=0.9,
        )
        results = deduplicate([r1, r2])
        assert len(results) == 1
        assert results[0].confidence == 0.9

    def test_keeps_different_categories(self):
        r1 = OSINTResult(
            source="provider_a",
            category=ResultCategory.USERNAME,
            status=ResultStatus.FOUND,
            value="user",
            url="https://example.com/user",
            confidence=0.7,
        )
        r2 = OSINTResult(
            source="provider_b",
            category=ResultCategory.EMAIL,
            status=ResultStatus.FOUND,
            value="user",
            url="https://example.com/user",
            confidence=0.9,
        )
        results = deduplicate([r1, r2])
        assert len(results) == 2

    def test_keeps_different_urls(self):
        r1 = OSINTResult(
            source="provider_a",
            category=ResultCategory.USERNAME,
            status=ResultStatus.FOUND,
            value="user",
            url="https://twitter.com/user",
            confidence=0.7,
        )
        r2 = OSINTResult(
            source="provider_b",
            category=ResultCategory.USERNAME,
            status=ResultStatus.FOUND,
            value="user",
            url="https://github.com/user",
            confidence=0.9,
        )
        results = deduplicate([r1, r2])
        assert len(results) == 2

    def test_empty_input(self):
        assert deduplicate([]) == []
