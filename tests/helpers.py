"""Shared test utilities."""

import uuid


def unique_name(prefix: str = "test") -> str:
    """Generate a unique name for test resources."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"
