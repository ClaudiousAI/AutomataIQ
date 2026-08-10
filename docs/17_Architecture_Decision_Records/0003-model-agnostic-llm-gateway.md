# ADR-0003 — Model-Agnostic LLM Gateway

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [05_AI_Architecture](../05_AI_Architecture.md) · NFR-13

## Context
LLM providers change models, pricing, and APIs frequently. The platform runs many AI stages (classification, extraction, architecture, scoring, narrative) and must not be locked to one provider; it must also control cost and version prompts/models.

## Decision
Introduce a **model-agnostic LLM gateway** as the single path for all model calls:

- Pluggable provider adapters; provider-specific code lives only in the gateway.
- Tiered model routing (cheap deterministic models for classification; capable models for hard reconstruction).
- Versioned prompt templates and model registry; every run records `(model, prompt_version, model_version)`.
- Caching, retry/fallback, and token/cost accounting enforced centrally.

## Consequences
### Positive
- Provider swap is configuration, not code (NFR-13 model lock-in resistance).
- Cost budgets and tiering enforceable in one place (NFR-12).
- Prompt/model changes are auditable and regression-gated (NFR-6).
### Negative / Trade-offs
- Gateway adds a layer; must stay thin to avoid duplicating provider features.
- Cross-provider behavior differences (e.g., structured-output support) must be normalized.
### Neutral
- Follows the master design's "model-agnostic LLM gateway" technical principle.
