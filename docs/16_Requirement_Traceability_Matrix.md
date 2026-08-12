# 16 — Requirements Traceability Matrix (RTM)

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Living — status updates tracked with every phase exit and PR merge
**Related docs:** [02_Functional_Requirements](./02_Functional_Requirements.md) · [03_NonFunctional_Requirements](./03_NonFunctional_Requirements.md) · [15_Project_Roadmap](./15_Project_Roadmap.md) · [19_Definition_of_Done](./19_Definition_of_Done.md)

> **Rule: Every code change, commit, and PR must reference one or more Requirement IDs from this document.** This prevents scope drift and creates an auditable link between what was built and what was planned. Code without a requirement reference will not pass the Definition of Done ([19](./19_Definition_of_Done.md)).

---

## ID Convention

- **Functional requirements:** `FR-NNN` (zero-padded, sequential)
- **Non-functional requirements:** `NFR-NNN`
- **IDs are stable and never reused** — if a requirement is removed, its ID is retired.
- The detailed rationale for each requirement lives in [doc02](./02_Functional_Requirements.md) / [doc03](./03_NonFunctional_Requirements.md). This matrix tracks *what exists* and *status*.

## Status Legend

| Status | Meaning |
|---|---|
| **Not Started** | Not yet implemented |
| **In Progress** | Work underway |
| **Blocked** | Blocked on dependency, design, or external factor |
| **Done** | Implemented, tested, meets DoD |
| **Deferred** | Intentionally deferred to a later phase |

---

## Functional Requirements

### Discovery Engine
*Sources, crawling, scheduling, compliance, provenance*

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| FR-001 | Source registry (CRUD, tier, active status, schedule, content hash) | Discovery Engine | In Progress | 4 | Integration |
| FR-002 | Source-specific acquisition (HTML, RSS/API, doc, sitemap) | Discovery Engine | Not Started | 4 | Integration |
| FR-003 | Continuous ingestion with Saturday six-day reporting boundary | Discovery Engine | Not Started | 4, 11 | Integration |
| FR-004 | Source tiering by authority (Tier 1–6) | Discovery Engine | Not Started | 4 | Unit |
| FR-005 | Provenance capture (URL, retrieved_at, version hash) on every finding | Discovery Engine | Not Started | 4 | Contract |
| FR-006 | Change gating — skip unchanged content (content hash) before expensive analysis | Change Detection | Not Started | 5 | Integration |
| FR-007 | Crawler policy compliance (robots.txt, terms, rate limits, auth boundaries) | Discovery Engine | Not Started | 4 | Security |

### Change Detection
*Hash, diff, classification, deduplication*

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| FR-008 | Versioned snapshots (policy-compliant storage + normalized snapshot) | Evidence Engine | In Progress | 5 | Integration |
| FR-009 | Lexical and semantic diff generation between versions | Change Detection | Not Started | 5 | Integration |
| FR-010 | Change classification (new capability, enhancement, clarification, deprecation, architecture, event, no meaningful change) | Change Detection | Not Started | 5 | Eval |
| FR-011 | Evidence confidence scoring (authority, recency, corroboration, specificity) | Evidence Engine | Not Started | 5 | Unit |
| FR-012 | Canonical finding merge — dedup ≥ 90% for multi-source coverage | Evidence Engine | Not Started | 5 | Eval |
| FR-013 | Fact labeling (confirmed / inferred / speculative) on every promoted fact | Evidence Engine | Not Started | 5 | Contract |
| FR-014 | Evidence trail for every priority finding (source version + locator) | Evidence Engine | Not Started | 5 | Contract |

### Automation Intelligence
*Pattern extraction, classification, taxonomy, cards*

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| FR-015 | Automation pattern extraction (process, area, products, trigger, inputs, decisions, workflow, human involvement, outcome) | Automation Intelligence | Not Started | 6 | Eval |
| FR-016 | Automation-type classification (workflow, RPA, document, API, event-driven, AI-assisted, agentic, predictive, custom) | Automation Intelligence | Not Started | 6 | Eval |
| FR-017 | Business problem and pre-automation process capture | Automation Intelligence | Not Started | 6 | Contract |
| FR-018 | Benefits recorded only when stated; inferred benefits flagged explicitly | Automation Intelligence | Not Started | 6 | Contract |
| FR-019 | Taxonomy mapping across FI/CO, SD, MM, PP, QM, PM, EWM, TM, PS, PLM, MDG, GRC, Treasury, CRM, HCM, procurement, industries | Automation Intelligence | In Progress | 6 | Unit |
| FR-020 | Canonical automation IDs assigned with temporal lineage | Automation Intelligence | Not Started | 6 | Contract |

