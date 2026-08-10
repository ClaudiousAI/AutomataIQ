# 08 — API Design

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [07_Database_Design](./07_Database_Design.md) · [13_Security_Architecture](./13_Security_Architecture.md) · [11_Frontend_Architecture](./11_Frontend_Architecture.md)

**Convention:** REST over HTTPS, JSON bodies, typed schemas (FastAPI/Pydantic), OpenAPI generated. All endpoints are tenant-scoped; the tenant is derived from the authenticated principal, never trusted from the client.

---

## 1. Common Conventions

- **Base path:** `/api/v1`
- **Auth:** Bearer token / OIDC session; RBAC enforced per endpoint ([13_Security_Architecture](./13_Security_Architecture.md)).
- **Errors:** RFC 7807-style problem+json: `{ "type", "title", "status", "detail", "instance", "trace_id" }`.
- **Pagination:** `?cursor=` (opaque) + `limit` (default 50, max 200); responses return `next_cursor`.
- **Filtering/facets:** `?domain=MM&industry=manufacturing&type=agentic&since=...&confidence=high`
- **Idempotency:** mutating job endpoints accept `Idempotency-Key` header.
- **Versioning:** URL versioning (`/api/v1`); breaking change bumps the version.

## 2. Resource Map (capability → endpoint group)

| Capability | Group | Primary endpoints |
|---|---|---|
| C01 Sources | `/sources`, `/crawl-runs` | CRUD sources; list/re-run runs |
| C02 Changes | `/changes`, `/findings` | list changes; canonical findings |
| C03 Automation | `/automations` | Automation Cards; types |
| C04 Architecture | `/architectures` | nodes/edges; diagrams; summaries |
| C05 Opportunity | `/opportunities` | validation checklist; paths |
| C06 Scoring | `/opportunities/{id}/scores` | score vector; override |
| C07 Knowledge | `/search`, `/graph` | semantic search; graph queries |
| C08 Reports | `/reports` | generate; export; detail |
| C09 Governance | `/reviews`, `/audit`, `/health`, `/admin` | review queue; audit; ops |
| C10 Learning | `/feedback`, `/models`, `/taxonomy` | feedback; versions |

## 3. Selected Endpoint Contracts

### Sources
- `GET /sources` → `{ items: [Source], next_cursor }`
- `POST /sources` body `{ url, type, domain, industry, priority, schedule, tier, crawl_policy }`
- `PATCH /sources/{id}` — partial update (activates/deactivates)
- `GET /sources/{id}/crawl-runs` — history + health
- `POST /sources/{id}/crawl-runs` — trigger a run (idempotent)

```jsonc
// Source
{ "id": "src_...", "url": "...", "type": "rss", "domain": "sap-community",
  "industry": "manufacturing", "priority": 1, "schedule": "*/15 * * * *",
  "tier": 3, "active": true, "last_crawl_at": "...", "content_hash": "sha256:..." }
```

### Findings & Changes
- `GET /findings?since=&status=&confidence=&q=` — faceted, cursor-paginated
- `GET /findings/{id}` → finding + automation summary + evidence count
- `GET /changes?window=30d` → change records within window

```jsonc
// Finding
{ "id": "fnd_...", "canonical_key": "S4HANA-2026-...", "title": "...",
  "status": "new", "confidence": "high", "fact_label": "confirmed",
  "first_detected_at": "...", "last_updated_at": "..." }
```

### Automations (Automation Cards)
- `GET /automations?domain=MM&industry=manufacturing`
- `GET /automations/{id}` → full card: business_process, trigger, inputs, decisions, workflow, human_involvement, outcome, benefits {stated[], inferred[]}, products, automation_type

### Architecture
- `GET /architectures/{automation_id}` → `{ nodes: [], edges: [] }` (with provenance + integration_pattern)
- `POST /architectures/{automation_id}/summary` → text summary (LLM, async job)
- `GET /architectures/{automation_id}/diagram` → renderable diagram payload (JSON; server-side SVG/PDF in report)

