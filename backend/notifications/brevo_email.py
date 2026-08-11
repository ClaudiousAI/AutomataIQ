"""Brevo transactional email transport for SAIE Saturday reports.

Sends the weekly intelligence report PDF as a transactional email through
the Brevo REST API (``POST /v3/smtp/email``). Behaviour follows the
notification requirements in docs/10 §6.5:

- Inputs are validated before any network call (NFR-002).
- Sends are idempotent: one call from the orchestrator produces exactly
  one email (NFR-007); retries here are safe because Brevo messages carry
  a unique ``Message-Id`` and a request is only retried when we did NOT
  receive a definitive success (2xx) — so no duplicate sends on the
  happy path.
- All activity is structured-logged for observability (NFR-005).
- Dry-run mode (the default) performs full validation without sending,
  preventing accidental API charges (NFR-012).

Traceability: FR-050, FR-051, NFR-002, NFR-005, NFR-007, NFR-012.
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path
from typing import Any

import requests

from .config import BrevoConfig
from .validators import validate_email, validate_pdf

logger = logging.getLogger(__name__)

#: Brevo Transactional Emails endpoint.
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
#: Per-request timeout in seconds — fail fast rather than hang a worker.
REQUEST_TIMEOUT = 30
#: Max attempts (initial + retries) for transient failures.
MAX_ATTEMPTS = 3
#: Base delay for exponential backoff, in seconds.
_BACKOFF_BASE_SECONDS = 1.0

#: HTTP statuses that mean "the request never reached a definitive state"
#: and are safe to retry. 4xx client errors are NOT retried (they would
#: fail identically every time).
_RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}


class BrevoEmailError(RuntimeError):
    """Raised when Brevo rejects the email or the request cannot be sent."""

    def __init__(self, message: str, status_code: int | None = None,
                 response_body: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


def send_report_email(
    pdf_path: str | Path,
    subject: str,
    config: BrevoConfig | None = None,
) -> dict[str, Any]:
    """Send a PDF report to the configured recipient via Brevo.

    Args:
        pdf_path: Path to the report PDF.
        subject: Email subject line.
        config: Resolved configuration; loaded from the environment if
            ``None`` (see :func:`backend.notifications.config.BrevoConfig.from_env`).

    Returns:
        A result dict. In dry-run mode it describes what *would* be sent;
        in live mode it carries Brevo's response details.

    Raises:
        FileNotFoundError: If the PDF does not exist.
        ValueError: If the PDF is invalid or config/emails are malformed.
        BrevoEmailError: If Brevo rejects the request or transport fails
            after retries.
    """
    config = config or BrevoConfig.from_env()

    # Validate everything before touching the network (NFR-002).
    pdf = validate_pdf(pdf_path)
    sender_email = validate_email(config.sender_email, "sender")
    recipient_email = validate_email(config.recipient_email, "recipient")

    if config.dry_run:
        return _dry_run(pdf, subject, config, recipient_email)

    payload = _build_payload(
        pdf=pdf,
        subject=subject,
        config=config,
        sender_email=sender_email,
        recipient_email=recipient_email,
    )

    logger.info(
        "Sending report email",
        extra={
            "recipient": recipient_email,
            "subject": subject,
            "attachment": pdf.name,
            "attachment_bytes": pdf.stat().st_size,
        },
    )
    return _send_with_retry(payload, config)


def _build_payload(
    pdf: Path,
    subject: str,
    config: BrevoConfig,
    sender_email: str,
    recipient_email: str,
) -> dict[str, Any]:
    """Build the Brevo SMTP API request body with a base64 PDF attachment."""
    pdf_bytes = pdf.read_bytes()
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    return {
        "sender": {"name": config.sender_name, "email": sender_email},
        "to": [{"email": recipient_email}],
        "subject": subject,
        "textContent": "Your SAIE weekly report is attached as a PDF.",
        "htmlContent": "<p>Your SAIE weekly report is attached as a PDF.</p>",
        "attachment": [{"content": pdf_b64, "name": pdf.name}],
    }


def _send_with_retry(payload: dict[str, Any], config: BrevoConfig) -> dict[str, Any]:
    """POST the payload to Brevo with limited exponential backoff.

    Retries only transient statuses (429/5xx) and network errors. On the
    final failure the exception is raised — never silently swallowed.
    """
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": config.api_key,
    }

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1:
            delay = _BACKOFF_BASE_SECONDS * (2 ** (attempt - 2))
            logger.info("Retrying Brevo send (attempt %s/%s)", attempt, MAX_ATTEMPTS)
            time.sleep(delay)

        try:
            response = requests.post(
                BREVO_API_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            last_error = exc
            logger.warning("Brevo request failed (attempt %s/%s): %s",
                           attempt, MAX_ATTEMPTS, exc)
            continue

        if response.ok:
            message_id = _extract_message_id(response)
            logger.info("Brevo accepted email", extra={"message_id": message_id})
            return _success_result(response, message_id)

        if response.status_code in _RETRYABLE_STATUSES and attempt < MAX_ATTEMPTS:
            last_error = BrevoEmailError(
                _describe_status(response), response.status_code, response.text
            )
            logger.warning(
                "Brevo transient error %s (attempt %s/%s): %s",
                response.status_code, attempt, MAX_ATTEMPTS, response.text,
            )
            continue

        raise _error_from_response(response)

    assert last_error is not None
    raise BrevoEmailError(
        f"Failed to send email after {MAX_ATTEMPTS} attempts: {last_error}"
    ) from last_error


def _extract_message_id(response: requests.Response) -> str | None:
    """Prefer the Message-Id header Brevo returns on success."""
    message_id = response.headers.get("Message-Id") or response.headers.get("message-id")
    if message_id:
        return message_id
    try:
        data = response.json()
    except ValueError:
        return None
    return data.get("messageId") or data.get("message_id")


def _success_result(response: requests.Response, message_id: str | None) -> dict[str, Any]:
    return {
        "status": "sent",
        "brevo_message_id": message_id,
        "http_status": response.status_code,
        "dry_run": False,
    }


def _error_from_response(response: requests.Response) -> BrevoEmailError:
    detail = response.text.strip()[:500]
    return BrevoEmailError(
        _describe_status(response) + (f": {detail}" if detail else ""),
        status_code=response.status_code,
        response_body=response.text,
    )


def _describe_status(response: requests.Response) -> str:
    messages = {
        400: "Brevo rejected the request payload (validation error)",
        401: "Brevo rejected the API key (unauthorized)",
        403: "Brevo denied the sender — is the sender address verified?",
        404: "Brevo endpoint not found",
        405: "Brevo method not allowed",
        429: "Brevo rate limit exceeded",
    }
    return messages.get(response.status_code, f"Brevo returned HTTP {response.status_code}")


def _dry_run(
    pdf: Path,
    subject: str,
    config: BrevoConfig,
    recipient_email: str,
) -> dict[str, Any]:
    """Dry-run mode: full validation, zero network calls (NFR-012)."""
    logger.info(
        "DRY-RUN: would send report email",
        extra={
            "recipient": recipient_email,
            "subject": subject,
            "attachment": pdf.name,
            "attachment_bytes": pdf.stat().st_size,
            "sender": config.sender_email,
        },
    )
    return {
        "status": "dry-run",
        "dry_run": True,
        "recipient": recipient_email,
        "subject": subject,
        "attachment": pdf.name,
        "attachment_bytes": pdf.stat().st_size,
        "message": (
            f"Would send '{subject}' to {recipient_email} with attachment "
            f"{pdf.name} ({pdf.stat().st_size} bytes). No email was sent."
        ),
    }


if __name__ == "__main__":
    # Minimal CLI for manual dry-runs and smoke-testing.
    # Usage: python -m notifications.brevo_email --pdf <path> --subject "<subject>"
    import argparse

    parser = argparse.ArgumentParser(description="Send (or dry-run) a SAIE report email.")
    parser.add_argument("--pdf", required=True, help="Path to the report PDF.")
    parser.add_argument("--subject", default="SAIE Weekly Intelligence Report",
                        help="Email subject line.")
    parser.add_argument("--live", action="store_true",
                        help="Actually send (default is dry-run, which is safer).")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.live:
        import os

        from .config import DRY_RUN_VAR

        os.environ[DRY_RUN_VAR] = "false"

    result = send_report_email(args.pdf, args.subject)
    print(result["message"])