### Architecture Reconstruction
*Flow extraction, technology ID, diagrams, provenance*

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| FR-021 | Architectural flow extraction (trigger → data → processing → AI/rules → decision → workflow → API/event → target → monitoring) | Architecture Reconstruction | Not Started | 7 | Eval |
| FR-022 | Technology identification (S/4HANA, BTP, Integration Suite, APIs, Event Mesh, Build, Process Automation, AI, Data Cloud, Datasphere, HANA, Cloud ALM) | Architecture Reconstruction | Not Started | 7 | Eval |
| FR-023 | Confirmed vs inferred component separation | Architecture Reconstruction | Not Started | 7 | Contract |
| FR-024 | Logical architecture diagram and text summary generation | Architecture Reconstruction | Not Started | 7 | E2E |
| FR-025 | Integration-pattern identification (sync API, async event, batch, workflow, document, agent) | Architecture Reconstruction | Not Started | 7 | Unit |
| FR-026 | Human-in-the-loop capture (controls, approvals, exception paths) | Architecture Reconstruction | Not Started | 7 | Contract |
| FR-027 | Validation flags (security, audit, resilience, observability, data-governance) | Architecture Reconstruction | Not Started | 7 | Unit |

### Opportunity Engine
*Validation, gap classification, migration, build path, checklist*

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| FR-028 | Gap classification (standard, configurable, extensible, partner-provided, genuinely missing) | Opportunity Engine | Not Started | 8 | Eval |
| FR-029 | Customer process pain and manual effort mapping | Opportunity Engine | Not Started | 8 | Contract |
| FR-030 | ECC-to-S/4 and clean-core implications identified | Opportunity Engine | Not Started | 8 | Eval |
| FR-031 | Build-path classification (standard SAP, config, extension, BTP automation, custom app, AI agent, external integration) | Opportunity Engine | Not Started | 8 | Unit |
| FR-032 | Reuse assessment across customers and industries; dependency tracking (release, edition, licensing, services) | Opportunity Engine | Not Started | 8 | Integration |
| FR-033 | Human validation checklist per opportunity | Opportunity Engine | Not Started | 8 | Contract |

### Scoring Engine
*Weighted scoring, rationale, override, ranking*

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| FR-034 | Weighted scoring (Business Value 20%, Automation Potential 15%, Technical Feasibility 15%, Reusability 15%, Demand 10%, Differentiation 10%, Clean-Core 10%) minus complexity penalty (up to −15%) | Scoring Engine | Not Started | 8 | Unit |
| FR-035 | Score vector + rationale per metric stored and exposed | Scoring Engine | Not Started | 8 | Contract |
| FR-036 | Reviewer override with previous/new value + actor + reason; audit trail | Scoring Engine | Not Started | 8 | Contract |
| FR-037 | Deterministic ranking for Saturday report and backlog (stable tie-break) | Scoring Engine | Not Started | 8 | Unit |

### Knowledge Graph & Search
*Graph linking, queries, lineage, semantic search, recommendations*

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| FR-038 | Knowledge graph linking (sources, findings, automations, products, processes, industries, technologies, APIs, events, architectures, opportunities) | Knowledge Graph | In Progress | 9 | Integration |
| FR-039 | Temporal queries (what changed in last 30 / 90 / 180 days) | Knowledge Graph | Not Started | 9 | Integration |
| FR-040 | Cross-domain queries (e.g. AI automation affecting MM + manufacturing) | Knowledge Graph | Not Started | 9 | Integration |
| FR-041 | Evidence and confidence at fact/relationship level | Knowledge Graph | Not Started | 9 | Contract |
| FR-042 | End-to-end lineage queryable (source → extraction → validation → score → report) | Knowledge Graph | Not Started | 9 | E2E |
| FR-043 | Semantic search + structured filters (hybrid vector + facets) | Search | In Progress | 9 | Integration |
| FR-044 | Related-pattern and reusable-architecture recommendations | Knowledge Graph | Not Started | 9 | Integration |

### Reporting
*Saturday report composition, automation cards, exports, narrative*

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| FR-045 | Report composition (executive summary, meaningful changes, automation findings, top opportunities) | Reporting | Not Started | 11 | E2E |
| FR-046 | Detailed Automation Cards with architecture and evidence | Reporting | Not Started | 11 | E2E |
| FR-047 | "Why it matters" narrative per headline finding | Reporting | Not Started | 11 | Eval |
| FR-048 | Domain, industry, and technology heat maps | Reporting | Not Started | 11 | E2E |
| FR-049 | ECC-to-S/4 and clean-core opportunity flags in executive section | Reporting | Not Started | 11 | Contract |
| FR-050 | PDF, HTML, JSON, CSV export generation | Reporting | Not Started | 11 | Integration |
| FR-051 | Configurable recipients, filters, scoring weights, and schedule per tenant | Reporting | Not Started | 11 | Contract |

### Workspace (UI)
*Workspaces, navigation, accessibility*

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| FR-052 | Workspaces: Dashboard, Discovery, Automation, Architecture, Opportunity, Evidence, Reports, Governance, Administration | Workspace (UI) | Not Started | 10 | E2E |

