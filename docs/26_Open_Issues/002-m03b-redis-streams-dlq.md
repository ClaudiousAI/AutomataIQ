---
gh_issue_number: null
gh_issue_url: null
local_id: 002
type: feat
priority: high
area: [backend, data]
title: "feat(data): provision Redis Streams + DLQ consumer groups"
module: M03b
rtm_ids: [NFR-007, NFR-013]
filed: 2026-08-13
filed_by: orchestrator
status: open
parent_local_id: 001
sub_issue_local_ids: []
mirror_pending: true
---

# feat(data): provision Redis Streams + DLQ consumer groups

> Sub-issue of [`001-m03b-storage-substrate`](./001-m03b-storage-substrate.md). Tracker-blocked; mirrors the would-be GitHub Issue body per [`docs/26/README.md`](../26_Open_Issues/README.md).

## Summary

Provision the Redis Streams substrate that the M04 event bus and the M07+ crawlers will produce to and consume from. Includes the cache namespace, three domain Streams topics, their consumer groups, and the DLQ stream + DLQ consumer group. Also ships the `RedisAdapter` Protocol contract that the other three sub-issues (`003`, `004`, `005`) inherit the shape from.

## Linked Requirement ID(s)

`NFR-007` (Recoverability — idempotent, replayable jobs) · `NFR-013` (Model lock-in resistance — storage adapters behind interfaces)

## Parent epic ACs satisfied

`AC-1` (provisioner idempotency) · `AC-2` (Streams + DLQ round-trip) · `AC-7` (docker-compose wires it in) · `AC-6` (Protocol contract origin — `RedisAdapter`)

## Acceptance Criteria

- [ ] **AC-1a** Stream topics `saie.crawl`, `saie.evidence`, `saie.report` exist; consumer groups `saie-crawl-cg`, `saie-evidence-cg`, `saie-report-cg` exist; `saie.dlq` DLQ stream + `saie-dlq-cg` consumer group exist. Idempotent: re-creating them is a no-op.
- [ ] **AC-1b** `pytest tests/integration/test_redis_streams_roundtrip.py` green: a real message is published to `saie.crawl`, consumed by the consumer group, ACKed, and removed from PEL; a poison message is published, fails processing N times, and lands on `saie.dlq` (NFR-007).
- [ ] **AC-1c** `backend/app/storage/redis_adapter.py` ships the `RedisAdapter` **implementation**, importing the Protocol from [`006`](./006-m03b-storage-adapter-interfaces.md) (`from backend.app.storage.protocols import RedisAdapter`). The implementation must satisfy every method on the Protocol; the Protocol's method signatures, docstrings, and `tenant_id`-first invariant are the source of truth and live in `006`. This sub-issue ships only the implementation — the contract is locked upstream so it cannot drift across the four adapters.
- [ ] **AC-1d** Docker Compose service: `redis:7-alpine` with healthcheck; AOF persistence enabled; volume mount for dev.
- [ ] **AC-1e** CI on the Ubuntu runner: install or run Redis as a service for integration tests (extend the M03a `apt-get install -y postgresql postgresql-contrib` pattern; do not trust `services: redis` alone — pin the test substrate to the same version as dev/prod to avoid the M03a "postgresql-contrib was missing" failure mode).

## Out of Scope

- The M04 event-bus runtime (publish-on-request, consume-in-Celery-worker). M03b ships the *substrate*; M04 ships the *runtime* that uses it.
- Producer code in M07+ (crawlers), M08+ (research), M12 (reporting). M03b ships the topics; the producers come with their respective modules.
- Caching policy / cache-key conventions. Those land in M05 (LLM gateway prompt-response cache) and M11 (search cache).

## Tests Required

- **Integration** — `test_redis_streams_roundtrip.py` (AC-1b): publish/consume/ack happy path + poison → DLQ path.
- **Contract** — Protocol method signatures (AC-1c); an M04 import smoke test asserts the Protocol methods exist with the documented types.
- **Ops** — Docker Compose `redis` service healthcheck is green in `docker compose up`.

## Definition of Done

- [ ] All ACs above checked.
- [ ] Linked RTM IDs in `docs/16` updated (NFR-007 remains In Progress until AC-10 of the parent epic is checked; NFR-013 remains In Progress).
- [ ] Any new CI gotcha pinned in `docs/18 §6`.
- [ ] PR title `feat(data): provision Redis Streams + DLQ consumer groups (NFR-007, NFR-013)`.
- [ ] Sub-issue AC ledger flipped at merge-time per `docs/25 §8`.

## Filed by

Orchestrator, 2026-08-13. Sub-issue of epic `001-m03b-storage-substrate`.
