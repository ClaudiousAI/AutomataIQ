# 07 — Database Design

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [04_System_Architecture](./04_System_Architecture.md) · [13_Security_Architecture](./13_Security_Architecture.md) · [08_API_Design](./08_API_Design.md)

---

## 1. Stores

| Store | Technology | Role |
|---|---|---|
| Transactional metadata | PostgreSQL | Primary relational store |
| Vector | Qdrant (self-hosted) | Semantic retrieval over findings/evidence |
| Graph | Neo4j (or graph model) | Relationships between entities |
| Search | PostgreSQL FTS (in Postgres) | Search + facets |
| Blobs | MinIO (S3-compatible) | Snapshots, report files, diagrams |

## 2. Entity-Relationship Overview

```
tenants 1─N users 1─N sources 1─N crawl_runs 1─N source_versions 1─N changes 1─N findings
tenants 1─N reports 1─N report_items N─1 findings
findings 1─N automations 1─N architecture_nodes 1─N architecture_edges
findings 1─N evidence
automations 1─N opportunities 1─N scores
sources N─1 findings (via evidence)
users 1─N reviews · users 1─N audit_log
agent_runs N─1 (entities)
```

## 3. Tables & Columns

### tenants
`id` PK · `name` · `settings` (JSONB) · `created_at` · `updated_at`
→ relationships: users, sources, findings, reports

### users
`id` PK · `tenant_id` FK → tenants · `email` · `role` (7 roles) · `external_sub` (IdP subject) · `created_at` · `updated_at`
→ reviews, audit_log

### sources
`id` PK · `tenant_id` FK · `url` · `type` (html|rss|api|doc|sitemap) · `domain` · `industry` · `priority` · `schedule` (cron) · `tier` (1–6 authority) · `last_crawl_at` · `content_hash` · `active` · `crawl_policy` (JSONB: robots/rate/auth)
→ crawl_runs, source_versions
Indexes: `(tenant_id, active)`, `(url)`

### crawl_runs
`id` PK · `source_id` FK → sources · `status` (queued|running|succeeded|failed|quarantined) · `started_at` · `finished_at` · `metrics` (JSONB: bytes, items, latency, retries)
→ source_versions

### source_versions
`id` PK · `source_id` FK · `crawl_run_id` FK · `content_hash` · `retrieved_at` · `size_bytes` · `blob_uri` (MinIO/S3-compatible URI) · `normalized_snapshot` (JSONB)
→ changes
Indexes: `(source_id, retrieved_at)`, `(content_hash)`

### changes
`id` PK · `version_id` FK → source_versions · `change_type` (new_capability|enhancement|documentation_clarification|deprecation|architecture_change|event_announcement|no_meaningful_change) · `lexical_diff_uri` · `semantic_summary` · `confidence` · `created_at`
→ findings
Indexes: `(change_type, created_at)`, `(version_id)`

### findings
`id` PK · `tenant_id` FK · `canonical_key` (dedup) · `title` · `status` (new|reviewed|merged|rejected) · `first_detected_at` · `last_updated_at` · `confidence` · `fact_label` (confirmed|inferred|speculative)
→ changes, automations
Indexes: `(canonical_key)`, `(status, confidence)`, `(last_updated_at)`; FTS on `title` + body (embeddings in Qdrant)

### automations
`id` PK · `finding_id` FK · `automation_id` (canonical, stable) · `domain` (FI/CO, SD, MM, PP, QM, PM/EAM, EWM, TM, PS, PLM, MDG, GRC, Treasury, CRM, HCM, procurement…) · `industry` · `product` (S/4HANA, BTP…) · `automation_type` (workflow|rpa|document|api|event_driven|ai_assisted|agentic|predictive|custom) · `business_process` · `business_area` · `trigger` · `inputs` (JSONB) · `decisions` (JSONB) · `workflow` (JSONB) · `human_involvement` · `outcome` · `business_problem` · `pre_automation_process` · `benefits` (JSONB: stated[] / inferred[]) · `created_at`
→ architecture_nodes, opportunities

### architecture_nodes
`id` PK · `automation_id` FK · `node_type` (trigger|data_source|processing|ai_rules|decision|workflow|api_event|target|monitoring|human_control) · `name` · `provenance` (confirmed|inferred) · `tech_refs` (JSONB → technologies) · `meta` (JSONB)
→ architecture_edges

