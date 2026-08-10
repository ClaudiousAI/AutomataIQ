# ADR-0013 — DAST: OWASP ZAP

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [14_Testing_Strategy](../14_Testing_Strategy.md) · [13_Security_Architecture](../13_Security_Architecture.md)
**Resolves:** OD-8 (DAST tool)

## Context
The security testing strategy (docs/14 §security testing) requires dynamic application security testing (DAST) as part of CI and the Phase 14 hardening pass. The tool choice was open.

## Decision
Adopt **OWASP ZAP** as the DAST tool.

- Baseline + full-scan jobs run in CI against staging after deploy; authenticated scan against a seeded test tenant.
- Results fail the pipeline on high-severity findings (aligned with DoD §2.2: no new high-severity findings).
- Findings wired into the alerting/runbook loop at Phase 14.

## Consequences
### Positive
- Free and open-source; no licensing cost; industry standard.
- CI-integratable (ZAP Docker image + baseline scan) and active community support.
### Negative / Trade-offs
- Requires tuning to reduce false positives on the SPA/auth-heavy frontend.
- DAST coverage is complementary to (not a replacement for) SAST/SCA and the LLM-focused security tests.
### Neutral
- A commercial DAST (Burp / Veracode / Synopsys) can be layered in later if enterprise compliance requires it; ZAP runs remain useful regardless.
