# 02 — Functional Requirements

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [01_Product_Requirements](./01_Product_Requirements.md) · [07_Database_Design](./07_Database_Design.md) · [08_API_Design](./08_API_Design.md) · [16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md)

Each requirement is keyed to a capability (C01–C10) and carries acceptance criteria used by the [Test Strategy](./14_Testing_Strategy.md) and the [Definition of Done](./19_Definition_of_Done.md).

---

## C01 — Discovery & Source Intelligence

**FR-C01-1 — Source Registry**
Maintain a source registry with: source ID, URL, type, domain, industry, priority, schedule, last crawl, content hash, active status.
- *AC:* create/update/deactivate a source; registry returns all fields; inactive sources are skipped by the scheduler.

**FR-C01-2 — Source Acquisition**
Support source-specific acquisition: HTML, RSS/API, structured documentation, and sitemap discovery where available.
- *AC:* each source type uses its declared acquisition strategy; unsupported types quarantine with a clear error.

**FR-C01-3 — Continuous Ingestion with Saturday Boundary**
Run continuous ingestion; the reporting boundary is Saturday. A "week" is the six-day window since the previous Saturday.
- *AC:* crawls scheduled per-source; the Saturday aggregation job closes the window and emits a report.

**FR-C01-4 — Source Tiering**
Tier sources by authority: SAP documentation → SAP announcements → SAP Community → partner/customer evidence → general discovery.
- *AC:* tier is stored per source and influences evidence confidence ([FR-C02-4]).

**FR-C01-5 — Provenance Capture**
Preserve URL, retrieval timestamp, and content version for every finding.
- *AC:* every finding/evidence row references (source_id, retrieved_at, version hash).

**FR-C01-6 — Change Gating**
Detect source-level changes before expensive semantic analysis.
- *AC:* unchanged content (same hash) skips extraction; only changed versions trigger the pipeline.

**FR-C01-7 — Compliance**
Respect robots.txt, terms, rate limits, and authentication boundaries.
- *AC:* crawler policy module blocks/queues non-compliant requests; no authenticated/paywalled content is bypassed.

## C02 — Change Detection & Evidence Intelligence

**FR-C02-1 — Versioned Snapshots**
Store policy-compliant source versions or normalized snapshots.
- *AC:* snapshot bytes + hash persisted; retention policy honored.

**FR-C02-2 — Lexical & Semantic Diff**
Generate lexical and semantic diffs between versions.
- *AC:* lexical diff for structural changes; semantic diff for meaning-preserving rewording.

**FR-C02-3 — Change Classification**
Classify changes as: new capability, enhancement, documentation clarification, deprecation, architecture change, event announcement, or no meaningful change.
- *AC:* classifier returns one of the seven classes plus confidence.

**FR-C02-4 — Evidence Confidence**
Assign evidence confidence from authority, recency, corroboration, and specificity.
- *AC:* confidence ∈ {high, medium, low} with decomposable rationale.

**FR-C02-5 — Canonical Finding Merge**
Merge multiple sources into one canonical finding (dedup ≥ 90%).
- *AC:* duplicate candidates consolidate under a canonical_key with preserved evidence trail.

**FR-C02-6 — Fact Labeling**
Label facts as **confirmed**, **inferred**, or **speculative**.
- *AC:* label stored per fact; UI badges reflect it ([09_UI_UX_Design](./09_UI_UX_Design.md)).

**FR-C02-7 — Evidence Trail**
Maintain an evidence trail for every priority finding.
- *AC:* each priority finding links to all source versions that substantiate it.

## C03 — Automation Pattern Intelligence

**FR-C03-1 — Pattern Extraction**
Extract: business process, business area, industry, SAP products, capability, trigger, inputs, decisions, workflow, human involvement, outcome.
- *AC:* Automation Card exposes every field; missing fields are null, never fabricated.

**FR-C03-2 — Automation-Type Classification**
Classify as: workflow, RPA, document processing, API integration, event-driven, AI-assisted, agentic, predictive, or custom automation.
- *AC:* type set is closed; classifier returns one primary type + optional secondary.

**FR-C03-3 — Problem & Pre-Automation Capture**
Capture the business problem and the pre-automation process.
- *AC:* both fields present on the Automation Card where stated in source.

**FR-C03-4 — Benefits Honesty**
Record benefits **only when stated**; mark inferred benefits explicitly.
- *AC:* inferred benefits carry a distinct badge; stated benefits cite the source.

**FR-C03-5 — Taxonomy Mapping**
Map findings across FI/CO, SD, MM, PP, QM, PM/EAM, EWM, TM, PS, PLM, MDG, GRC, Treasury, CRM, HCM, procurement, and industries.
- *AC:* each finding tagged with domain(s), industry(ies), products — validated against the taxonomy.

