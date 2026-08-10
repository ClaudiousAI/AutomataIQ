# 05 — AI Architecture

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [04_System_Architecture](./04_System_Architecture.md) · [06_Agent_Architecture](./06_Agent_Architecture.md) · [13_Security_Architecture](./13_Security_Architecture.md) · [14_Testing_Strategy](./14_Testing_Strategy.md)

---

## 1. Principles

1. **Evidence-first and provenance-preserving** — LLM output is treated as inference until linked to evidence.
2. **Deterministic preprocessing before generative reasoning** — parse, normalize, hash/diff, dedup, and entity resolution run as deterministic code before any model call. The LLM never sees unchanged content (cost gate, [FR-C01-6]).
3. **Human-in-the-loop** for high-impact decisions.
4. **Model-agnostic LLM gateway** — no provider-specific code outside the gateway ([NFR-13]).
5. **Versioned prompts, models, and classifiers** — every artifact records its producing version ([NFR-6]).
6. **Facts labeled** confirmed / inferred / speculative; benefits only stated or explicitly inferred ([FR-C03-4], [FR-C02-6]).

## 2. LLM Gateway (model-agnostic)

```
            ┌────────────────────────────────────────────┐
 Agent ───▶ │  LLM Gateway                                 │
            │  · provider adapters (pluggable)            │
            │  · prompt templates (versioned)             │
            │  · model routing (tiered by task)           │
            │  · caching (deterministic hit/miss)         │
            │  · token/budget accounting                  │
            │  · structured-output contracts (JSON Schema)│
            │  · retry / fallback / review routing        │
            └────────────────────────────────────────────┘
```

- **Structured outputs:** agents return typed JSON validated against schemas; invalid output triggers retry or review, never silent acceptance.
- **Tiered models:** cheap deterministic models for classification; capable models for architecture reconstruction; budget-aware routing ([NFR-12]).
- **Caching:** identical prompt+inputs hit cache; semantic-diff content reuses cached extractions where valid.

## 3. AI-Powered Stages

| Stage | AI role | Guardrail |
|---|---|---|
| Change classification | Classify new/enhancement/deprecation/architecture/event/no-meaningful | Output is a closed enum + confidence |
| Automation extraction | Extract business process, products, type, workflow fields | Every field cites evidence; missing ⇒ null |
| Architecture reconstruction | Reconstruct trigger→…→monitoring; identify technologies | confirmed vs inferred labels |
| Opportunity validation | Assess standard/config/extend/missing + path | Classification + evidence; checklist for human |
| Scoring | Produce score vector + rationale per metric | Scores are recommendations, not facts; override allowed |
| Report narrative | Explain "what changed and why it matters" | Draft only — reviewed before publish |
| Semantic search / recommend | Hybrid vector retrieval + related-pattern recs | Ranking shown with reasons |

## 4. Hallucination & Reliability Controls

- **Confirmed vs inferred labels** on every node/edge/fact ([FR-C04-3]).
- **Evidence-linked extraction:** each claim references source + locator; unreferenced claims are dropped or marked speculative.
- **Deterministic preprocessing** shrinks the space the model can hallucinate in.
- **LLM failure handling:** retry → fallback model → route to review ([edge cases in App Flow]).
- **Low-confidence outputs are never auto-promoted**; high-impact items route to the Review Queue ([FR-C09-5]).
- **Conflicting sources** retain claims and reduce confidence ([FR-C02-4]).
- **Golden-set evaluation** gates changes ([14_Testing_Strategy](./14_Testing_Strategy.md) §Evaluation).

## 5. Prompt & Model Versioning

- Every prompt template has an immutable version; agents record `(model, prompt_version, model_version)` per run (`agent_runs` table).
- Taxonomy and scoring calibration evolve via [C10] feedback loops.
- A prompt/model change triggers a regression run against the golden set before promotion.

## 6. Cost & Latency Controls

- Change gating (cheap first, expensive only on change).
- Tiered model routing by task difficulty.
- Caching at prompt-response and extraction level.
- Per-source, per-agent, per-tenant budgets; alerting on breach ([NFR-12]).
- Semantic analysis is async (queue) so cost never blocks ingestion.

## 7. Evaluation & Quality

- Golden datasets per capability (classification, extraction, architecture, scoring).
- Metrics tracked: precision, recall, relevance, duplicate-consolidation, architecture usefulness ([PRD §9]).
- A "precision:genuinely-new" gate is the primary health metric for Discovery.
- Reviewer feedback ([FR-C10-1]) is sampled to grow the golden set.
