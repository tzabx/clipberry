"""Utility functions and helpers."""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any


def generate_device_id() -> str:
    """Generate a unique device ID."""
    return str(uuid.uuid4())


def generate_pairing_token(length: int = 8) -> str:
    """Generate a short-lived pairing token."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # No ambiguous chars
    return "".join(secrets.choice(alphabet) for _ in range(length))


def compute_content_hash(data: bytes) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(data).hexdigest()


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


def utc_timestamp() -> float:
    """Get current UTC timestamp."""
    return utc_now().timestamp()


def format_timestamp(ts: float) -> str:
    """Format timestamp for display."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_size(size: int) -> str:
    """Format byte size for display."""
    size_float = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_float < 1024.0:
            return f"{size_float:.1f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.1f} TB"
