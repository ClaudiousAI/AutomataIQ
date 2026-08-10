# ADR-0011 — Frontend Hosting: Container in the Cluster

**Status:** Superseded by [ADR-0014](./0014-cost-minimized-open-source-stack.md)
**Date:** 2026-08-10
**Superseded:** 2026-08-10
**Related:** [ADR-0001](./0001-nextjs-fastapi-stack.md) · [ADR-0008](./0008-aws-cloud-platform.md) · [11_Frontend_Architecture](../11_Frontend_Architecture.md)
**Resolves:** OD-7 (Next.js hosting model)

## Context
The Next.js frontend must be served in three environments (dev/staging/prod) alongside the FastAPI API, workers, and Temporal. Options: a serverless frontend host (Vercel) vs. a container in the same Kubernetes cluster as everything else.

## Decision
Host the Next.js application as a **container in the same EKS cluster** as the API and workers.

- Built as a Docker image in CI, pushed to ECR, deployed via Helm (ADR-0008).
- Node.js standalone build (`output: "standalone"`) for a minimal runtime image.
- Served behind the cluster ingress; SSR and static assets served from the container; CDN in front for caching (Phase 14).

## Consequences
### Positive
- Single deployment platform and pipeline for the whole product — one GitOps path, one observability mesh.
- Enterprise controls (tenant isolation, egress, WAF, audit) apply uniformly to the UI.
- No second-platform vendor relationship; avoids Vercel-specific lock-in.
### Negative / Trade-offs
- The team owns Node runtime scaling/patching that Vercel would absorb.
- SSR pods need CPU for render; mitigated by `output: "standalone"` and horizontal autoscaling.
### Neutral
- Next.js app stays framework-standard (App Router, SSR + client) so it could be moved to Vercel later without re-architecture.
