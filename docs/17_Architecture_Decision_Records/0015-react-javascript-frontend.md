# ADR-0015 — React (JavaScript) + Vite Frontend Architecture

**Status:** Accepted
**Date:** 2026-08-11
**Related:** [ADR-0001](./0001-nextjs-fastapi-stack.md) · [ADR-0014](./0014-cost-minimized-open-source-stack.md) · [11_Frontend_Architecture](../11_Frontend_Architecture.md) · [04_System_Architecture](../04_System_Architecture.md)
**Resolves:** Frontend stack for professional, fluid, ultra-smooth UX

---

## Context

The initial architecture (ADR-0001) adopted Next.js + TypeScript for the frontend, aligned with the master design TRD. However, during the architecture review, the product direction clarified that the SAIE workspace must deliver a **professional, fluid, ultra-smooth UX** with rich interactive components (data tables, architecture diagrams, evidence drawers, timeline visualizations, and real-time health dashboards) in an **authenticated enterprise workspace** — not a public marketing site.

Key constraints:
- No SSR/SEO needed (authenticated workspace)
- Single-runtime simplicity (React + Vite) reduces operational complexity
- React's component model + hooks provides the fluidity and interactivity required
- TypeScript adds complexity for hand-authored frontend source without proportional benefit for this team
- Vite produces optimized static assets served by Nginx — zero Node runtime in production

---

## Decision

Adopt **React + JavaScript (Vite SPA)** as the frontend architecture.

| Layer | Technology | Rationale |
|---|---|---|
| Frontend runtime | React + JavaScript | Component-driven, hooks-based, professional UX |
| Build tool | Vite | Fast dev, optimized static build |
| Routing | React Router | Client-side workspace routes |
| Server state | TanStack Query | Query cache, invalidation, polling for jobs |
| Styling | CSS variables + component CSS | Theme-aware, no hard-coded colors |
| Auth | OIDC via Keycloak | Session tokens, RBAC reflection |
| Testing | Vitest + Testing Library + Playwright | Unit/component/e2e |
| Lint/format | ESLint + Prettier | JavaScript/React rules |

**This decision amends ADR-0001** (which now supersedes only the FastAPI API decision; its Web UI portion is replaced by this ADR) and supersedes the Next.js portion of ADR-0014.

---

## Consequences

### Positive
- **Ultra-smooth UX:** React SPA eliminates SSR hydration latency; client-side transitions and interactions feel native.
- **Professional polish:** Rich component library (DataTable, ArchitectureDiagram, EvidenceDrawer, ReviewQueue) achievable with consistent patterns.
- **Simpler operations:** Static Vite build served by Nginx — no Node server, no SSR complexity, no Next.js upgrades.
- **Single runtime on frontend:** JavaScript only; TypeScript reserved for generated API contracts if desired.
- **Lower ops ceiling:** Matches ADR-0014's Docker-only deployment; no Node.js process to manage in production.
- **Team velocity:** Familiar React patterns, mature ecosystem, no TypeScript overhead in hand-authored code.

### Negative / Trade-offs
- **No SSR/SEO:** Acceptable — this is an authenticated workspace behind Keycloak.
- **No compile-time type safety in frontend source:** Mitigated by OpenAPI-generated types for API boundaries, runtime validation, and centralized type-like patterns in JSDoc where needed.
- **Client-side routing requires Nginx rewrite config:** Standard SPA pattern; documented in deployment.
- **Team must adopt React + JavaScript discipline:** Enforced via CI lint rules and this ADR.

### Neutral
- Generated API client from OpenAPI may emit TypeScript types; the frontend consumes them as JavaScript via `import type` or runtime validation.
- Component library choice (shadcn-style composition, Radix primitives, internal) remains open — deferred to M13 implementation with this ADR as the guardrail.
- Keycloak OIDC integration is unchanged (ADR-0010).

---

## Open Questions (Resolved by this ADR)

| Question | Resolution |
|---|---|
| Next.js or React SPA? | React + JavaScript SPA |
| TypeScript in frontend source? | No — hand-authored source is JavaScript |
| Build tool? | Vite |
| SSR or static? | Static (Vite build → Nginx) |
| Routing? | React Router (client-side) |
| Component library? | Deferred to M13; must compose with design tokens |

---

## Related Updates

- **ADR-0001** amended: Web UI portion superseded by this ADR; FastAPI API decision remains.
- **ADR-0014** amended: Frontend row updated to React + JavaScript (Vite SPA).
- **docs/04_System_Architecture.md** updated: Presentation layer = React + JavaScript (Vite SPA).
- **docs/11_Frontend_Architecture.md** finalized: Complete implementation-ready architecture.
- **docs/20_Architecture_Review_Pack.md** updated: UI framework = React + JavaScript (Vite SPA).
- **CLAUDE.md** updated: Stack lock reflects React + JavaScript.
- **docs/18_Project_Memory.md** updated: ADR-0001 entry updated.
- **docs/19_Definition_of_Done.md** updated: TypeScript check removed from universal DoD.
- **docs/22_Module_Roadmap.md** updated: M01 and M13 scope updated to React + JavaScript.