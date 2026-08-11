"""Notification delivery for SAIE reports (FR-050, FR-051).

Currently provides Brevo transactional email transport for the Saturday
intelligence report PDF. The notification layer is abstracted here so
additional transports (SMS, webhook, etc.) can be added later.
"""

from .brevo_email import send_report_email

__all__ = ["send_report_email"]
