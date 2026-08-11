"""Input validation for the Brevo email transport.

Validation happens before any HTTP request so misconfiguration and bad
payloads fail fast and cheap — a key part of "never publish incomplete"
(NFR-002) and of keeping failed sends out of the network path (FR-055).
"""

from __future__ import annotations

import re
from pathlib import Path

#: Minimal, pragmatic email check — validates structure, not deliverability.
#: Full RFC-5322 regexes are overkill here and reject legitimate addresses.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

#: Attachment filename length upper bound (defensive; Brevo allows more).
_MAX_FILENAME_CHARS = 255


def validate_pdf(pdf_path: str | Path) -> Path:
    """Validate a PDF path is suitable for attachment.

    Args:
        pdf_path: Path to the report PDF.

    Returns:
        The resolved absolute :class:`~pathlib.Path`.

    Raises:
        FileNotFoundError: If the file does not exist or is not a file.
        ValueError: If the path has a non-``.pdf`` suffix, is empty, or is
            otherwise unsuitable as an attachment.
    """
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"Report PDF not found: {path}")
    if not path.is_file():
        raise ValueError(f"Report PDF path is not a regular file: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Report file must be a PDF, got extension {path.suffix!r}: {path}"
        )

    if path.stat().st_size == 0:
        raise ValueError(f"Report PDF is empty (0 bytes): {path}")

    if len(path.name) > _MAX_FILENAME_CHARS:
        raise ValueError(
            f"Report PDF filename exceeds {_MAX_FILENAME_CHARS} characters: {path.name!r}"
        )

    return path.resolve()


def validate_email(email: str, label: str) -> str:
    """Validate an email address.

    Args:
        email: The address to validate.
        label: Field name used in the error message (e.g. ``"sender"``).

    Returns:
        The trimmed address.

    Raises:
        ValueError: If the address does not look like an email.
    """
    value = email.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError(f"Invalid {label} email address: {email!r}")
    return value
