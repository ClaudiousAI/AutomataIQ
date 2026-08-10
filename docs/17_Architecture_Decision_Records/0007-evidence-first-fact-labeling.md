# ADR-0007 — Evidence-First with Confirmed/Inferred Fact Labeling

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [05_AI_Architecture](../05_AI_Architecture.md) · [09_UI_UX_Design](../09_UI_UX_Design.md) · NFR-1

## Context
The product's trust model forbids presenting AI inference as confirmed SAP facts (PRD out-of-scope: "unreviewed claims presented as confirmed SAP facts"). UI and reports must visually separate evidence-backed fact from model inference.

## Decision
- Every fact, architecture node/edge, and benefit carries a label: **confirmed | inferred | speculative**, plus evidence references.
- Benefits recorded only when stated; inferred benefits flagged explicitly.
- Confidence (high/medium/low) is derived from authority, recency, corroboration, specificity — with rationale.
- Architecture components separate **confirmed** from **inferred**; UI shows both but never conflates them.
- Low-confidence / high-impact items route to human review; never auto-promoted.

## Consequences
### Positive
- Honest separation of fact vs inference (core differentiator for SAP architects).
- Satisfies auditability (NFR-1) and the "≥85% precision after human evaluation" metric.
- Reviewer feedback (C10) can correct mislabeled facts.
### Negative / Trade-offs
- More labeling work in the pipeline; requires discipline so labels stay meaningful.
- Reports must carry the labeling language even at the cost of density.
### Neutral
- Extends the master design's confirmed/inferred/speculative fact model into a platform invariant.
