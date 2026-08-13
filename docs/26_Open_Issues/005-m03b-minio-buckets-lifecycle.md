---
gh_issue_number: null
gh_issue_url: null
local_id: 005
type: feat
priority: high
area: [backend, data]
title: "feat(data): provision MinIO buckets + versioning + lifecycle"
module: M03b
rtm_ids: [FR-008, NFR-011, NFR-013]
filed: 2026-08-13
filed_by: orchestrator
status: open
parent_local_id: 001
sub_issue_local_ids: []
mirror_pending: true
---

# feat(data): provision MinIO buckets + versioning + lifecycle

> Sub-issue of [`001-m03b-storage-substrate`](./001-m03b-storage-substrate.md). Tracker-blocked; mirrors the would-be GitHub Issue body per [`docs/26/README.md`](../26_Open_Issues/README.md).

## Summary

Provision the MinIO object store that holds versioned source snapshots, agent artifacts, and the published Saturday report. Ships the three buckets with versioning enabled, the lifecycle / retention rules per NFR-011, IAM policy per bucket, and the `MinioAdapter` Protocol. Retention is enforced by the lifecycle rule, **not** by application code — this is the property the M03 AC "retention enforced" means in practice.

## Linked Requirement ID(s)

`FR-008` (Versioned snapshots — policy-compliant storage + normalized snapshot) · `NFR-011` (Compliance — robots, terms, retention) · `NFR-013` (Storage adapters behind interfaces)

## Parent epic ACs satisfied

`AC-1` (provisioner idempotency) · `AC-5` (buckets + lifecycle + retention) · `AC-7` (docker-compose wiring) · `AC-8` (cross-tenant denial) · `AC-6` (Protocol contract — `MinioAdapter`)

## Acceptance Criteria

- [ ] **AC-4a** Three buckets exist: `saie-snapshots` (versioned, lifecycle: archive to warm tier after 90 d, expire after 7 y per NFR-011 retention), `saie-artifacts` (versioned, lifecycle: expire after 1 y), `saie-reports` (write-once via bucket policy, lifecycle: keep indefinitely; reports are the audit trail). The `saie-reports` bucket rejects `PutObject` on an existing key — the policy is `Deny` on `s3:PutObject` when the key already exists.
- [ ] **AC-4b** Versioning enabled on `saie-snapshots` and `saie-artifacts`; lifecycle rules are committed to `infra/minio/lifecycle.json` (or equivalent declarative form) and applied idempotently by the provisioner.
- [ ] **AC-4c** `pytest tests/integration/test_minio_lifecycle.py` green: a synthetic aged object is detected by the lifecycle rule and tiered (or expired, depending on age); the write-once policy on `saie-reports` rejects a second `PutObject` on the same key. The test uses MinIO's `mc admin` to advance the clock if necessary — **not** a real 90-day sleep.
- [ ] **AC-4d** `backend/app/storage/minio_adapter.py` ships the `MinioAdapter` **implementation**, importing the Protocol from [`006`](./006-m03b-storage-adapter-interfaces.md) (`from backend.app.storage.protocols import MinioAdapter`). The implementation must satisfy every method on the Protocol; the Protocol's `t/{tenant_id}/{key}` key-prefix rule, the cross-tenant `presigned_url` policy scoping, and the `tenant_id`-first invariant are the source of truth and live in `006`. This sub-issue ships only the implementation — the contract is locked upstream so it cannot drift across the four adapters.
- [ ] **AC-4e** Docker Compose service: `minio/minio:latest` with `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` from a Docker secret (not env), persistent volume, healthcheck on `:9000`. The lifecycle rules are applied via a one-shot `minio/mc` job that runs after the MinIO service is healthy.
- [ ] **AC-4f** CI on the Ubuntu runner: spin a MinIO container for integration tests; pin the image SHA; the lifecycle-advance pattern (mc) is exercised in-test, not via wall-clock.

## Out of Scope

- M16 work: production secrets management (Docker secrets / SOPS), cross-region replication, backup/restore drills, the prod TLS termination. M03b is the substrate; M16 is the production deployment topology.
- The actual content of snapshots (M07 produces them; M03b ships the bucket they land in).
- The actual content of artifacts (M06+ agent envelope produces them; M03b ships the bucket).
- The PDF / HTML / JSON / CSV renderers (M12 ships those; M03b ships the bucket M12 writes to).

## Tests Required

- **Integration** — `test_minio_lifecycle.py` (AC-4c): aged-object tiering; write-once policy on `saie-reports`.
- **Contract** — `MinioAdapter` Protocol method signatures; M04 import smoke test.
- **Ops** — Docker Compose `minio` service healthcheck is green; the `mc` job applies lifecycle rules without error.

## Definition of Done

- [ ] All ACs above checked.
- [ ] Linked RTM IDs in `docs/16` updated.
- [ ] `infra/minio/lifecycle.json` committed + applied idempotently.
- [ ] Any new CI gotcha pinned in `docs/18 §6`.
- [ ] PR title `feat(data): provision MinIO buckets + versioning + lifecycle (FR-008, NFR-011, NFR-013)`.
- [ ] Sub-issue AC ledger flipped at merge-time per `docs/25 §8`.

## Filed by

Orchestrator, 2026-08-13. Sub-issue of epic `001-m03b-storage-substrate`.
