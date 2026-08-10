# 09 — UI/UX Design

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [11_Frontend_Architecture](./11_Frontend_Architecture.md) · [01_Product_Requirements](./01_Product_Requirements.md) · [02_Functional_Requirements](./02_Functional_Requirements.md)

---

## 1. Design Direction

**Modern enterprise intelligence console** — analytical, trustworthy, dense but readable, evidence-first, with clear separation between **confirmed facts** and **AI inference**.

Visual character: calm, high-information, deterministic-feeling. The UI must communicate "this is a system of record backed by evidence," not "an AI chatbot."

## 2. Design Tokens

- **Palette:** neutral surface base with a single brand accent for interactivity; semantic colors reserved for status (success/warn/danger) and confidence levels. Never the *only* signal — see Accessibility.
- **Typography:** system/enterprise stack; dense but readable; configurable density (comfortable / compact).
- **Spacing & radius:** tight grid for density; small radii; hairline borders.
- **Evidence badges:** Confirmed · Corroborated · Inferred · Speculative — distinct label + icon + color; labels must remain legible when color is removed.

## 3. Information Architecture (App Flow)

| Area | Pages |
|---|---|
| Home | Overview / Weekly Pulse |
| Discovery | Sources · Crawl Runs · Changes · Errors |
| Intelligence | Automation Findings · Detail · Architecture |
| Opportunities | Backlog · Detail · Validation |
| Knowledge | Products · Processes · Industries · Technologies · APIs |
| Reports | Saturday Reports · Detail · Export |
| Governance | Review Queue · Evidence · Audit |
| Administration | Users · Sources · Schedules · Scoring · Agents · Models |
| Settings | Profile · Notifications · Preferences |

Collapsible left navigation; breadcrumbs; persistent global search.

## 4. Core Patterns

- Executive KPI cards (sources scanned, meaningful changes, unique patterns, top opportunities).
- Dense sortable/filterable findings tables with facet chips.
- Evidence badges on every fact-bearing row.
- Transparent score badges (composite + sparkline of metric vector).
- Clickable architecture diagrams (pan/zoom; click node → evidence drawer).
- Source-change timeline (version → change → finding).
- Evidence side drawers (source, locator, snapshot link, captured_at).
- Human review queue with decision actions.
- Responsive laptop/tablet layout; desktop-first density.

## 5. Primary Screens

1. **Weekly Pulse Dashboard** — KPIs, top opportunities, change heat maps, report banner.
2. **Change Explorer** — timeline + facets over changes/findings.
3. **Automation Intelligence Board** — automation cards grouped by domain/type.
4. **Automation Detail** — full card: problem, current process, new capability, approach, benefits (stated/inferred).
5. **Architecture Viewer** — clickable diagram, confirmed/inferred layers toggle, integration patterns.
6. **Opportunity Radar** — ranked backlog, score breakdown, gap_class/build_path filters.
7. **Evidence Explorer** — searchable evidence with provenance.
8. **Report Viewer** — Saturday report render + export buttons.
9. **Review Queue** — pending items with evidence, classification correction, score override.
10. **Source Health** — per-source status, last crawl, error counts.
11. **Agent Operations** — runs, retries, DLQ, cost budgets.
12. **Administration** — users/roles, sources/schedules, scoring weights, model/prompt registry, taxonomy.

## 6. Accessibility

- Keyboard navigation and visible focus states throughout.
- Strong contrast (WCAG AA).
- Do not encode meaning by color alone — always paired with labels/icons.
- Accessible tables (proper headers, aria), sort/filter announced.
- Readable typography; configurable density; reduced-motion respected.

## 7. Empty / Loading / Error States

- Empty: actionable call-to-action ("Add a source" / "No changes this week").
- Loading: skeleton screens; async agents show job status, not infinite spinners.
- Error: problem+json surfaced readably with retry action; DLQ/alert surfaced in Agent Operations.
- Low-confidence: finding renders with warning treatment and routes to Review Queue.

## 8. Design Governance

- Component library driven by the [Frontend Architecture](./11_Frontend_Architecture.md) design system (tokens → primitives → patterns).
- Every new screen is a pattern composition; evidence/score/confidence components are single-sourced.
- Visual regressions covered by the [Testing Strategy](./14_Testing_Strategy.md).
