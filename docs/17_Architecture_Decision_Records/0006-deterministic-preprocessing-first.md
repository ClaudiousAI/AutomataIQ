# ADR-0006 — Deterministic Preprocessing Before Generative Reasoning

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [05_AI_Architecture](../05_AI_Architecture.md) · NFR-9 · NFR-12

## Context
Generative reasoning is expensive, non-deterministic, and can hallucinate. Running it on every byte of every source version would be cost-prohibitive and error-prone.

## Decision
- Run **deterministic code first**: acquisition → parse → normalize → hash → diff → relevance → dedup → entity resolution.
- The LLM is invoked **only on changed, relevant content**, and its output is schema-validated and evidence-linked.
- Cheap checks gate expensive analysis (FR-C01-6).

## Consequences
### Positive
- Semantic analysis only on meaningful change → cost control (NFR-12) and latency (NFR-9).
- Smaller hallucination surface; deterministic stages are unit-testable exactly.
- Reliable replay (deterministic stages reproduce byte-for-byte).
### Negative / Trade-offs
- Pipeline has more stages to build; the deterministic layer must stay robust to source-structure changes (parser quarantine edge case).
### Neutral
- Reinforces the "evidence-first" principle: the model reasons about known-normalized input, not raw noise.
