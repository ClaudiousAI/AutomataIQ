# 24 — Brevo Transactional Email Integration

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Finalized — implementation-ready
**Module:** `backend/notifications/` (first implementation module)
**Related docs:** [10_Backend_Architecture](./10_Backend_Architecture.md) §6 · [22_Module_Roadmap](./22_Module_Roadmap.md) M12 · [23_Development_Rules](./23_Development_Rules.md)
**Requirements:** FR-050, FR-051, NFR-002, NFR-005, NFR-007, NFR-012

---

## 1. Overview

The SAIE reporting pipeline ends with "notify configured recipients"
(docs/10 §6.5). This document describes the first concrete transport:
sending the weekly Saturday intelligence report **PDF** as a transactional
email through the [Brevo REST API](https://developers.brevo.com/) via
`POST https://api.brevo.com/v3/smtp/email`.

The transport lives in `backend/notifications/` and exposes a single
function, `send_report_email()`. It is deliberately small, deterministic,
and dependency-light: it is the **first implementation module** in a
project that currently contains no production code, and it is designed to
be wired into the M16 report pipeline later.

## 2. Environment Variables

Read from the project-root `.env` file (via `python-dotenv`) or the real
environment. Real environment variables take precedence over `.env`.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `BREVO_API_KEY` | ✅ | — | Brevo API key (`Settings → API Keys`). Sent as the `api-key` header. |
| `BREVO_SENDER_EMAIL` | ✅ | — | Sender address. Must be **verified** in Brevo or the API returns 403. |
| `BREVO_SENDER_NAME` | ✅ | — | Display name shown as the sender. |
| `REPORT_RECIPIENT_EMAIL` | ✅ | — | Recipient of the Saturday report PDF. |
| `EMAIL_DRY_RUN` | ❌ | `true` | `true` → validate only, send nothing. `false` → send real email. |

> ⚠️ **Safety default:** if `EMAIL_DRY_RUN` is unset, dry-run is assumed.
> No real email is ever sent unless the operator explicitly sets
> `EMAIL_DRY_RUN=false`.

Missing required variables raise `ValueError` **before** any network call,
naming every missing variable so misconfiguration is fixable in one pass.

## 3. Brevo Account Setup

1. Create an account at [brevo.com](https://www.brevo.com/).
2. Under **Settings → Senders & IP → Senders**, add and **verify** the
   address you will use as `BREVO_SENDER_EMAIL`. Unverified senders return
   HTTP 403.
3. Under **Settings → API Keys**, create a key and copy it into
   `BREVO_API_KEY`. (The newer "Master API Key" and older "v3 key" both
   work for this endpoint.)
4. Copy `.env.example` → `.env` at the project root and fill in the values.

> Note: transaction emails require a sender on the Free plan; check current
> plan limits before sending high volumes.

## 4. Sender Verification

Brevo rejects emails from unverified senders with HTTP 403
(`sender not verified`). Verify the sender in the Brevo dashboard and
confirm the value of `BREVO_SENDER_EMAIL` matches **exactly** what you
verified (case and domain).

## 5. Installation

```bash
pip install -r backend/requirements.txt
# or, for the two production deps:
pip install requests python-dotenv
```

Python 3.10+ is required (the code uses `str | Path` unions and
`from __future__ import annotations`).

## 6. Usage

```python
# Run from backend/ so the notifications package is importable:
#   cd backend && python
from notifications.brevo_email import send_report_email

result = send_report_email(
    "/path/to/saie-weekly-report.pdf",
    "SAIE Weekly Report — Week 12 / 2026",
)
print(result)
```

If `EMAIL_DRY_RUN=true` (or unset), `result` describes what *would* be
sent and no email leaves the machine:

```
{'status': 'dry-run', 'dry_run': True, 'recipient': '...',
 'subject': '...', 'attachment': 'saie-weekly-report.pdf', ...}
```

With `EMAIL_DRY_RUN=false`, a successful send returns:

```
{'status': 'sent', 'brevo_message_id': '<...>', 'http_status': 201,
 'dry_run': False}
```

### Command-line

```bash
cd backend
# Dry-run (safe, default):
python -m notifications.brevo_email --pdf path/to/report.pdf \
  --subject "SAIE Report - Week 12 / 2026"

# Live send — only when you explicitly intend to:
python -m notifications.brevo_email --pdf path/to/report.pdf --live
```

## 7. Dry-Run Mode

Dry-run performs the **full validation pipeline** — PDF existence,
extension, non-empty size, email format, config completeness — and logs a
summary of what would be sent, but performs **zero** network calls. It is
the default and is the recommended way to smoke-test the module (NFR-012).

## 8. Testing

```bash
cd backend
python -m pytest notifications/tests/ -v
```

The suite (16 tests) mocks the Brevo endpoint — no real API calls are
made. It covers:

- Correct endpoint, `api-key` header, JSON payload, timeout
- PDF base64-encoding and attachment filename
- Validation gates (missing / empty / wrong-extension / directory / bad
  emails) with **no network call**
- HTTP handling: 201 success, 400/401/403/429 errors, retry-then-success
  on 5xx, retry exhaustion on 429 and network errors
- Dry-run: zero API calls, correct info, still validates the PDF

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ValueError: Missing required Brevo environment variable(s)` | `.env` missing/blank vars | Copy `.env.example` → `.env`, fill all four required vars |
| HTTP 401 | Wrong/revoked API key | Regenerate key in Brevo Settings → API Keys |
| HTTP 403 | Sender not verified | Verify `BREVO_SENDER_EMAIL` in Brevo Senders tab |
| HTTP 400 | Malformed payload (e.g. bad email format) | Check recipient/sender values; see `response_body` on the exception |
| HTTP 429 | Rate limit hit | Automatic retry with backoff handles it; raise the plan limit if persistent |
| Email not sent despite `status: sent` | None — that's dry-run | Set `EMAIL_DRY_RUN=false` |

## 10. Security Notes

- **Never commit the real `.env`.** It is gitignored; `.env.example` is
  the committed template (no secrets).
- The Brevo API key is only sent in the `api-key` header over HTTPS — it
  never appears in the email body or attachment.
- The API key is never logged. Logging records recipient, subject,
  attachment name/size, and Brevo's `Message-Id` — not credentials.
- The module never retries a definitive 4xx rejection, so a misconfigured
  key cannot silently rack up retry traffic.
- Rotate the key immediately if it is ever exposed (e.g. in a pasted log
  or a shared `.env`).
