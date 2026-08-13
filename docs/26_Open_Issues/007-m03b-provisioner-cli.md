---
gh_issue_number: null
gh_issue_url: null
local_id: 007
type: feat
priority: high
area: [backend, data, ops]
title: "feat(data): M03b provisioner CLI - saie.bootstrap idempotent entry point"
module: M03b
rtm_ids: [NFR-007, NFR-013]
filed: 2026-08-13
filed_by: orchestrator
status: open
parent_local_id: 001
sub_issue_local_ids: []
mirror_pending: true
---

# feat(data): M03b provisioner CLI - saie.bootstrap idempotent entry point

> Sub-issue of [`001-m03b-storage-substrate`](./001-m03b-storage-substrate.md). Filed **before** the four store-side sub-issues (`002`, `003`, `004`, `005`) ship their bootstraps, by conductor judgment call: the provisioner CLI is the **glue** that ties the four bootstrap scripts into a single `saie.bootstrap` entry point and ships the AC-1 cross-cutting integration test (provisioner idempotency on clean + post-bootstrap state). The four store-side implementers read this file as part of their context so their bootstrap scripts expose a uniform shape the provisioner can call. Tracker-blocked; mirrors the would-be GitHub Issue body per [`docs/26/README.md`](../26_Open_Issues/README.md).

## Summary

Ship the **single entry point** that bootstraps the entire M03b storage substrate. The provisioner is idempotent (NFR-007, AC-1): running it twice from a clean state yields identical resource state; re-running from a post-bootstrap state is a no-op. The provisioner is what the M03 acceptance criterion *"Seed re-runs produce no duplicates"* means in practice for the storage layer.

The provisioner does **not** write the four bootstrap scripts — those ship in `002` (Redis), `003` (Qdrant), `004` (Neo4j), `005` (MinIO). The provisioner **calls** them in dependency order, captures their idempotency state, and exposes a single CLI / Celery-task surface that the M03a CI substrate and `docker-compose.yml` for dev both consume. This is the property AC-7 captures (the provisioner is wired into docker-compose and CI) and AC-1 enforces (the cross-cutting integration test).

## Linked Requirement ID(s)

`NFR-007` (Recoverability — idempotent, replayable jobs; drives the AC-1 cross-cutting integration test) · `NFR-013` (Model lock-in resistance — the provisioner is vendor-agnostic; it dispatches to the four vendor-specific bootstraps but exposes a vendor-neutral interface)

## Parent epic ACs satisfied

`AC-1` (provisioner idempotency — the central AC) · `AC-7` (docker-compose wiring — the provisioner is the surface `docker-compose up` calls) · `AC-9` (docs/18 gotcha discipline — any CI / runtime gotcha the provisioner surfaces gets pinned)

## Sequencing (per architect recommendation in [`008` §g](./008-m03b-architect-design.md))

`007` lands **after** `002`, `003`, `004`, `005` merge — the four bootstrap scripts must exist before the provisioner can glue them. Filing `007` as a sub-issue now (before the four ship) is the conductor's judgment call: the four implementers read this file so their bootstrap scripts expose a uniform shape. The implementation work (the actual `saie.bootstrap` entry point, the AC-1 cross-cutting integration test, the docker-compose wiring) does not start until the four store-side PRs merge.

## Acceptance Criteria

