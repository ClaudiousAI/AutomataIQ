# 11 — Frontend Architecture

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [09_UI_UX_Design](./09_UI_UX_Design.md) · [08_API_Design](./08_API_Design.md) · [04_System_Architecture](./04_System_Architecture.md)

---

## 1. Stack

- **Next.js + TypeScript** (App Router), server-side rendering for the workspace shell, client-side interactivity for tables/diagrams.
- Styling via design tokens (CSS variables) + a component library ([09_UI_UX_Design](./09_UI_UX_Design.md) §2).
- Data fetching: typed API client generated from the OpenAPI spec; TanStack Query (or equivalent) for server state.
- State: server-state via query cache; minimal client state (filters, UI prefs).

## 2. Structure (proposed)

```
web/
  app/                      # Next.js routes (App Router)
    (workspace)/
      dashboard/
      discovery/{sources,changes,errors}/
      intelligence/{automations,[id],architecture}/
      opportunities/{backlog,[id],validation}/
      knowledge/{products,processes,industries,technologies,apis}/
      reports/{[id],export}/
      governance/{review-queue,evidence,audit}/
      administration/{users,sources,schedules,scoring,agents,models}/
      settings/
  components/               # UI primitives + feature components
  features/                 # feature slices (findings, opportunities, report, ...)
  lib/                      # api client, auth, query hooks, utils
  styles/                   # tokens + global styles
  tests/                    # unit + component + e2e specs
```

## 3. Page ↔ App-Flow Mapping

| App-Flow area | Route | Data source (API) |
|---|---|---|
| Home / Weekly Pulse | `/dashboard` | `/reports/latest`, `/findings`, `/opportunities` |
| Discovery | `/discovery/*` | `/sources`, `/crawl-runs`, `/changes` |
| Intelligence | `/intelligence/*` | `/automations`, `/architectures` |
| Opportunities | `/opportunities/*` | `/opportunities`, `.../scores` |
| Knowledge | `/knowledge/*` | `/search`, `/graph` |
| Reports | `/reports/*` | `/reports`, `.../export` |
| Governance | `/governance/*` | `/reviews`, `/audit` |
| Administration | `/administration/*` | `/admin/*`, `/health/*` |

## 4. Core Components

- **DataTable** — dense, sortable, filterable, facet chips, cursor pagination.
- **EvidenceBadge** — Confirmed/Corroborated/Inferred/Speculative (label + icon + color).
- **ScoreBadge** — composite + metric sparkline + rationale tooltip.
- **ArchitectureDiagram** — interactive node/edge graph (SVG/Canvas), layer toggle (confirmed vs inferred), node→evidence drawer.
- **Timeline** — source-change timeline (version → change → finding).
- **EvidenceDrawer** — source, locator, snapshot, captured_at, confidence.
- **ReviewQueue** — decision actions, classification correction, score override.
- **KpiCard** — headline metrics with trend.

## 5. State & Data Patterns

- **Server-driven lists:** search/filter/sort are URL params (shareable, deep-linkable); results cached.
- **Job status:** long-running actions (crawl trigger, report generation) poll a job resource or subscribe to events; UI shows progress, never blocks.
- **Optimistic updates** for low-risk actions (toggles); **confirmed mutations** for governed actions (overrides, reviews) with audit confirmation.
- **RBAC-gating:** routes and actions reflect the user's role from session claims; server enforces regardless.

## 6. Accessibility & UX Guardrails

- Keyboard navigation, visible focus, AA contrast, no color-only meaning ([09_UI_UX_Design](./09_UI_UX_Design.md) §6).
- Configurable density; reduced motion.
- Error states map problem+json to readable UI with retry.

## 7. Build & Quality

- ESLint + Prettier; strict TypeScript (`noUncheckedIndexedAccess`).
- Component/viz regression tests + e2e for core journeys (Discover / Evaluate / Report) ([14_Testing_Strategy](./14_Testing_Strategy.md)).
- The [Artifact/dataviz guidance](../.claude/skills/) applies to heat maps and diagrams — accessible, theme-aware visualizations.
