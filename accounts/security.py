import re
from typing import Any

from django.conf import settings
from django.core.cache import cache

PHONE_PATTERN = re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)

BLOCKED_TERMS = (
    "kill yourself",
    "kys",
    "send nudes",
    "share your password",
    "share your address",
)


def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def rate_limit_key(scope: str, identifier: str) -> str:
    return f"desktap:ratelimit:{scope}:{identifier}"


def is_rate_limited(scope: str, identifier: str, limit: int, period: int) -> bool:
    key = rate_limit_key(scope, identifier)
    return cache.get(key, 0) >= limit


def record_rate_limit_attempt(scope: str, identifier: str, period: int) -> int:
    key = rate_limit_key(scope, identifier)
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, period)
        return 1


def clear_rate_limit(scope: str, identifier: str) -> None:
    cache.delete(rate_limit_key(scope, identifier))


def validate_safe_content(text: str) -> list[str]:
    issues: list[str] = []
    lowered = text.lower()

    if PHONE_PATTERN.search(text):
        issues.append("Phone numbers are not allowed in posts or comments.")
    if EMAIL_PATTERN.search(text):
        issues.append("Email addresses are not allowed in posts or comments.")
    if URL_PATTERN.search(text):
        issues.append("External links are not allowed in posts or comments.")
    for term in BLOCKED_TERMS:
        if term in lowered:
            issues.append("This content contains language that is not allowed.")
            break

    return issues


def log_security_event(
    event_type: str,
    request=None,
    user=None,
    metadata: dict[str, Any] | None = None,
) -> None:
    from accounts.models import SecurityEvent

    SecurityEvent.objects.create(
        event_type=event_type,
        user=user,
        ip_address=get_client_ip(request) if request else "",
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500] if request else "",
        metadata=metadata or {},
    )


def login_rate_limit_settings() -> tuple[int, int]:
    return (
        getattr(settings, "LOGIN_RATE_LIMIT", 5),
        getattr(settings, "LOGIN_RATE_LIMIT_PERIOD", 900),
    )