### Opportunities & Scoring
- `GET /opportunities?status=&sort=score&min_score=` — ranked backlog
- `GET /opportunities/{id}` → gap_class, build_path, clean_core_relevance, ecc_to_s4_flag, dependencies, validation_checklist
- `GET /opportunities/{id}/scores` → score vector + rationale + composite
- `POST /opportunities/{id}/scores/{metric}/override` body `{ value, reason }` — RBAC reviewer+

```jsonc
// Score vector
{ "opportunity_id": "opp_...", "composite": 74.2,
  "metrics": [
    { "metric": "business_value", "value": 8, "weight": 0.20, "rationale": "...", "overridden": false },
    { "metric": "complexity_penalty", "value": -1.5, "weight": 1.0, "rationale": "...", "overridden": true, "override_reason": "..." }
  ] }
```

### Knowledge & Search
- `GET /search?q=...&domain=&industry=&window=&type=` → hybrid (vector + facets) ranked results with reasons
- `GET /graph/neighbors?entity=...&depth=2` → graph neighborhood
- `GET /graph/queries/cross-domain?from=MM&to=manufacturing` → connected findings

### Reports
- `POST /reports` body `{ period_end, config: { recipients[], filters{}, weights{}, format[] } }` → async job
- `GET /reports/{id}` → status + `file_uri` per format
- `GET /reports/{id}/export?format=pdf|html|json|csv`

### Governance & Ops
- `GET /reviews?state=pending` → review queue
- `POST /reviews/{id}/decision` body `{ decision, comments }`
- `GET /audit?actor=&entity=&window=` — audit trail (RBAC admin)
- `GET /health/sources`, `GET /health/agents`, `GET /health/queues`, `GET /cost` — operations dashboards
- `GET /admin/models`, `POST /admin/models` — model registry; `GET /admin/prompts` — prompt registry

### Learning (C10)
- `POST /feedback` body `{ entity_type, entity_id, dimension, rating, comment }`
- `GET /taxonomy`, `POST /taxonomy` — versioned taxonomy evolution (admin)

## 4. Event Schemas (internal async contracts)

```jsonc
// SourceVersionCreated
{ "event": "source.version.created", "version": 1,
  "source_version_id": "...", "source_id": "...", "content_hash": "sha256:...",
  "retrieved_at": "...", "blob_uri": "s3://...", "tenant_id": "..." }

// ChangeClassified
{ "event": "change.classified", "version": 1,
  "change_id": "...", "version_id": "...", "change_type": "enhancement",
  "confidence": 0.9, "semantic_summary": "...", "tenant_id": "..." }

// FindingPromoted
{ "event": "finding.promoted", "version": 1,
  "finding_id": "...", "canonical_key": "...", "confidence": "high",
  "needs_review": false, "tenant_id": "..." }

// ReportReady
{ "event": "report.ready", "version": 1,
  "report_id": "...", "period": "2026-W32", "file_uris": { "pdf": "...", "html": "...", "json": "...", "csv": "..." },
  "tenant_id": "..." }
```

Events are versioned; consumers tolerate forward versions (unknown fields ignored, missing required fields → dead-letter).

## 5. RBAC Matrix (subset)

| Action | platform_admin | tenant_admin | architect | analyst | reviewer | executive | read_only |
|---|---|---|---|---|---|---|---|
| Read findings/automations | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Trigger crawl | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Override score | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Review decision | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Generate/export report | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manage sources/schedules | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Manage users/roles | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Audit trail | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Model/prompt/taxonomy admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

## 6. Error Handling & Idempotency

- Retryable failures (LLM, crawl) return `429`/`503` with `Retry-After`; client retries with same `Idempotency-Key`.
- Validation failures return `422` with field-level detail.
- Duplicate submissions return the original result (200/201) rather than a new record.
