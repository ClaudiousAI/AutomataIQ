# 15 — Project Roadmap

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [04_System_Architecture](./04_System_Architecture.md) · [01_Product_Requirements](./01_Product_Requirements.md) · [12_DevOps_Architecture](./12_DevOps_Architecture.md) · [19_Definition_of_Done](./19_Definition_of_Done.md)

The 16-phase enterprise implementation plan from the master design. Phases are sequential with explicit done criteria; each phase exits only when its [Definition of Done](./19_Definition_of_Done.md) checks pass.

---

## Phase 1 — Product & Architecture
**Goal:** Approved PRD, taxonomy, security model, and target-state architecture.
**Done criteria:**
- PRD approved (this doc set).
- Taxonomies (functional domain + technology) defined and versioned.
- Security model + RBAC roles approved.
- Target-state architecture signed off.
**Outputs:** `docs/01–19`, taxonomy seed data.

## Phase 2 — Platform Foundation
**Goal:** Repo, CI/CD, environments, identity, observability.
**Done criteria:**
- Monorepo + CI/CD pipelines run green.
- `dev` / `staging` / `prod` environments provisioned (IaC).
- IdP + SSO + RBAC scaffold working.
- OTel observability baseline emitting metrics/logs/traces.
**Outputs:** [12_DevOps_Architecture](./12_DevOps_Architecture.md) implemented.

## Phase 3 — Data Foundation
**Goal:** DB, vector, graph, storage, migrations.
**Done criteria:**
- PostgreSQL schema migrated (Alembic); FTS/trigram indexes enabled.
- Qdrant collection + Neo4j schema + seed; MinIO buckets + retention policies.
- Redis Streams topics + DLQ provisioned.
**Outputs:** [07_Database_Design](./07_Database_Design.md) implemented.

## Phase 4 — Source Intelligence
**Goal:** Reliable, replayable ingestion + source health.
**Done criteria:**
- Source registry CRUD + scheduler.
- Connectors: HTML, RSS/API, structured docs, sitemap.
- Crawl-policy module (robots/rate/auth) enforced.
- Replayable crawl runs; source-health metrics surfaced.
**Outputs:** C01 complete.

## Phase 5 — Change Intelligence
**Goal:** Versioning, diff, classification, deduplication.
**Done criteria:**
- Versioned snapshots + lexical/semantic diff.
- Change classification (closed enum) with golden-set gate ≥ thresholds.
- Canonical merge with ≥ 90% duplicate consolidation.
**Outputs:** C02 complete.

## Phase 6 — Automation Intelligence
**Goal:** Structured Automation Cards + taxonomy mapping.
**Done criteria:**
- Extraction pipeline populates all card fields.
- Automation-type classification + domain/industry mapping validated.
- Benefits stated/inferred separation enforced.
**Outputs:** C03 complete.

## Phase 7 — Architecture Intelligence
**Goal:** Evidence-backed architecture graph + diagrams.
**Done criteria:**
- Node/edge extraction with confirmed/inferred provenance.
- Integration-pattern identification; clickable diagrams render.
- Validation flags generated.
**Outputs:** C04 complete.

## Phase 8 — Opportunity Intelligence
**Goal:** Validated, scored opportunity backlog.
**Done criteria:**
- Gap/build-path classification; clean-core & ECC-to-S/4 flags.
- Scoring engine (7 metrics − complexity penalty) with rationale + override.
- Ranked backlog exposed via API.
**Outputs:** C05 + C06 complete.

## Phase 9 — Knowledge & Search
**Goal:** Entity resolution, graph, semantic/faceted search.
**Done criteria:**
- Neo4j populated with lineage source→…→report.
- Hybrid search (vector + facets) with SLOs met.
- Time-window (30/90/180-day) + cross-domain queries pass.
**Outputs:** C07 complete.

## Phase 10 — Workspace UX
**Goal:** End-to-end dashboard and workspaces.
**Done criteria:**
- All 12 primary screens functional against real API.
- Accessibility + responsive checks pass.
**Outputs:** C09 (UX half) + [09_UI_UX_Design](./09_UI_UX_Design.md) / [11_Frontend_Architecture](./11_Frontend_Architecture.md) implemented.

## Phase 11 — Reports
**Goal:** Six-day aggregation, Saturday PDF/HTML/JSON, alerts.
**Done criteria:**
- Report pipeline produces all formats from stored scores.
- Configurable recipients/filters/weights; incomplete-report never published.
- Schedule + notification + alert working.
**Outputs:** C08 complete.

## Phase 12 — Governance
**Goal:** Review, audit, prompt/model registry.
**Done criteria:**
- Review queue + routing rules live.
- Audit log complete for governed actions.
- Prompt/model registry with versioning + promotion workflow.
**Outputs:** C09 (governance half) + C10 foundations.

## Phase 13 — Evaluation
**Goal:** Golden sets, regression, precision/recall, quality gates.
**Done criteria:**
- Golden datasets + harness in CI.
- Quality gates enforce thresholds ([14_Testing_Strategy](./14_Testing_Strategy.md)).
- Regression on model/prompt changes.
**Outputs:** [14_Testing_Strategy](./14_Testing_Strategy.md) fully operational.

## Phase 14 — Production Hardening
**Goal:** HA, DR, security, cost controls, runbooks.
**Done criteria:**
- HA topology + failover verified; DR drill passed.
- Security scan + threat-model review closed.
- Cost budgets/alerts live; runbooks complete.
**Outputs:** NFRs verified in prod.

## Phase 15 — Continuous Learning
**Goal:** Feedback, calibration, source optimization.
**Done criteria:**
- Reviewer-feedback loop feeding golden sets.
- Scoring calibration reviewed with acceptance-rate trend.
- Source optimization (tier/priority/schedule tuning).
**Outputs:** C10 feedback loops live.

## Phase 16 — Productization
**Goal:** Tenant packs, APIs, external product foundation.
**Done criteria:**
- Customer-specific source packs + private knowledge spaces.
- Public API surface (opportunity/architecture retrieval) versioned.
- Multi-tenant onboarding verified.
**Outputs:** C10 complete; product foundation.

## Cross-Phase Dependencies

```
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14
                                              ↘ 15 → 16
```
Phases 13 (eval) and 12 (governance) may start in parallel once 8–9 land; 15 depends on live review feedback from 12.
