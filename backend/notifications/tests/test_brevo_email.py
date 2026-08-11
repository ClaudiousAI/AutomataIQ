"""Tests for the Brevo email transport.

Verifies behaviour required by FR-050 (report export delivery), FR-051
(configurable recipient), NFR-002 (never publish incomplete — validation
gates), NFR-005 (observability), NFR-007 (idempotent, no duplicate
sends), NFR-012 (dry-run default prevents cost).

The Brevo HTTP endpoint is always mocked; no test performs a real network
call.
"""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from notifications.brevo_email import (
    BREVO_API_URL,
    REQUEST_TIMEOUT,
    BrevoEmailError,
    send_report_email,
)
from notifications.config import BrevoConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _config(**overrides) -> BrevoConfig:
    defaults = dict(
        api_key="test-api-key",
        sender_email="sender@example.com",
        sender_name="SAIE Test",
        recipient_email="recipient@example.com",
        dry_run=False,
    )
    defaults.update(overrides)
    return BrevoConfig(**defaults)


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    """A small valid PDF fixture (well-formed enough to be attached)."""
    pdf = tmp_path / "saie-report.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% SAIE test report\n%%EOF\n")
    return pdf


def _ok_response(status: int = 201, **headers) -> Mock:
    mock = Mock(spec=requests.Response)
    mock.status_code = status
    mock.ok = 200 <= status < 300
    mock.text = ""
    mock.headers = {"Message-Id": "msg_123"} | headers
    mock.json.return_value = {"messageId": "msg_123"}
    return mock


def _error_response(status: int, body: str = "") -> Mock:
    mock = Mock(spec=requests.Response)
    mock.status_code = status
    mock.ok = False
    mock.text = body
    mock.headers = {}
    return mock


# ---------------------------------------------------------------------------
# Happy path — request construction
# ---------------------------------------------------------------------------

class TestRequestConstruction:
    def test_send_calls_correct_endpoint(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post",
                   return_value=_ok_response()) as post:
            send_report_email(pdf_file, "Weekly Report", _config())
        post.assert_called_once()
        assert post.call_args.args[0] == BREVO_API_URL

    def test_api_key_header_set(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post",
                   return_value=_ok_response()) as post:
            send_report_email(pdf_file, "Weekly Report", _config(api_key="secret-key"))
        headers = post.call_args.kwargs["headers"]
        assert headers["api-key"] == "secret-key"

    def test_request_is_post_with_json(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post",
                   return_value=_ok_response()) as post:
            send_report_email(pdf_file, "Weekly Report", _config())
        # The payload is passed as JSON to the POST endpoint.
        assert "json" in post.call_args.kwargs
        assert "method" not in post.call_args.kwargs  # requests.post, not a generic request()

    def test_timeout_set(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post",
                   return_value=_ok_response()) as post:
            send_report_email(pdf_file, "Weekly Report", _config())
        assert post.call_args.kwargs["timeout"] == REQUEST_TIMEOUT

    def test_recipient_and_sender_in_payload(self, pdf_file: Path):
        cfg = _config(sender_name="SAIE", sender_email="s@example.com",
                      recipient_email="r@example.com")
        with patch("notifications.brevo_email.requests.post",
                   return_value=_ok_response()) as post:
            send_report_email(pdf_file, "Subject", cfg)
        payload = post.call_args.kwargs["json"]
        assert payload["to"] == [{"email": "r@example.com"}]
        assert payload["sender"] == {"name": "SAIE", "email": "s@example.com"}
        assert payload["subject"] == "Subject"

    def test_pdf_base64_encoded(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post",
                   return_value=_ok_response()) as post:
            send_report_email(pdf_file, "Weekly Report", _config())
        payload = post.call_args.kwargs["json"]
        content = payload["attachment"][0]["content"]
        # Decoding must succeed and match the exact file bytes.
        assert base64.b64decode(content) == pdf_file.read_bytes()

    def test_attachment_filename(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post",
                   return_value=_ok_response()) as post:
            send_report_email(pdf_file, "Weekly Report", _config())
        payload = post.call_args.kwargs["json"]
        assert payload["attachment"][0]["name"] == pdf_file.name


# ---------------------------------------------------------------------------
# Validation gates — no network call on invalid input (NFR-002)
# ---------------------------------------------------------------------------