### architecture_edges
`id` PK · `automation_id` FK · `from_node` FK → architecture_nodes · `to_node` FK → architecture_nodes · `relation` (calls|triggers|consumes|emits|updates|approves) · `integration_pattern` (sync_api|async_event|batch|workflow|document|agent) · `provenance`
Indexes: `(automation_id, from_node, to_node)`

### evidence
`id` PK · `finding_id` FK · `source_id` FK → sources · `source_version_id` FK · `locator` (URL anchor/quote) · `confidence` · `captured_at` · `blob_uri`
Indexes: `(finding_id)`, `(source_id)`

### opportunities
`id` PK · `automation_id` FK · `status` (open|validated|rejected|monitor|in_build) · `gap_class` (standard|configurable|extensible|partner|missing) · `build_path` (standard_sap|configuration|extension|btp_automation|custom_app|ai_agent|external_integration) · `clean_core_relevance` · `ecc_to_s4_flag` · `reuse_score` · `dependencies` (JSONB) · `owner` FK → users · `validation_checklist` (JSONB) · `score` (computed, cached) · `created_at` · `updated_at`
→ scores

### scores
`id` PK · `opportunity_id` FK · `metric` (business_value|automation_potential|technical_feasibility|reusability|demand|differentiation|clean_core|complexity_penalty) · `value` NUMERIC · `rationale` TEXT · `weight` NUMERIC · `overridden` BOOL · `override_reason` · `overridden_by` FK → users
Indexes: `(opportunity_id, metric)`

### reports
`id` PK · `tenant_id` FK · `period_start` · `period_end` · `status` (draft|generated|published|failed) · `file_uri` · `generated_at` · `config` (JSONB: recipients, filters, weights)
→ report_items

### report_items
`id` PK · `report_id` FK · `finding_id` FK · `rank` · `section` · `score_at_generation`
Indexes: `(report_id, rank)`

### reviews
`id` PK · `tenant_id` FK · `entity_type` (finding|automation|opportunity|score|architecture) · `entity_id` · `reviewer_id` FK → users · `decision` (approve|reject|revise|escalate) · `comments` · `created_at` · `resolved_at`

### agent_runs
`id` PK · `agent_type` · `tenant_id` · `run_id` (idempotency key, unique) · `model` · `prompt_version` · `model_version` · `status` · `input_refs` (JSONB) · `output_artifacts` (JSONB) · `token_cost_usd` · `latency_ms` · `created_at`
→ audit_log

### audit_log
`id` PK · `actor_id` FK → users · `action` · `entity_type` · `entity_id` · `details` (JSONB) · `timestamp`
Indexes: `(actor_id, timestamp)`, `(entity_type, entity_id)`

## 4. Security Model

- **Tenant isolation at every query boundary** — all queries scoped by `tenant_id` (row-level security preferred).
- **RBAC roles:** `platform_admin`, `tenant_admin`, `architect`, `analyst`, `reviewer`, `executive`, `read_only`.
- **Audit** administrative and review actions.
- **Encrypt secrets and sensitive configuration outside application data** (secret manager, not columns).
- **Source-content retention & licensing policies** applied to `source_versions`/`evidence` blobs.

## 5. Migrations & Conventions

- Versioned migrations (e.g., Alembic for Postgres); forward-only with rollback scripts for destructive changes.
- `updated_at` maintained by trigger or app layer; `created_at` immutable.
- Soft-delete for governed entities (sources, opportunities) with audit trail; hard delete only where policy requires.
- IDs: ULID/`UUIDv7` for global ordering (report ranking stability), human-safe slugs for canonical keys.

## 6. Query Patterns

| Need | Pattern |
|---|---|
| "What changed in last 30/90/180 days" | `changes.created_at` / `findings.first_detected_at` window + filter |
| Faceted search | PostgreSQL FTS on findings + facet fields (domain, industry, product, type) |
| Semantic search | Qdrant embedding over findings/automation cards |
| Cross-domain "AI affecting MM & manufacturing" | Neo4j multi-hop over automation→product→domain→industry |
| Lineage source→…→report | join path via evidence/findings/automations/report_items |
