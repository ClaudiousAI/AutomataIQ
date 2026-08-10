# 14 — Testing Strategy

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [02_Functional_Requirements](./02_Functional_Requirements.md) · [03_NonFunctional_Requirements](./03_NonFunctional_Requirements.md) · [05_AI_Architecture](./05_AI_Architecture.md) · [19_Definition_of_Done](./19_Definition_of_Done.md)

---

## 1. Test Pyramid

```
         ┌──────────────────────────────┐
         │  E2E journeys (Discover/      │
         │  Evaluate/Report)  —  few     │
         ├──────────────────────────────┤
         │  Integration + contract +     │
         │  evaluation/golden sets       │
         ├──────────────────────────────┤
         │  Unit (domain logic) — many   │
         └──────────────────────────────┘
```

| Level | Scope | Examples |
|---|---|---|
| Unit | Pure domain logic | scoring formula, dedup keys, taxonomy validation, confidence aggregation |
| Contract | Service boundaries | API schemas, event schemas, agent envelope validation |
| Integration | Components + stores | crawl → parse → diff; DB/vector/graph repositories; tenant scoping |
| Evaluation | LLM-dependent stages | golden-set precision/recall on classification, extraction, architecture, scoring |
| E2E | Journeys | Discover / Evaluate / Report flows across web + API |
| Security | Adversarial | tenant bypass, RBAC escalation, SSRF, prompt-injection ([13_Security_Architecture](./13_Security_Architecture.md) §9) |

## 2. Golden Sets & Eval Harness

- **Golden datasets** per capability (change classification, automation extraction, architecture reconstruction, opportunity scoring) curated from reviewed real output + synthetic fixtures.
- Harness replays pipeline against golden sets; tracks precision, recall, relevance, duplicate-consolidation, architecture-usefulness ([PRD §9]).
- **Quality gates:** a capability cannot be promoted unless its metrics clear thresholds:
  - ≥ 85% precision genuinely-new findings
  - ≥ 80% relevance automation-related findings
  - ≥ 90% duplicate consolidation
  - ≥ 80% reviewed architecture summaries judged useful
- Regression: a model/prompt/taxonomy change must not regress golden metrics ([NFR-6]).

## 3. LLM-Specific Testing

- **Deterministic-first principle:** test the deterministic stages exactly; test LLM stages through golden-set eval + schema-validated outputs.
- **Structured output contract tests:** invalid/missing fields → retry or review routing (never silent acceptance).
- **Prompt-injection tests:** source content containing instructions must not steer extraction (content is data, not control).
- **Cost/fallback tests:** fallback-model routing on provider failure; caching hit/miss correctness.

## 4. Key Non-Functional Tests

- **Idempotency:** re-running a job produces identical, non-duplicated results ([NFR-7]).
- **Tenant isolation:** cross-tenant access denied at API + data layer ([NFR-4]).
- **Report reliability:** incomplete report never published; retry + alert on failure ([NFR-2]).
- **Performance:** faceted search p95 < 3 s; graph neighborhood p95 < 2 s; Saturday report < 30 min for reference set ([NFR-9]).
- **Cost:** semantic analysis only on changed content; budgets enforced ([NFR-12]).

## 5. Frontend Testing

- Unit: component behavior (DataTable, EvidenceBadge, ScoreBadge, ArchitectureDiagram).
- Component/viz regressions for heat maps and diagrams (theme-aware, accessible).
- E2E: Discover / Evaluate / Report journeys with mocked API ([11_Frontend_Architecture](./11_Frontend_Architecture.md) §7).

## 6. Test Data & Fixtures

- **Synthetic sources** with controlled change sequences (safe, deterministic).
- **Reviewed real fixtures** from staging crawl (retention-compliant).
- Tenant fixtures: 2+ tenants to prove isolation.

## 7. CI Integration

- PR CI: lint, typecheck, unit, contract, security scan.
- Merge/staging: integration + golden-set eval + e2e + non-functional smoke.
- Prod promotion: eval gates must pass; results archived for audit.
- Coverage policy per module documented in DoD ([19_Definition_of_Done](./19_Definition_of_Done.md)).

## 8. Mutation & Robustness Mindset

- Tests are strengthened adversarially (mutation-style review of assertions) for the highest-risk paths: scoring, dedup, tenant scoping, report atomicity.
- Edge cases from the App Flow are explicit test cases (unavailable source, changed page structure, conflicting sources, LLM failure, low confidence, report failure).
