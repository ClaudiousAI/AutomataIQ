# 11 — Frontend Architecture

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Finalized — implementation-ready frontend architecture
**Related docs:** [09_UI_UX_Design](./09_UI_UX_Design.md) · [08_API_Design](./08_API_Design.md) · [04_System_Architecture](./04_System_Architecture.md) · [ADR-0015](./17_Architecture_Decision_Records/0015-react-javascript-frontend.md)

---

## 1. Frontend Decision

SAIE's frontend is a **React + JavaScript** single-page application built with **Vite** and served as static assets behind **Nginx**. The frontend does **not** use TypeScript in hand-authored source files.

**Rationale:** the product needs a professional, fluid, ultra-smooth intelligence workspace with rich tables, interactive diagrams, evidence drawers, transitions, and responsive dashboard behavior. A React SPA keeps the UI runtime simple and optimized for client-side interactivity in an authenticated enterprise workspace.

---

## 2. Stack

| Concern | Decision | Notes |
|---|---|---|
| UI runtime | React + JavaScript | Functional components + hooks only |
| Build tool | Vite | Fast dev server, optimized static build |
| Routing | React Router | Client-side workspace routes |
| Server state | TanStack Query | Query cache, retries, invalidation, polling |
| Forms | React Hook Form + schema validation | Client UX validation; server remains source of truth |
| Styling | CSS variables/design tokens + component CSS | Theme-aware, responsive, no hard-coded colors |
| Icons | Open-source icon package or internal SVGs | Accessible labels where needed |
| Charts/diagrams | SVG/Canvas/React graph components | Must preserve evidence labels and keyboard access |
| Auth | OIDC via Keycloak | Token/session integration; server enforces RBAC |
| Testing | Vitest + Testing Library + Playwright | Unit/component/e2e coverage |
| Lint/format | ESLint + Prettier | JavaScript/React rules; no TypeScript source |

**Allowed file extensions:** `.js`, `.jsx`, `.css`, `.json`, `.html`, `.svg`.

**Not allowed in hand-authored frontend source:** `.ts`, `.tsx`, TypeScript-only syntax, Next.js App Router, frontend SSR runtime.

---

## 3. Structure

```
web/
  index.html
  vite.config.js
  package.json
  src/
    main.jsx                  # React entry point
    app/
      App.jsx                 # top-level app shell
      providers.jsx           # query, auth, theme, router providers
      router.jsx              # React Router route tree
      layouts/
        WorkspaceLayout.jsx
        AuthLayout.jsx
    components/
      primitives/             # Button, Card, Dialog, Drawer, Tabs, Badge, Tooltip
      data-display/           # DataTable, KpiCard, Timeline, EmptyState
      feedback/               # ErrorState, Toast, Skeleton, Progress
      visualization/          # ArchitectureDiagram, HeatMap, ScoreSparkline
    features/
      dashboard/
      discovery/
      intelligence/
      opportunities/
      knowledge/
      reports/
      governance/
      administration/
      settings/
    lib/
      api/                    # generated/openapi client wrapper + fetch helpers
      auth/                   # Keycloak/OIDC session helpers
      query/                  # query keys, polling helpers, mutation wrappers
      rbac/                   # role/action gating helpers
      formatting/             # dates, scores, confidence labels
      validation/             # runtime schemas for forms and API edges
    styles/
      tokens.css
      global.css
      themes.css
      motion.css
    tests/
      unit/
      components/
      e2e/
```

---

## 4. Page ↔ App-Flow Mapping

| App-flow area | Route | Primary API source |
|---|---|---|
| Home / Weekly Pulse | `/dashboard` | `/reports/latest`, `/findings`, `/opportunities` |
| Discovery | `/discovery/*` | `/sources`, `/crawl-runs`, `/changes` |
| Intelligence | `/intelligence/*` | `/automations`, `/architectures` |
| Opportunities | `/opportunities/*` | `/opportunities`, `.../scores` |
| Knowledge | `/knowledge/*` | `/search`, `/graph` |
| Reports | `/reports/*` | `/reports`, `.../export` |
| Governance | `/governance/*` | `/reviews`, `/audit` |
| Administration | `/administration/*` | `/admin/*`, `/health/*` |
| Settings | `/settings` | `/admin/*`, `/health/*` |

Routes are client-side. Nginx rewrites application routes to `index.html`; API calls route to FastAPI.

---

## 5. Core UX Components

