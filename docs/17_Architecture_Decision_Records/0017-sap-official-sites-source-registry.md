# ADR-0017 — `SAP Official Sites.txt` as the canonical Discovery Engine source registry

- **Status:** Accepted
- **Date:** 2026-08-11
- **Supersedes:** —
- **Amends:** —

## Context

SAIE is, at its core, an intelligence platform over the SAP ecosystem.
The **Discovery Engine** (M07, FR-001…FR-007) and the downstream
**Opportunity Engine** (M09, FR-028…FR-033) need a curated, durable
list of authoritative sources to crawl, classify, and score. Without
one, M07 ships with an empty source registry and M09 has nothing to
validate against — defeating the product's central question
("*what changed, what automation pattern does it reveal, where can
it be applied, and what should we build or replace because of it?*").

The product owner (Ganesh) has already curated this list by hand and
committed it to the repo root as
[`SAP Official Sites.txt`](../../SAP Official Sites.txt) (175 lines,
~10 KB). The file covers:

- SAP master catalogs (`/products`, `/products/a-z`, help.sap.com,
  portfolio explorer, news.sap.com, community.sap.com,
  learning.sap.com).
- Core business domains (Business Suite, S/4HANA, BTP, Ariba, HCM,
  CX, sustainability, business transformation).
- S/4HANA functional areas (FI, CO, SD, MM, PP, QM, PM/EAM, EWM,
  TM, PS, PLM, MDG, GRC, Treasury, Service).
- Procurement + workforce (Ariba, Concur, SuccessFactors).
- Supply chain + manufacturing + logistics.
- CRM + customer experience + retail + media.
- Technology + automation + development (BTP, Integration Suite,
  Process Automation, ABAP, CAP, `api.sap.com`, HANA, AI Core,
  AI Launchpad, Joule, Cloud ALM).
- 25 industry portfolios (aerospace, automotive, banking,
  consumer products, healthcare, life sciences, manufacturing,
  mining, oil & gas, public sector, retail, telco, utilities, …).
- Innovation sources (`news.sap.com`, `community.sap.com`,
  `learning.sap.com`, Sapphire 2026 innovation guide).

Per `docs/02_Functional_Requirements.md` §"Discovery Engine", every
FR-001…FR-007 surface that touches *what to crawl* must consult a
durable registry rather than a free-form list inside code. ADR-0014
locks the technology stack but does not bind the source list — that
gap is what this ADR closes.

## Decision

**`SAP Official Sites.txt` is the canonical Discovery Engine source
registry for SAIE.** Every implementation of the Discovery, Evidence,
and Opportunity agents — at M07, M08, M09, and downstream — MUST read
this file as the authoritative input when seeding the source registry,
deriving connector types, computing source tiers, or building the
opportunity checklist.

Concretely:

1. **Single source of truth.** No agent is permitted to invent source
   URLs that are not in this file, and no source in this file may be
   silently dropped without a documented exception recorded in the
   change log below.
2. **Path.** The file lives at the repo root
   (`./SAP Official Sites.txt`) and is tracked in git. It is
   intentionally **not** placed under `docs/` or `infra/` — it is an
   *operational input*, not a design document, and its review
   lifecycle is content-owner-driven (not architecture-driven).
3. **Tiering seed.** Each source listed inherits an initial tier
   derived from its kind:
   - Tier 1 — `help.sap.com` (official documentation).
   - Tier 2 — `api.sap.com`, SAP product master catalogs
     (`/products/...`).
   - Tier 3 — `news.sap.com` innovation topics, `community.sap.com`,
     `learning.sap.com`.
   - Tier 4 — `pages.community.sap.com/topics/joule`, innovation
     guides.
   - Tier 5+ — partner / industry subdomains; to be re-tiered by the
     Discovery agent once M07's authority scorer is live.
   The M07 architect agent is responsible for promoting these to a
   first-class `source_tier` enum (see FR-004) without losing the
   provenance back to the originating line in the file.
4. **Connector-type seed.** Each source's URL pattern informs the
   connector type:
   - `help.sap.com/docs/...` → structured doc connector (FR-002).
   - `/products/...` HTML pages → HTML connector.
   - `news.sap.com/topics/...` → RSS / sitemap connector.
   - `api.sap.com/...` → API connector.
   - `community.sap.com/...` → community-syndication connector
     (deferred; reserved name `community_rss`).
   This seed is advisory — the M07 connector impl owns the final
   mapping.
5. **Crawl-policy inheritance.** All sources inherit
   `robots.txt`-respect + rate-limit + auth-boundary defaults from
   FR-007 / NFR-011. Sources that publish explicit terms
   (e.g. `community.sap.com`) require an opt-in flag captured at
   connector registration.
6. **Change log.** Updates to the file are recorded in §"Change log"
   below, with a one-line rationale per added/removed entry. Major
   additions (≥ 5 new URLs in a single commit) require a brief ADR
   amendment addendum.
7. **Honoring the file is required, not optional.** The Discovery
   agent's golden-set eval (FR-004, NFR-014) MUST assert that every
   seed in the registry traces back to a line in
   `SAP Official Sites.txt`; the Opportunity Engine's eval (FR-028)
   MUST assert that gap-classification inputs reference at least one
   source from this registry.

## Consequences

### Positive

- **Conductor-driven curation, agent-driven execution.** The product
  owner stays in control of *what counts as the SAP ecosystem*
  (their judgment), while the Discovery agent owns *how to fetch,
  parse, and tier* (architectural judgment). This is exactly the
  split the wizard protocol encodes: conductor = direction, agent =
  execution.
- **No drift between M03, M07, M08, M09.** Every later module reads
  the same file, so the registry is consistent by construction.
- **Tests pin the constraint.** The "every seed traces to a line in
  `SAP Official Sites.txt`" assertion makes a future agent that
  invents a URL fail loudly rather than silently.
- **Auditable.** Git history of the file is the audit trail for
  "which sources was SAIE watching on date X" — critical for NFR-001
  (auditability) and for the Saturday report's source attribution
  (FR-014 evidence trail).

### Negative / Trade-offs

- **The file is content-managed, not type-managed.** URLs are free-
  form strings; a typo or dead link will only surface at crawl time.
  Mitigated by an M07 health-check job that pings each Tier 1/2
  source weekly and emits a `source_health` alert (FR-055, FR-058).
- **Single-author bias.** The list is the product owner's curation.
  The Discovery agent's "promotion" mechanism (Tier 5+ sources
  discovered organically) is the escape hatch for sources the owner
  didn't initially include; those promotions MUST be back-ported
  into the file by the conductor before they become Tier 1/2.
