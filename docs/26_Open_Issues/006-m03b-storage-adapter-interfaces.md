---
gh_issue_number: null
gh_issue_url: null
local_id: 006
type: feat
priority: high
area: [backend, data]
title: "feat(data): M03b/M04 storage adapter interfaces (shared Protocols)"
module: M03b
rtm_ids: [NFR-007, NFR-013, FR-057]
filed: 2026-08-13
filed_by: orchestrator
status: open
parent_local_id: 001
sub_issue_local_ids: []
mirror_pending: true
---

# feat(data): M03b/M04 storage adapter interfaces (shared Protocols)

> Sub-issue of [`001-m03b-storage-substrate`](./001-m03b-storage-substrate.md). Filed **before** the four store-side sub-issues (`002`, `003`, `004`, `005`) ship their adapters, by conductor judgment call: the Protocol contract is the spine the four implementers import — if the contract drifts across the four PRs, the M04 import smoke test (`AC-6`) fails and the lint (`AC-11`) flags the regression. Filing this first is the inverse of `docs/25 §7`'s default ("file the sub-issue after the architect's design lands") and is the explicit exception. Tracker-blocked; mirrors the would-be GitHub Issue body per [`docs/26/README.md`](../26_Open_Issues/README.md).

## Summary

Ship the **single source of truth** for the four storage-adapter Protocol classes: `RedisAdapter`, `QdrantAdapter`, `Neo4jAdapter`, `MinioAdapter`. These Protocols are imported by the four store-side sub-issues (`002`–`005`), by the M04 wiring code, and by the AC-11 lint test. No implementation lives in this sub-issue — only the contracts — so that the four implementers cannot drift from the shared shape.

This is the file that fixes the M03b/M04 interface-contract ownership: before this filing, the four sub-issues each said "the Protocol contract is captured in `002` and inherited by `003`/`004`/`005`," which was both a single point of failure (`002` becomes a coupling hub) and a denial of the Protocol's actual status as a cross-cutting interface. With this filing, the four sub-issues' Protocol ACs (`AC-1c`, `AC-2d`, `AC-3e`, `AC-4d`) defer to `006`.

## Linked Requirement ID(s)

`NFR-013` (Model lock-in resistance — storage adapters behind interfaces) · `NFR-007` (Recoverability — idempotent, replayable jobs; drives the M04 import smoke test discipline) · `FR-057` (Tenant isolation — uniform across stores)

## Parent epic ACs satisfied

`AC-6` (Protocol contract + M04 import smoke test) · `AC-11` (Tenant isolation as a lint-enforced invariant; the test scaffolding the architect designs lives here)

## Acceptance Criteria