**FR-C03-6 — Canonical IDs & Lineage**
Assign canonical Automation IDs and temporal lineage.
- *AC:* automation_id stable across merges; history queryable.

## C04 — Architecture Reconstruction

**FR-C04-1 — Architectural Flow Extraction**
Extract: trigger → data source → processing → AI/rules → decision → workflow → API/event → target → monitoring.
- *AC:* nodes + directed edges persisted; cycle/validation rules applied.

**FR-C04-2 — Technology Identification**
Identify evidenced SAP technologies: S/4HANA, BTP, Integration Suite, APIs, Event Mesh, Build, Process Automation, AI, Data Cloud, Datasphere, HANA, Cloud ALM, related services.
- *AC:* technology entities link to architecture nodes only when evidenced.

**FR-C04-3 — Confirmed vs Inferred Separation**
Separate confirmed components from inferred components.
- *AC:* each node/edge carries a provenance label; UI colors confirmed/inferred distinctly but not by color alone.

**FR-C04-4 — Diagram & Summary Generation**
Generate logical architecture diagrams and text summaries.
- *AC:* diagram (clickable) + text summary exported for an automation.

**FR-C04-5 — Integration-Pattern Identification**
Identify synchronous API, asynchronous event, batch, workflow, document, and agent invocation patterns.
- *AC:* pattern type recorded per edge with evidence.

**FR-C04-6 — Human-in-the-Loop Capture**
Capture human-in-loop controls, approvals, and exception paths.
- *AC:* HL control nodes rendered distinctly.

**FR-C04-7 — Validation Flags**
Flag security, audit, resilience, observability, and data-governance considerations for validation.
- *AC:* each flag routes to the validation checklist ([FR-C05-5]).

## C05 — Opportunity Validation

**FR-C05-1 — Gap Classification**
Determine whether discovery is standard, configurable, extensible, partner-provided, or genuinely missing.
- *AC:* classification output with supporting evidence.

**FR-C05-2 — Pain & Effort Mapping**
Map capability to customer process pain and manual effort.
- *AC:* pain/effort fields populated or marked "not stated".

**FR-C05-3 — Migration Implications**
Identify ECC-to-S/4 and clean-core implications.
- *AC:* implications list generated; clean-core relevance score updated.

**FR-C05-4 — Build-Path Classification**
Classify path: standard SAP, configuration, extension, BTP automation, custom app, AI agent, or external integration.
- *AC:* path matches the Opportunity Classes set in the PRD.

**FR-C05-5 — Reuse & Dependency Assessment**
Assess reuse across customers/industries; track dependencies on release, edition, licensing, and services.
- *AC:* reuse score + dependency list stored per opportunity.

**FR-C05-6 — Human Validation Checklist**
Create a human validation checklist for each opportunity.
- *AC:* checklist persisted and available in the Review Queue workspace.

## C06 — Scoring & Prioritization

**FR-C06-1 — Weighted Scoring**
Score Business Value (20%), Automation Potential (15%), Technical Feasibility (15%), Reusability (15%), Demand (10%), Differentiation (10%), Clean-Core relevance (10%) — minus complexity penalty (up to −15%).
- *AC:* weighted composite computed from the score vector.

**FR-C06-2 — Transparency**
Store the numerical score **plus** rationale per metric.
- *AC:* score vector + rationale persisted; UI shows breakdown.

**FR-C06-3 — Reviewer Override**
Allow reviewer override with an explanation.
- *AC:* override stores previous and new value + actor + reason; audit trail updated.

**FR-C06-4 — Ranking**
Rank opportunities for the Saturday report and backlog.
- *AC:* ranking deterministic (stable tie-break) and reproducible from stored scores.

## C07 — Knowledge Graph & Intelligence Repository

**FR-C07-1 — Graph Linking**
Link sources, findings, automation patterns, products, processes, industries, technologies, APIs, events, architectures, opportunities.
- *AC:* entities + relationships in graph store; CRUD via service layer.

**FR-C07-2 — Temporal Queries**
Support "what changed in the last 30/90/180 days".
- *AC:* time-window filters over change/first-detected timestamps.

**FR-C07-3 — Cross-Domain Queries**
Support queries such as "AI automation affecting MM and manufacturing".
- *AC:* multi-hop relationship queries return connected findings.

**FR-C07-4 — Evidence & Confidence at Fact Level**
Store evidence and confidence at fact/relationship level where practical.
- *AC:* property-based provenance on edges/entities.