- **No machine-readable structure (yet).** The file is plain text
  with section headers. The M07 bootstrap step parses it into the
  `sources` table (FR-001) once; the canonical form for runtime is
  the database row, not the text file. The text file is the seed,
  not the runtime registry.

### Neutral

- **No code change today.** This ADR only commits the constraint;
  the M07 implementation that consumes the file is a future module
  per `docs/22 §3`. No `app/` source file changes are required as a
  result of this ADR.

## Operational notes

- **Reading the file in M07.** The recommended parser entry point is
  a `sources_seed.py` module under `backend/app/discovery/` (to be
  created in M07). It MUST:
  1. Read the file by path-relative-to-repo-root.
  2. Skip comment lines (`#`-prefix) and blank lines.
  3. Group URLs under their numbered section heading (preserving the
     tier seed).
  4. Yield typed `SourceSeed` rows with fields
     `url, section, suggested_tier, suggested_connector`.
- **Updating the file.** Every PR that adds/removes URLs in
  `SAP Official Sites.txt` MUST also update §"Change log" below in
  this ADR, AND reference the corresponding FR ID in the commit
  message (per CLAUDE.md traceability rule).
- **What is *not* in scope here.** The 25 industry subdomains
  (§"SAP industry domains" in the file) are tier-pending; M07's
  authority scorer decides their final tier. This ADR does not
  pre-assign those tiers.

## Change log

| Date | Author | Change | Rationale |
|------|--------|--------|-----------|
| 2026-08-11 | Ganesh | Initial seed (175 lines, 10 KB) | First curated pass; covers catalog, BTP, S/4HANA, CX, SCM, industry portfolios, innovation sources. |

## Traceability

- **FR-001** Source registry (CRUD, tier, schedule) — file is the seed.
- **FR-002** Source-specific acquisition — connector-type mapping per §Decision.4.
- **FR-004** Source tiering (Tier 1–6) — tier seed per §Decision.3.
- **FR-007** Crawler policy compliance — inherits FR-007/NFR-011 defaults.
- **FR-028** Gap classification (M09) — opportunity inputs reference this file per §Decision.7.
- **NFR-001** Auditability — file's git history is the source-attribution audit trail.
- **NFR-011** Compliance — explicit `robots.txt` + terms-respect inheritance.
- **NFR-014** Quality gates — golden-set evals assert registry-traceability per §Decision.7.