| Component | Responsibility | Guardrails |
|---|---|---|
| `DataTable` | Dense sortable/filterable tables, facets, cursor pagination | Virtualize large result sets; URL-backed filters |
| `EvidenceBadge` | Confirmed/corroborated/inferred/speculative label | Text + icon + color; never color-only |
| `ScoreBadge` | Composite score, metric sparkline, rationale tooltip | Scores are recommendations, not facts |
| `ArchitectureDiagram` | Interactive node/edge graph and flow view | Confirmed vs inferred layer toggle; evidence drawer |
| `Timeline` | Version → change → finding progression | Keyboard navigable; compact/detailed density |
| `EvidenceDrawer` | Source, locator, snapshot, confidence, captured time | Copyable evidence refs; no hidden provenance |
| `ReviewQueue` | Human decision workflow, correction, override | Audit confirmation for governed actions |
| `KpiCard` | Headline metrics and trend | Skeleton/loading/error states built in |
| `HealthPanel` | Source/agent/queue/cost status | Live polling with backoff; clear degraded state |

---

## 6. State & Data Patterns

1. **Server state lives in TanStack Query.** Query keys are centralized in `lib/query/keys.js`.
2. **URL state for shareable views.** Filters, sorting, pagination cursors, and selected tabs use query params where practical.
3. **Minimal local state.** Local React state is for transient UI only: open drawers, focused rows, density preference, temporary form drafts.
4. **Governed mutations are confirmed.** Review decisions, score overrides, source configuration changes, and admin actions require confirmation and server audit.
5. **Optimistic UI only for low-risk actions.** Visual preferences and non-governed toggles may update optimistically; business decisions wait for server confirmation.
6. **Long-running jobs never block the UI.** Crawl/report actions return job IDs; the UI polls job resources or event endpoints and shows progress, retry, and failed states.
7. **RBAC is reflected, not enforced, by the frontend.** The UI hides/disables unauthorized actions for clarity; FastAPI remains the enforcement boundary.

---

## 7. API Contract Pattern

- FastAPI publishes OpenAPI as the contract source of truth.
- The frontend may generate a JavaScript API client from OpenAPI, but hand-authored frontend source remains JavaScript.
- Runtime validation is used at API/form boundaries for defensive UX.
- API errors use `problem+json` and map to consistent user-facing error states.
- API clients must always attach tenant/session context through the auth layer; components never manually construct authorization headers.

---

## 8. Professional Look & Feel Requirements

The interface must feel like a polished enterprise intelligence product, not a basic admin CRUD UI.

| Quality | Rule |
|---|---|
| Fluidity | Skeletons, progressive loading, virtualized tables, non-blocking transitions |
| Responsiveness | Layout adapts from laptop to large monitor; no horizontal body scroll |
| Density | Configurable compact/comfortable modes for analyst workflows |
| Visual hierarchy | Clear cards, panels, section headers, and evidence emphasis |
| Motion | Subtle transitions only; respect reduced-motion preference |
| Trust | Every insight shows evidence, confidence, and rationale affordances |
| Professional polish | Consistent spacing, typography scale, alignment, iconography, empty/error states |

---

## 9. Accessibility & Governance UX

- Keyboard navigation for all primary flows.
- Visible focus states.
- AA contrast.
- No color-only meaning, especially confidence and score indicators.
- Reduced-motion support.
- ARIA labels for interactive diagram controls and drawer triggers.
- Review and override actions include confirmation, rationale capture, and audit visibility.
- Low-confidence items clearly show why a human review is required.

---

## 10. Build, Test, and Quality Gates

| Gate | Command family | Requirement |
|---|---|---|
| Lint | ESLint | No errors; React hooks rules enforced |
| Format | Prettier | Stable formatting |
| Unit/component | Vitest + Testing Library | Components and utilities covered |
| E2E | Playwright | Discover / Evaluate / Report journeys |
| Accessibility | Playwright/axe where configured | No critical accessibility issues |
| Build | Vite production build | Static assets generated and served by Nginx |
| Security | Dependency/secrets scan | No new high-severity findings |

Frontend test files must reference the Requirement ID(s) they verify, per [19_Definition_of_Done](./19_Definition_of_Done.md).

---

## 11. Frontend Implementation Guardrails

- Do not introduce Next.js, SSR, or server components.
- Do not introduce TypeScript for hand-authored frontend source.
- Do not call LLM providers or backend storage directly from the browser.
- Do not duplicate authorization decisions in components; use centralized RBAC helpers and rely on server enforcement.
- Do not render confidence, evidence, or scores without labels/rationale affordances.
- Do not hard-code colors; use design tokens.
- Do not build custom one-off table/filter behavior when shared primitives already cover it.

---

## 12. Definition of Done for This Architecture

This frontend architecture is finalized when:

- [x] React + JavaScript is locked as the frontend stack.
- [x] Next.js + TypeScript is removed from operative frontend architecture.
- [x] Routing, state, API, styling, testing, and UX guardrails are specified.
- [x] Professional, fluid, ultra-smooth UX requirements are explicit.
- [x] Implementation is blocked from starting until AI, frontend, and backend architecture are all finalized.
