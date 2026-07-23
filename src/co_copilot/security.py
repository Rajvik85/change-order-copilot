"""Upload and filename hardening for public multi-user deployments."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from co_copilot.exceptions import ValidationError

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    """Remove path components and unsafe characters from an uploaded name."""
    safe = _SAFE_FILENAME.sub("_", Path(filename).name).strip("._")
    if not safe:
        raise ValidationError("The uploaded filename has no usable characters.")
    return safe[:160]


def validate_upload(
    filename: str,
    size_bytes: int,
    content_type: str | None,
    config: dict[str, Any],
) -> str:
    """Validate an upload before its bytes enter the parsing pipeline.

    Args:
        filename: Browser-supplied name.
        size_bytes: Uploaded byte count.
        content_type: Browser-supplied MIME type, treated only as a hint.
        config: Application configuration.

    Returns:
        Sanitized filename.

    Raises:
        ValidationError: If size or type is unsafe or unsupported.
    """
    safe_name = sanitize_filename(filename)
    extension = Path(safe_name).suffix.lower()
    rules = config["uploads"]
    if extension in set(rules["rejected_extensions"]):
        raise ValidationError(
            f"{extension or 'This file type'} is rejected for safety. "
            "Upload an individual change-order document instead."
        )
    if extension not in set(rules["allowed_extensions"]):
        raise ValidationError(
            f"{extension or 'Files without an extension'} are not supported. "
            f"Allowed: {', '.join(rules['allowed_extensions'])}."
        )
    limit = int(rules["max_file_size_mb"]) * 1024 * 1024
    if size_bytes > limit:
        raise ValidationError(
            f"{safe_name} is {size_bytes / 1024 / 1024:.1f} MB; the public-app "
            f"limit is {rules['max_file_size_mb']} MB per file."
        )
    if content_type and any(
        token in content_type.lower()
        for token in ("executable", "archive", "x-sh", "x-msdownload")
    ):
        raise ValidationError(
            "The reported content type is unsafe for a document upload."
        )
    return safe_name
