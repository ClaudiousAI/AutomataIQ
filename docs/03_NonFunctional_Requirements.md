# 03 — Non-Functional Requirements

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [02_Functional_Requirements](./02_Functional_Requirements.md) · [12_DevOps_Architecture](./12_DevOps_Architecture.md) · [13_Security_Architecture](./13_Security_Architecture.md) · [14_Testing_Strategy](./14_Testing_Strategy.md)

NFRs are ID-ed for traceability ([16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md)) and enforced by [19_Definition_of_Done](./19_Definition_of_Done.md).

---

## NFR-1 Auditability
> Every report finding is traceable to evidence.

- **Requirement:** Any finding surfaced in a report must resolve to source URL(s), retrieval timestamp(s), content version hash(es), and the extraction/validation path that produced it.
- **Acceptance:** A lineage query from a report item to raw evidence succeeds for ≥ 90% of priority findings (PRD metric), and is always present for anything labeled "confirmed".

## NFR-2 Reliability
> Scheduled Saturday report with retries and alerts.

- **Requirement:** Ingestion and report jobs must be idempotent and replayable. A failed report never publishes an incomplete package; it retries and alerts.
- **Acceptance:** Job retries with backoff; report generation is atomic (complete or not-at-all); DLQ surfaces failed messages; the Saturday report is generated on schedule in ≥ 99% of weeks (target 100%).

## NFR-3 Scalability
> Ingestion and analysis workers scale independently.

- **Requirement:** Crawl/enrich/report worker pools are horizontally scalable and decoupled via the queue/stream layer. Semantic analysis is gated behind cheap change detection to control cost ([FR-C01-6]).
- **Acceptance:** Adding workers increases throughput without code change; no shared-state bottleneck in the worker path.

## NFR-4 Security
> SSO, least privilege, tenant isolation.

- **Requirement:** OIDC/SAML-capable identity provider; RBAC with the seven roles; tenant isolation enforced at every query boundary; secrets encrypted outside application data.
- **Acceptance:** Cross-tenant access is denied at API and data layer; secrets never appear in logs or artifacts. Full detail in [13_Security_Architecture](./13_Security_Architecture.md).

## NFR-5 Observability
> Crawl, agent, cost, latency, and quality metrics.

- **Requirement:** OpenTelemetry metrics/logs/traces for every service; dashboards for source health, agent health, LLM cost, job latency, and eval quality.
- **Acceptance:** Trace from scheduler → worker → LLM → DB visible for a sample job; cost per source/agent/month queryable.

## NFR-6 Maintainability
> Modular services, typed contracts, versioned agents.

- **Requirement:** Services are modular with typed contracts between them (API schemas, event schemas, agent I/O). Prompts, models, and classifiers are versioned. The LLM gateway is model-agnostic.
- **Acceptance:** A model swap requires config change only; contract change requires a version bump; dead code is caught by the quality gate.

## NFR-7 Recoverability
> Replayable ingestion and report jobs.

- **Requirement:** Jobs can be re-run from a prior state without duplicate side effects (idempotency keys, event sourcing of job state where practical).
- **Acceptance:** Replaying a failed crawl run produces identical, non-duplicated results; restarting mid-report resumes or re-runs cleanly.

## NFR-8 Explainability
> Score and confidence rationale available.

- **Requirement:** Every score and confidence carries a human-readable rationale; reviewer overrides are recorded with reason.
- **Acceptance:** Score breakdown + rationale exposed in UI and report; override shows before/after + actor + reason.

## NFR-9 Performance Targets
- Change detection (hash/diff) must be cheap relative to semantic analysis (gating per FR-C01-6).
- Interactive queries (semantic search, graph) return within acceptable SLOs for a single-tenant working set (target: p95 < 3 s for faceted search; graph neighborhood queries p95 < 2 s).
- Saturday report generation for a full six-day window completes within a defined window (target: < 30 min for reference source set).

## NFR-10 Availability
- Target availability 99.5% for the interactive workspace; ingestion pipeline is resilient to partial outages (queues buffer).
- Scheduled report generation has defined SLAs; alerts on missed/failed runs.

## NFR-11 Compliance & Source/Legal Risk
- Respect robots.txt, site terms, licensing, authentication boundaries, and content retention policies.
- Source content retained only under policy; paywalled/authenticated content never bypassed.
- Customer-specific source packs respect pack licensing.

## NFR-12 Cost Control
- Tiered LLM models, caching, deterministic preprocessing, and budgets.
- Monthly cost per source/agent tracked and alertable; semantic analysis only runs on changed content.

## NFR-13 Model Lock-In Resistance
- The LLM gateway is model-agnostic and versioned; no provider-specific calls outside the gateway.
- Prompts are versioned and migrated with the gateway.

## NFR-14 Quality Gates (via Evaluation)
- Golden sets and regression harness gate the pipeline ([14_Testing_Strategy](./14_Testing_Strategy.md)):
  - ≥ 85% precision on genuinely-new findings
  - ≥ 80% relevance of automation-related findings
  - ≥ 90% duplicate consolidation
  - ≥ 80% of reviewed architecture summaries judged useful
- No promotion to production for a capability that fails its gate.