- [ ] **AC-6a** `backend/app/storage/protocols.py` ships four `typing.Protocol` classes — `RedisAdapter`, `QdrantAdapter`, `Neo4jAdapter`, `MinioAdapter` — with method signatures only (no implementation). Each method's first positional parameter is `tenant_id: UUID` and its docstring states the invariant. See the **Contract** section below for the full shape.
- [ ] **AC-6b** Each Protocol's class docstring cross-references the M03a `app.tenant_id` GUC convention and the epic-level AC-11 — the Protocol is the M03b expression of the M03a tenant-isolation invariant. The docstring states: *"The adapter's first parameter IS the tenant context, and the adapter refuses to construct a query that doesn't filter on it. This is the M03b equivalent of the M03a `SET LOCAL app.tenant_id` RLS convention."*
- [ ] **AC-6c** `backend/tests/test_storage_adapter_interfaces.py` ships as the **M04 import smoke test** (per the parent's `AC-6`): imports `backend.app.storage.protocols`, asserts each Protocol exposes the documented methods, and asserts each method's first parameter is named `tenant_id` (string-level introspection of the signature, not duck typing). This is the **import-time** test; the **build-time** test lives at `backend/tests/security/test_tenant_isolation_pattern.py` (the AC-11 lint) and is authored alongside this file in the same PR.
- [ ] **AC-6d** Protocol methods are documented at the level needed by the four implementers to ship without further design calls: input types, output types, error contract (`RedisAdapter.consume` raises on stream-not-found; `QdrantAdapter.search` raises on collection-not-found; `Neo4jAdapter.merge_node` raises on constraint violation; `MinioAdapter.get_object` raises on missing-version), idempotency property (which methods are safe to retry), and tenant-isolation expectation (every method filters on `tenant_id` server-side; no method accepts a "skip tenant filter" flag).
- [ ] **AC-6e** The four sub-issues `002`/`003`/`004`/`005` each reference `006` from their Protocol AC (`AC-1c` → see `006`; `AC-2d` → see `006`; `AC-3e` → see `006`; `AC-4d` → see `006`). The implementers import from `backend.app.storage.protocols`, not from a sibling sub-issue's adapter file. The merge-time check is mechanical: `git grep -nE "from backend\.app\.storage\.(redis|qdrant|neo4j|minio)_adapter import" backend/app/storage/` returns zero hits against `protocols.py`'s consumers (the implementers only `from .protocols import ...`, never from each other).
- [ ] **AC-6f** `mypy --strict` is green on `backend/app/storage/protocols.py`: every Protocol method is fully typed (parameter types, return type, no `Any` leaks); the Protocol classes themselves are `@runtime_checkable` so `isinstance(adapter, RedisAdapter)` works for the M04 wiring code. (M04 may add the runtime check; `006` only ships the declaration.)
- [ ] **AC-6g** The four store-side sub-issues' implementers cannot begin before `006` lands — `006` is the dependency gate, not just a coordination convention. The conductor's PR cycle enforces this: any PR opened by `002`–`005` before `006` has merged is held for rebase onto `006`.

## Contract (the spine)

The four Protocol classes. Method bodies are not in this file — only signatures + docstrings. The order in the docstring below mirrors the order in `protocols.py` so a reader can follow both files in parallel.

```python
# backend/app/storage/protocols.py
# Single source of truth for the M03b storage-adapter interfaces.
# Imported by:
#   - backend/app/storage/redis_adapter.py  (002's implementation)
#   - backend/app/storage/qdrant_adapter.py (003's implementation)
#   - backend/app/storage/neo4j_adapter.py  (004's implementation)
#   - backend/app/storage/minio_adapter.py  (005's implementation)
#   - backend/app/storage/__init__.py        (M04 wiring)
#   - backend/tests/test_storage_adapter_interfaces.py  (AC-6c)
#   - backend/tests/security/test_tenant_isolation_pattern.py  (AC-11 lint)
#
# INVARIANT (cross-cutting, enforced by AC-11):
#   The first positional parameter of every public method is `tenant_id: UUID`.
#   The adapter refuses to construct a query, key, or access check that does
#   not filter on `tenant_id`. This is the M03b equivalent of the M03a
#   `SET LOCAL app.tenant_id` RLS convention.
#   There is no "admin override" parameter; there is no "skip tenant filter"
#   flag. Cross-tenant access is a bug, not a feature.
```

### `RedisAdapter`

| Method | Returns | Tenant-isolation rule | Notes |
|---|---|---|---|
| `publish(tenant_id, stream: str, payload: bytes, *, idempotency_key: str \| None = None) -> str` | `str` (message ID) | Key prefix: `t:{tenant_id}:s:{stream}` | Idempotent on `idempotency_key` (NFR-007). |
| `consume(tenant_id, stream: str, group: str, consumer: str, block_ms: int = 5000) -> list[StreamMessage]` | `list[StreamMessage]` | Reads only from `t:{tenant_id}:s:{stream}` | Auto-claim stale PEL entries on startup. |
| `ack(tenant_id, stream: str, group: str, message_id: str) -> None` | `None` | Confirms tenant before ACK | Cross-tenant ACK raises. |
| `dlq_publish(tenant_id, source_stream: str, original_payload: bytes, reason: str) -> str` | `str` | DLQ key: `t:{tenant_id}:dlq:{source_stream}` | Reason is recorded in payload metadata for replay triage. |
| `reconnect() -> None` | `None` | n/a (transport-level) | Re-establishes the connection pool with exponential backoff. |
| `stream_health(tenant_id) -> StreamHealth` | `StreamHealth` (dataclass) | Reports per-tenant lag, consumer-group state | Used by the M16 health endpoint. |

### `QdrantAdapter`

| Method | Returns | Tenant-isolation rule | Notes |
|---|---|---|---|
| `upsert(tenant_id, points: list[PointStruct]) -> None` | `None` | Every point's `payload["tenant_id"]` MUST equal the parameter; the adapter refuses if not | This is the write-side enforcement. |
| `search(tenant_id, query_vector: list[float], *, top_k: int = 10, filters: dict \| None = None) -> list[ScoredPoint]` | `list[ScoredPoint]` | The adapter **always** appends `must=[FieldCondition(key="tenant_id", match=tenant_id)]` to `filters`; callers cannot override this | Filters are additive — the tenant filter is non-removable. |
| `delete_by_tenant(tenant_id, *, filter: dict \| None = None) -> None` | `None` | Refuses if `filter` would expand scope beyond the tenant | Used by tenant-offboarding (M16). |
| `collection_health() -> CollectionHealth` | `CollectionHealth` | n/a | Reports vector count, segment count, p95 lat. |
| `payload_filter_builder() -> FilterBuilder` | `FilterBuilder` | Helper that exposes `.tenant(tenant_id)` and `.range()`/`.term()` builders; the tenant filter is added in `.build()` and cannot be skipped | Lets M11 build expressive filters without ever touching the underlying Qdrant filter shape. |

### `Neo4jAdapter`

| Method | Returns | Tenant-isolation rule | Notes |
|---|---|---|---|
| `merge_node(tenant_id, label: str, canonical_key: str, props: dict) -> NodeRef` | `NodeRef` | Every `MERGE` clause is preceded by a `tenant_id` predicate; the adapter raises if a node label's constraint would be violated across tenants | FR-041 evidence + confidence are mandatory props. |
| `merge_relationship(tenant_id, from_ref: NodeRef, rel_type: str, to_ref: NodeRef, props: dict) -> RelRef` | `RelRef` | The tenant filter is part of the `MATCH` clause, not the `WHERE` clause — tenants are graph-partitioned, not row-filtered | Same FR-041 enforcement. |
| `find_path(tenant_id, from_ref: NodeRef, to_ref: NodeRef, *, max_depth: int = 6) -> list[Path]` | `list[Path]` | Cross-tenant traversal raises | Used by M11 lineage. |
| `cross_domain_query(tenant_id, cypher: str, params: dict) -> list[Record]` | `list[Record]` | The adapter prepends `WITH {tenant_id: $tenant_id} AS ctx REQUIRE ctx.tenant_id IS NOT NULL` to every read query; the tenant_id param is the first bind | Belt-and-braces; the Cypher itself cannot omit the context. |
| `temporal_query(tenant_id, cypher: str, params: dict, as_of: datetime) -> list[Record]` | `list[Record]` | Same prepend pattern; `as_of` is the second param | Used for time-travel debugging (M11). |
| `graph_health() -> GraphHealth` | `GraphHealth` | n/a | Reports constraint count, index health. |

### `MinioAdapter`

| Method | Returns | Tenant-isolation rule | Notes |
|---|---|---|---|
| `put_object(tenant_id, bucket: BucketName, key: str, data: bytes, *, content_type: str \| None = None) -> ObjectRef` | `ObjectRef` (incl. `version_id`) | Key prefix: `t/{tenant_id}/{key}`; the adapter refuses to write outside this prefix | `saie-reports` write-once is enforced by bucket policy, not by adapter logic — the adapter just writes to the key. |
| `get_object(tenant_id, bucket: BucketName, key: str, *, version_id: str \| None = None) -> bytes` | `bytes` | Refuses if the resolved object is outside the tenant prefix (defense in depth on top of the IAM policy) | `version_id=None` returns latest. |
| `delete_object(tenant_id, bucket: BucketName, key: str, *, version_id: str \| None = None) -> None` | `None` | Refuses cross-tenant delete | Used by GDPR/right-to-erasure (M16). |
| `presigned_url(tenant_id, bucket: BucketName, key: str, *, expires_in: int = 3600) -> str` | `str` | URL is signed with a tenant-scoped policy; cross-tenant GET on the signed URL is denied | Short TTL by default. |
| `bucket_health() -> BucketHealth` | `BucketHealth` | n/a | Reports versioning state, lifecycle-rule state, total object count. |
| `lifecycle_status(tenant_id, bucket: BucketName, key: str) -> LifecycleStatus` | `LifecycleStatus` (dataclass: tier, expires_at, current_version_id) | Used by M16 compliance audit | |

## Cross-cutting properties (locked by the architect)

1. **`tenant_id` is `UUID`** across all four Protocols. The string form `"t:<uuid>"` lives only in the adapter implementations (as the key prefix), not in the public interface.
2. **No method accepts an "admin override" or "skip tenant filter" parameter.** Cross-tenant access is a bug; if a tenant truly needs to see another tenant's data, the fix is a shared tenant ID upstream, not an adapter escape hatch.
3. **Errors are typed, not opaque.** Every method raises either a known `SAIEError` subclass (`TenantIsolationViolation`, `StoreUnavailable`, `ConstraintViolation`, `ObjectNotFound`) or a domain-specific exception; no method raises a bare `Exception` or swallows errors silently.
4. **Idempotency is documented per method.** Methods marked **idempotent** are safe to retry on network failure without producing duplicates; methods marked **non-idempotent** require a caller-side idempotency key.
5. **No store-side cross-tenant joins.** The four adapters do not call each other; cross-store correlation is M11's job via the Postgres `findings` table, not via adapter composition.
6. **`@runtime_checkable`** is set on each Protocol so M04's wiring code can do `isinstance(adapter, RedisAdapter)` defensively at startup.

## Out of Scope

- The four adapter **implementations** — those ship in `002`, `003`, `004`, `005` respectively.
- The M04 wiring code (FastAPI dependency injection of the four adapters; Celery task helpers that wrap them).
- The AC-11 lint test scaffolding — the architect designs the test (`backend/tests/security/test_tenant_isolation_pattern.py`) and the `006` implementer lands it in the same PR. The lint is the *build-time* gate; `006`'s `AC-6c` is the *import-time* gate.
- Any vendor-specific code. The Protocols are vendor-agnostic — the implementers are the vendor-specific layer.

## Tests Required

- **Contract** — `backend/tests/test_storage_adapter_interfaces.py` (AC-6c): import smoke + signature introspection.
- **Security / lint** — `backend/tests/security/test_tenant_isolation_pattern.py` (AC-11): greps every adapter module and `protocols.py` for `tenant_id` as the first parameter; fails the build on regression.
- **Static** — `mypy --strict` is green on `protocols.py` (AC-6f).

## Definition of Done

- [ ] All ACs above checked (`AC-6a` … `AC-6g`).
- [ ] Linked RTM IDs in `docs/16` updated (NFR-013 → In Progress; FR-057 already Done via M03a).
- [ ] `backend/app/storage/protocols.py` committed + `mypy --strict` clean.
- [ ] `backend/tests/test_storage_adapter_interfaces.py` committed + green.
- [ ] `backend/tests/security/test_tenant_isolation_pattern.py` committed + green.
- [ ] Four sub-issues `002`/`003`/`004`/`005` updated to cross-reference `006` from their Protocol AC.
- [ ] Any new CI gotcha pinned in `docs/18 §6`.
- [ ] PR title `feat(data): M03b/M04 storage adapter interfaces (shared Protocols) (NFR-013, FR-057)`.
- [ ] Sub-issue AC ledger flipped at merge-time per `docs/25 §8`.

## Filed by

Orchestrator, 2026-08-13. Sub-issue of epic `001-m03b-storage-substrate`. Filed as the dependency gate for the four store-side sub-issues — explicit exception to the `docs/25 §7` "file after design" default, by conductor judgment call: the Protocol contract is the spine the four implementers import, and locking it in a single source of truth before the four PRs start is the property the lint (`AC-11`) and the M04 import smoke test (`AC-6c`) both depend on.