### Governance & Ops
*RBAC, audit, health monitoring, review routing, alerts*

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| FR-053 | RBAC: platform_admin, tenant_admin, architect, analyst, reviewer, executive, read_only | Governance & Ops | Done | 2, 10 | Security |
| FR-054 | Audit logs + prompt/model versioning + evidence traceability | Governance & Ops | In Progress | 12 | Security |
| FR-055 | Source health, agent health, retries, DLQ, cost budgets monitoring | Governance & Ops | Not Started | 12 | Ops |
| FR-056 | Human review routing (low-confidence + high-impact → Review Queue) | Governance & Ops | Not Started | 12 | Integration |
| FR-057 | Tenant isolation at every query boundary + least privilege enforcement | Governance & Ops | Done | 2, 3, 12 | Security |
| FR-058 | Alerts and operational runbooks | Governance & Ops | Not Started | 12, 14 | Ops |

### Continuous Learning
*Feedback, benchmarks, taxonomy, customer packs, APIs*

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| FR-059 | Reviewer feedback capture (relevance, correctness, architecture, scoring) | Continuous Learning | Not Started | 15 | Integration |
| FR-060 | Quality metrics and benchmark (golden) datasets | Continuous Learning | Not Started | 13 | Eval |
| FR-061 | Taxonomy evolution with versioning and workflow | Continuous Learning | Not Started | 15 | Contract |
| FR-062 | Customer-specific source packs and private knowledge spaces | Continuous Learning | Not Started | 16 | Security |
| FR-063 | Future APIs for automation-opportunity and architecture retrieval | Continuous Learning | Not Started | 16 | Contract |
| FR-064 | Recommendation layer (what to build, what to replace, reusable accelerator) | Continuous Learning | Not Started | 16 | Eval |

**Functional requirement count: 64**

---

## Non-Functional Requirements

| Requirement ID | Description | Module | Status | Phase | Verify |
|---|---|---|---|---|---|
| NFR-001 | **Auditability** — every report finding traceable to evidence | Governance & Ops | Not Started | 9, 11 | E2E |
| NFR-002 | **Reliability** — Saturday report retries/alerts; never publish incomplete | Reporting | Not Started | 11 | E2E |
| NFR-003 | **Scalability** — ingestion and analysis workers scale independently | Platform | Not Started | 14 | Ops |
| NFR-004 | **Security** — SSO, RBAC, tenant isolation, encrypted secrets | Platform | Done | 2, 13 | Security |
| NFR-005 | **Observability** — OTel metrics/logs/traces; cost and quality dashboards | Platform | In Progress | 2 | Ops |
| NFR-006 | **Maintainability** — typed contracts, versioned prompts/models/classifiers | Platform | In Progress | 6, 12 | Contract |
| NFR-007 | **Recoverability** — idempotent, replayable jobs | Platform | Done | 4, 5 | Unit |
| NFR-008 | **Explainability** — score and confidence rationale always available | Scoring Engine | Not Started | 8 | Contract |
| NFR-009 | **Performance** — search p95 < 3s; graph p95 < 2s; Saturday report < 30min | Platform | Not Started | 9, 11, 14 | Performance |
| NFR-010 | **Availability** — 99.5% workspace target; ingestion resilient via queues | Platform | Not Started | 14 | Ops |
| NFR-011 | **Compliance** — robots.txt, site terms, licensing, content retention | Discovery Engine | Not Started | 4, 14 | Security |
| NFR-012 | **Cost control** — tiered models, caching, deterministic gating, budgets | Platform | Not Started | 5, 12 | Ops |
| NFR-013 | **Model lock-in resistance** — LLM gateway is model-agnostic, versioned | Platform | Not Started | 5, 12 | Contract |
| NFR-014 | **Quality gates** — golden-set eval gates enforce PRD metric thresholds | Continuous Learning | Not Started | 13 | Eval |

**Non-functional requirement count: 14**

---

## Summary

| Type | Total | Not Started | In Progress | Done |
|---|---|---|---|---|
| FR | 64 | 55 | 7 | 2 |
| NFR | 14 | 10 | 2 | 2 |
| **Total** | **78** | **65** | **9** | **4** |

---

## Code Reference Policy

1. **Every change request (PR/merge request) title must include** one or more requirement IDs, e.g. `FR-010, FR-013`.
2. **Every commit message in a feature branch** must include at least one requirement ID.
3. **Every test file** must reference the requirement(s) it verifies.
4. **No requirement ID is skipped** — if a change introduces new behavior without a requirement, add the requirement here first (Phase / Status = *Not Started*) before coding.
5. **Status is updated** by the PR author when the PR meets DoD and merges: `Not Started → In Progress → Done`.
6. **Stale IDs are not reused** — if a requirement is retired, mark it `Deferred` with an explanation in the PR.
