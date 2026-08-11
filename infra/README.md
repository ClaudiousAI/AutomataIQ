# SAIE — Infrastructure (M01)

This directory holds infrastructure-as-code that does not belong in
the application repos:

- `nginx.conf` — edge reverse proxy (production deployment, M16).
- `keycloak/` — Keycloak realm export (M02).
- `prometheus/` — Prometheus scrape config (M14).
- `grafana/` — Grafana dashboards (M14).

M01 only ships the edge Nginx config and the directory layout; later
modules fill it in as they land.

## Traceability

- NFR-004 — no secrets committed; all credentials are env-injected
  (`.env.example` is the only place to look for the names).
- NFR-005 — healthchecks are declared in each `Dockerfile` so the
  container orchestrator gates traffic on liveness.
- NFR-009 — production deployment shape documented in
  `docs/12_DevOps_Architecture.md`.