**FR-C07-5 — Lineage**
Maintain lineage: source → extraction → validation → score → report.
- *AC:* lineage path traversable end-to-end.

**FR-C07-6 — Semantic Search & Filters**
Provide semantic search plus structured filters.
- *AC:* hybrid retrieval (vector + facets) returns ranked results.

**FR-C07-7 — Recommendations**
Enable related-pattern and reusable-architecture recommendations.
- *AC:* recommendation endpoint returns related items with rationale.

## C08 — Reporting & Saturday Intelligence

**FR-C08-1 — Report Composition**
Generate: executive summary, meaningful changes, automation findings, top opportunities.
- *AC:* all sections present in the six-day report.

**FR-C08-2 — Automation Cards**
Provide detailed Automation Cards with architecture and evidence.
- *AC:* card fields per [Saturday Report Specification](#saturday-report-specification).

**FR-C08-3 — Narrative**
Explain what changed and why it matters.
- *AC:* each headline finding carries a why-it-matters paragraph.

**FR-C08-4 — Heat Maps**
Include domain, industry, and technology heat maps.
- *AC:* heat-map datasets rendered in report and UI.

**FR-C08-5 — Clean-Core Flags**
Include ECC-to-S/4 and clean-core opportunity flags.
- *AC:* flagged items enumerated in the exec section.

**FR-C08-6 — Exports**
Generate PDF, HTML, and JSON/CSV exports.
- *AC:* all four export formats produce valid files.

**FR-C08-7 — Configurability**
Allow configurable recipients, filters, scoring weights, and schedule.
- *AC:* per-tenant report config applied at generation time.

### Saturday Report Specification

**Title:** SAP Automation Intelligence — Week ## / YYYY

**Executive section:** sources scanned & health · meaningful changes · unique automation patterns · top opportunities · industry & technology signals · clean-core / ECC-to-S/4 opportunities · items requiring architect review.

**Detailed Automation Card:** Finding ID · Title · First detected · Last updated · Domain · Industry · SAP products · Automation type · Problem · Current process · New capability · Approach · Technology · Architecture · Human involvement · Benefits · Evidence · Confidence · Opportunity score · Recommended action.

**Appendices:** all findings · rejected/duplicate findings · source changes · evidence index · scoring methodology · agent/model versions · system health summary.

## C09 — UX, Governance & Operations

**FR-C09-1 — Workspaces**
Provide Dashboard, Discovery, Automation, Architecture, Opportunity, Evidence, Reports, Administration workspaces.
- *AC:* every workspace reachable from left nav; RBAC-scoped.

**FR-C09-2 — RBAC**
Implement roles: platform_admin, tenant_admin, architect, analyst, reviewer, executive, read_only.
- *AC:* role-based route & API guards enforced.

**FR-C09-3 — Audit**
Audit logs for administrative and review actions; prompt/model versioning; evidence traceability.
- *AC:* audit entry for every governed action; version snapshots stored.

**FR-C09-4 — Health & Operations**
Monitor source health, agent health, retries, dead-letter queues, cost budgets.
- *AC:* health dashboards + alerts; DLQ observable.

**FR-C09-5 — Human Review Routing**
Route low-confidence and high-impact items to human review.
- *AC:* Review Queue populated per routing rules; decisions recorded.

**FR-C09-6 — Isolation & Least Privilege**
Enforce tenant isolation and least privilege.
- *AC:* cross-tenant access attempt denied; minimal-scope tokens.

**FR-C09-7 — Alerts & Runbooks**
Provide alerts and operational runbooks.
- *AC:* runbook links attached to alert types.

## C10 — Continuous Improvement & Productization

**FR-C10-1 — Reviewer Feedback**
Capture reviewer feedback on relevance, correctness, architecture, scoring.
- *AC:* feedback persisted, linked to entity + reviewer.

**FR-C10-2 — Quality Metrics & Benchmarks**
Maintain quality metrics and benchmark (golden) datasets.
- *AC:* eval harness runs against golden sets; metrics trended.

**FR-C10-3 — Taxonomy Evolution**
Continuously evolve taxonomies and scoring calibration.
- *AC:* taxonomy change workflow with versioning.

**FR-C10-4 — Customer Packs**
Support customer-specific source packs and private knowledge spaces.
- *AC:* pack CRUD + isolation.

**FR-C10-5 — Future APIs**
Expose future APIs for automation-opportunity and architecture retrieval.
- *AC:* API surface versioned and documented.

**FR-C10-6 — Recommendation Layer**
Future recommendation layer: what to build, what to replace, which reusable accelerator to create.
- *AC:* (planned) recommendation output contract defined.
