"""Environment-variable configuration for the Brevo email transport.

All secrets and sender/recipient settings are read from the process
environment, which python-dotenv populates from the project-root ``.env``
file (real environment variables take precedence over ``.env`` values).

Traceability: FR-051 (configurable recipients), NFR-012 (cost control via
dry-run default).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

#: Env var names — kept in one place so docs/24 and tests stay in sync.
API_KEY_VAR = "BREVO_API_KEY"
SENDER_EMAIL_VAR = "BREVO_SENDER_EMAIL"
SENDER_NAME_VAR = "BREVO_SENDER_NAME"
RECIPIENT_EMAIL_VAR = "REPORT_RECIPIENT_EMAIL"
DRY_RUN_VAR = "EMAIL_DRY_RUN"

#: Truthy values accepted for the EMAIL_DRY_RUN boolean flag.
_TRUTHY = {"true", "1", "yes", "y", "on"}


@dataclass(frozen=True)
class BrevoConfig:
    """Resolved Brevo configuration.

    Immutable once loaded so a partially-mutated config can never be sent
    with a dry-run flag that no longer matches reality.
    """

    api_key: str
    sender_email: str
    sender_name: str
    recipient_email: str
    dry_run: bool

    @classmethod
    def from_env(cls) -> BrevoConfig:
        """Load configuration from the environment / ``.env`` file.

        Raises:
            ValueError: If any required variable is missing or blank.
                The message names every missing variable so misconfig
                is fixable in one pass.
        """
        # find_dotenv walks up from this module's location, so the
        # project-root .env is found regardless of the process CWD.
        load_dotenv()

        required = {
            API_KEY_VAR: os.getenv(API_KEY_VAR),
            SENDER_EMAIL_VAR: os.getenv(SENDER_EMAIL_VAR),
            SENDER_NAME_VAR: os.getenv(SENDER_NAME_VAR),
            RECIPIENT_EMAIL_VAR: os.getenv(RECIPIENT_EMAIL_VAR),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                f"Missing required Brevo environment variable(s): {joined}. "
                f"Copy .env.example to .env and fill in the values."
            )

        # Dry-run is the SAFE default: no real email is sent unless the
        # operator explicitly sets EMAIL_DRY_RUN=false (NFR-012).
        dry_run_raw = os.getenv(DRY_RUN_VAR, "true").strip().lower()
        return cls(
            api_key=required[API_KEY_VAR].strip(),
            sender_email=required[SENDER_EMAIL_VAR].strip(),
            sender_name=required[SENDER_NAME_VAR].strip(),
            recipient_email=required[RECIPIENT_EMAIL_VAR].strip(),
            dry_run=dry_run_raw in _TRUTHY,
        )