class TestValidationGates:
    def test_no_request_on_missing_pdf(self):
        with patch("notifications.brevo_email.requests.post") as post:
            with pytest.raises(FileNotFoundError):
                send_report_email("C:/nonexistent/report.pdf", "Subject", _config())
        post.assert_not_called()

    def test_no_request_on_empty_pdf(self, tmp_path: Path):
        empty = tmp_path / "empty.pdf"
        empty.write_bytes(b"")
        with patch("notifications.brevo_email.requests.post") as post:
            with pytest.raises(ValueError, match="empty"):
                send_report_email(empty, "Subject", _config())
        post.assert_not_called()

    def test_no_request_on_wrong_extension(self, tmp_path: Path):
        txt = tmp_path / "report.txt"
        txt.write_bytes(b"not a pdf")
        with patch("notifications.brevo_email.requests.post") as post:
            with pytest.raises(ValueError, match="PDF"):
                send_report_email(txt, "Subject", _config())
        post.assert_not_called()

    def test_no_request_on_directory_path(self, tmp_path: Path):
        with patch("notifications.brevo_email.requests.post") as post:
            with pytest.raises(ValueError, match="regular file"):
                send_report_email(tmp_path, "Subject", _config())
        post.assert_not_called()

    def test_no_request_on_invalid_sender_email(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post") as post:
            with pytest.raises(ValueError, match="sender"):
                send_report_email(pdf_file, "Subject",
                                  _config(sender_email="not-an-email"))
        post.assert_not_called()

    def test_no_request_on_invalid_recipient_email(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post") as post:
            with pytest.raises(ValueError, match="recipient"):
                send_report_email(pdf_file, "Subject",
                                  _config(recipient_email="bad@"))
        post.assert_not_called()

    def test_config_requires_api_key(self, monkeypatch, pdf_file: Path):
        # Remove every Brevo var so from_env() must fail. load_dotenv() is
        # neutralized so a present root .env cannot repopulate them.
        for var in ("BREVO_API_KEY", "BREVO_SENDER_EMAIL", "BREVO_SENDER_NAME",
                    "REPORT_RECIPIENT_EMAIL"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("EMAIL_DRY_RUN", "false")
        with patch("notifications.config.load_dotenv"):
            with pytest.raises(ValueError, match="BREVO_API_KEY"):
                send_report_email(pdf_file, "Subject")


# ---------------------------------------------------------------------------
# HTTP response handling
# ---------------------------------------------------------------------------

class TestHttpHandling:
    def test_http_201_accepted(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post",
                   return_value=_ok_response(201, **{"Message-Id": "m1"})) as post:
            result = send_report_email(pdf_file, "Subject", _config())
        assert result["status"] == "sent"
        assert result["brevo_message_id"] == "m1"
        assert post.call_count == 1  # no retry on success

    def test_http_400_validation_error(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post",
                   return_value=_error_response(400, '{"code":"invalid_parameter"}')):
            with pytest.raises(BrevoEmailError, match="validation"):
                send_report_email(pdf_file, "Subject", _config())

    def test_http_401_invalid_key(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post",
                   return_value=_error_response(401, "unauthorized")):
            with pytest.raises(BrevoEmailError, match="API key"):
                send_report_email(pdf_file, "Subject", _config())

    def test_http_403_sender_auth(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post",
                   return_value=_error_response(403, "sender not verified")):
            with pytest.raises(BrevoEmailError, match="verified"):
                send_report_email(pdf_file, "Subject", _config())

    def test_http_429_rate_limit(self, pdf_file: Path):
        # 429 is retryable, but after exhausting attempts it must raise.
        with patch("notifications.brevo_email.requests.post",
                   return_value=_error_response(429, "rate limit"),
                   ) as post:
            with patch("notifications.brevo_email.time.sleep") as sleep:
                with pytest.raises(BrevoEmailError, match="rate limit"):
                    send_report_email(pdf_file, "Subject", _config())
        # MAX_ATTEMPTS total calls: no duplicate happy-path send.
        assert post.call_count == 3
        assert sleep.call_count == 2

    def test_retry_on_5xx_then_success(self, pdf_file: Path):
        responses = [_error_response(503, "unavailable"), _ok_response(201)]
        with patch("notifications.brevo_email.requests.post",
                   side_effect=responses) as post:
            with patch("notifications.brevo_email.time.sleep") as sleep:
                result = send_report_email(pdf_file, "Subject", _config())
        assert result["status"] == "sent"
        assert post.call_count == 2
        assert sleep.call_count == 1

    def test_network_error_retried_then_raises(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post",
                   side_effect=requests.ConnectionError("boom")) as post:
            with patch("notifications.brevo_email.time.sleep"):
                with pytest.raises(BrevoEmailError):
                    send_report_email(pdf_file, "Subject", _config())
        assert post.call_count == 3


# ---------------------------------------------------------------------------
# Dry-run mode (NFR-012) — zero network calls
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_dry_run_no_api_call(self, pdf_file: Path):
        with patch("notifications.brevo_email.requests.post") as post:
            result = send_report_email(pdf_file, "Subject", _config(dry_run=True))
        post.assert_not_called()
        assert result["status"] == "dry-run"
        assert result["dry_run"] is True

    def test_dry_run_displays_info(self, pdf_file: Path):
        result = send_report_email(pdf_file, "Weekly Report",
                                   _config(dry_run=True, recipient_email="r@example.com"))
        assert result["recipient"] == "r@example.com"
        assert result["subject"] == "Weekly Report"
        assert result["attachment"] == pdf_file.name
        assert "No email was sent" in result["message"]

    def test_dry_run_still_validates_pdf(self, tmp_path: Path):
        missing = tmp_path / "missing.pdf"
        with patch("notifications.brevo_email.requests.post") as post:
            with pytest.raises(FileNotFoundError):
                send_report_email(missing, "Subject", _config(dry_run=True))
        post.assert_not_called()
