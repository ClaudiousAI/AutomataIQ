"""SAIE FastAPI application package.

M01 — Project Foundation. Holds the app factory, OTel bootstrap, settings
loader, and the ``/health`` endpoint. Business logic is intentionally
absent: real services land in M02+.

Traceability: NFR-005 (observability bootstrap), NFR-006 (typed config
contract at every service boundary).
"""