- [ ] **AC-glue-1** `backend/app/storage/bootstrap.py` ships `saie.bootstrap` as the single idempotent entry point. Signature: `def run(force: bool = False, *, dry_run: bool = False) -> ProvisionerReport`. Returns a structured report (`ProvisionerReport` dataclass) with per-store status (created / already-exists / failed), timing, and any warnings. The report is JSON-serializable for the CI substrate to assert on.
- [ ] **AC-glue-2** The provisioner dispatches to the four store-side bootstraps in dependency order: Redis first (cache namespace + Streams + DLQ), then Qdrant (collection + HNSW), then Neo4j (constraints + seed), then MinIO (buckets + lifecycle). The order matters because the Neo4j seed references Redis namespace constants and the MinIO lifecycle rules reference Qdrant collection names. Dependency order is documented in `bootstrap.py`'s module docstring; deviating from it is a bug.
- [ ] **AC-glue-3** Idempotency: each store-side bootstrap must be idempotent on its own (per its own sub-issue's AC). The provisioner adds the **cross-cutting** idempotency check: a `saie.bootstrap` run on a fully-bootstrapped state returns `ProvisionerReport` with all four statuses `already-exists` and zero new resources created. The `force=True` flag re-runs every bootstrap from scratch (used by the AC-1 test to reset state between runs); without `force`, the provisioner detects "already-exists" via the per-store idempotency check and skips.
- [ ] **AC-glue-4** `backend/tests/integration/test_provisioner_idempotency.py` ships the AC-1 cross-cutting integration test:
  - **Test 1: clean state.** Run `saie.bootstrap()` against a fresh docker-compose stack; assert all four statuses are `created`; assert zero `already-exists`; capture the resource state snapshot.
  - **Test 2: post-bootstrap state.** Re-run `saie.bootstrap()` on the same stack without `force=True`; assert all four statuses are `already-exists`; assert zero new resources; assert the resource state snapshot from Test 1 is byte-identical to Test 2's snapshot (the property NFR-007 demands).
  - **Test 3: idempotency-key replay.** Simulate a Celery task retry by calling `saie.bootstrap()` twice in quick succession on a partially-bootstrapped state (Redis + Qdrant done; Neo4j in flight when the second call starts); assert the second call waits for the first to finish or returns a structured "already-in-progress" status, NOT a duplicate resource. This is the NFR-007 replay-safety property.
- [ ] **AC-glue-5** `backend/cli/saie_bootstrap.py` (or equivalent — the CLI surface) wraps `saie.bootstrap` for manual / docker-compose use. Flags: `--dry-run` (prints the plan, creates nothing), `--force` (re-runs from scratch, used by tests), `--store <redis|qdrant|neo4j|minio>` (run a single bootstrap, used for debugging and for the M03a CI substrate's per-store isolation). The CLI is **not** a Celery task; Celery wraps it via `celery.app.task` decorator in M04.
- [ ] **AC-glue-6** Docker Compose wiring: `docker-compose.yml`'s `saie-bootstrap` service runs `python -m backend.cli.saie_bootstrap` once after the four store services are healthy; the service exits 0 on success and the stack is then ready for M04 to start. The healthcheck pattern is the same as M03a: `dockerize -wait tcp://redis:6379` etc. before invoking the provisioner. `docker compose up` brings Redis + Qdrant + Neo4j + MinIO + the bootstrap service online idempotently (AC-7).
- [ ] **AC-glue-7** CI substrate integration: the M03a CI workflow (`apt-get install -y postgresql postgresql-contrib` etc.) gets extended with the four store containers (Redis, Qdrant, Neo4j, MinIO) pinned to the same image SHAs as dev. The provisioner is invoked once at the top of the test job; the AC-1 test runs against the live provisioner output. Any new CI / runtime gotcha surfaces during this integration and gets pinned in `docs/18 §6` per AC-9.
- [ ] **AC-glue-8** The provisioner exposes a `ProvisionerReport` dataclass with per-store structured status, used by the AC-1 test for assertions AND by M16's `/health/bootstrap` endpoint for observability. Fields: `redis: StoreStatus`, `qdrant: StoreStatus`, `neo4j: StoreStatus`, `minio: StoreStatus`, `started_at: datetime`, `finished_at: datetime`, `warnings: list[str]`. `StoreStatus` is an enum: `created | already_exists | failed | skipped`.

## Uniform bootstrap-script shape (the contract `007` requires of `002`–`005`)

The four store-side sub-issues' bootstrap scripts must expose a uniform shape so `007`'s provisioner can call them generically. The contract:

```python
# Each backend/app/db/<store>/bootstrap.py exposes:
def run(force: bool = False, *, dry_run: bool = False) -> StoreStatus:
    """Idempotent bootstrap for <store>.

    Returns StoreStatus enum: created | already_exists | failed.
    force=True re-runs from scratch (used by tests).
    dry_run=True prints the plan without executing.
    """
```

The four implementers (`002`/`003`/`004`/`005`) **must** ship a `bootstrap.py` in their store's `backend/app/db/<store>/` directory with this signature. The provisioner imports and dispatches:

```python
# backend/app/storage/bootstrap.py (sketch)
from backend.app.db.redis.bootstrap import run as bootstrap_redis
from backend.app.db.qdrant.bootstrap import run as bootstrap_qdrant
from backend.app.db.neo4j.bootstrap import run as bootstrap_neo4j
from backend.app.db.minio.bootstrap import run as bootstrap_minio

def run(force: bool = False, *, dry_run: bool = False) -> ProvisionerReport:
    ...
```

This is the contract that closes the M03b/M04 boundary: M04 imports `saie.bootstrap` and does not import any of the four store-side bootstraps directly. Cross-cutting dependency discipline, mirrors the `006` AC-6e contract at the bootstrap layer.

## Out of Scope

- The four store-side bootstrap scripts themselves — those ship in `002`, `003`, `004`, `005`. This sub-issue (`007`) ships the glue, not the bootstraps.
- M04 wiring (Celery task wrapper, FastAPI dependency injection). M04 imports `saie.bootstrap`; it does not own the bootstrap code.
- Production deployment topology, secrets management, cross-region replication, backup/restore. M16 owns the prod overlay; M03b (and `007`) ships the substrate + the dev/CI provisioner.
- The actual data that gets seeded into the four stores. The seed content lives in the four store-side sub-issues (`002`–`005`); the provisioner only calls the bootstraps.

## Tests Required

- **Integration** — `backend/tests/integration/test_provisioner_idempotency.py` (AC-glue-4): the three cross-cutting tests (clean state, post-bootstrap, idempotency-key replay).
- **Ops** — Docker Compose `saie-bootstrap` service exits 0 on a clean stack and on a re-run of a clean stack.
- **Contract** — the four store-side `bootstrap.py` files conform to the uniform signature above. Pinned by `backend/tests/test_bootstrap_contract.py` (a small test that imports each and asserts `run(force=False)` exists and returns `StoreStatus`).

## Definition of Done

- [ ] All eight ACs above checked (`AC-glue-1` … `AC-glue-8`).
- [ ] Linked RTM IDs in `docs/16` updated (NFR-007 → In Progress until AC-10 of the parent epic is checked; NFR-013 already In Progress via `006`).
- [ ] `backend/app/storage/bootstrap.py` committed + idempotent.
- [ ] `backend/cli/saie_bootstrap.py` committed with `--dry-run` / `--force` / `--store` flags.
- [ ] `docker-compose.yml` updated with the `saie-bootstrap` service + the four store services pinned to image SHAs (the M03a pattern of substrate == CI version applies).
- [ ] CI workflow updated to spin the four store containers and run the AC-glue-4 tests.
- [ ] Any new CI gotcha pinned in `docs/18 §6` per AC-9.
- [ ] PR title `feat(data): M03b provisioner CLI - saie.bootstrap idempotent entry point (NFR-007, NFR-013)`.
- [ ] Sub-issue AC ledger flipped at merge-time per `docs/25 §8`.
- [ ] Parent epic `001` §AC-1 checked at this sub-issue's merge (the cross-cutting idempotency test is the AC-1 deliverable; it lives here, not in `002`–`005`).

## Filed by

Orchestrator, 2026-08-13. Sub-issue of epic `001-m03b-storage-substrate`. Filed as the glue sub-issue per the architect's sequencing recommendation in [`008` §g](./008-m03b-architect-design.md). The implementation waits on `002`/`003`/`004`/`005` merging; the sub-issue is filed now so the four store-side implementers read the uniform bootstrap-contract and shape their `bootstrap.py` modules to match.
