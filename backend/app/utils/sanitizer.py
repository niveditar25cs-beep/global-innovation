"""
Input sanitization and credential/secret redaction utilities.
Ensures zero credential leakage in logs, error payloads, and traces.
"""

import re
from typing import Any

# Common sensitive field keys
SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "apikey",
    "private_key",
    "cookie",
    "session_id",
    "database_url",
    "redis_url",
}

# Regex to detect connection strings with passwords: protocol://user:password@host
CONN_STRING_PATTERN = re.compile(r"([a-zA-Z0-9\+]+://[^:]+:)([^@]+)(@.+)")


def sanitize_text(text: str, max_length: int = 500) -> str:
    """
    Sanitize text input by removing null bytes, stripping whitespace,
    and limiting excessive length.
    """
    if not isinstance(text, str):
        return str(text)
    cleaned = text.replace("\x00", "").strip()
    return cleaned[:max_length]


def mask_connection_string(text: str) -> str:
    """
    Redact passwords from database and cache connection strings in arbitrary text.
    """
    if not isinstance(text, str):
        return text
    return CONN_STRING_PATTERN.sub(r"\1***\3", text)


def redact_sensitive_data(data: Any) -> Any:
    """
    Recursively sanitize dictionaries, lists, and strings to redact
    passwords, tokens, and connection strings.
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = redact_sensitive_data(v)
        return sanitized
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    elif isinstance(data, str):
        return mask_connection_string(data)
    return data
