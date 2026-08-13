---
gh_issue_number: null
gh_issue_url: null
local_id: 008
type: design
priority: high
area: [backend, data, architecture]
title: "design(data): M03b storage substrate architect design + RED test spec"
module: M03b
rtm_ids: [NFR-013, FR-057, NFR-007, FR-008, FR-038, FR-041, FR-043, NFR-009, NFR-011]
filed: 2026-08-13
filed_by: architect-agent (via orchestrator)
status: open
parent_local_id: 001
sub_issue_local_ids: []
mirror_pending: true
---

# design(data): M03b storage substrate architect design + RED test spec

> Sub-issue of [`001-m03b-storage-substrate`](./001-m03b-storage-substrate.md). Filed by the architect agent on 2026-08-13, after the architect dispatch that returned the design. The implementers (`006`, `002`, `003`, `004`, `005`, `007`) read this file alongside `006` — `006` is the spine (Protocol signatures), this file is the implementation guide (dataclass shapes, error bindings, RED test spec, divergence ledger). Tracker-blocked; mirrors the would-be GitHub Issue body per [`docs/26/README.md`](../26_Open_Issues/README.md).

## Conductor decisions (locked 2026-08-13, post-`006` commit `da6d0c8`)

Three design calls landed after the architect's first pass. All three are baked into `006` (commit `f3add4f`); they are repeated here as callouts so the implementers see them without re-reading `006`.

- **Q1 (a): AC-11 is amended to scope to tenant-scoped methods.** The four cluster-scoped methods (`collection_health`, `payload_filter_builder`, `graph_health`, `bucket_health`) are the explicit exception. They are documented in `006` §Cluster-scoped methods. The AC-11 lint test (`backend/tests/security/test_tenant_isolation_pattern.py`) skips these four.
- **Q2 (a): `RedisAdapter.consume` auto-claim is per-call `XAUTOCLAIM` with 60 s idle threshold.** No `init_consumer_group` method. No M04 startup hook. The 60 s threshold is configurable per consumer-group; default is 60 s.
- **Q3 (P2): `FilterBuilder` is no-arg; `.tenant()` is the required first chained call.** `.range`/`.term`/`.build` without prior `.tenant()` raises `TenantIsolationViolation`. `.build()` always prepends the tenant predicate; caller cannot remove it. Pinned by `backend/tests/integration/test_qdrant_filter_builder.py::test_builder_requires_tenant_first`.

## Severity-2 architect defaults (locked unless the conductor overrides)

- **Q4 HNSW values:** `m=16`, `ef_construct=100`, `ef=128` (Qdrant defaults). Validated by `003`'s `backend/tests/perf/test_qdrant_p95.py`. If the benchmark fails, `003` tunes and re-records.
- **Q5 `MinioAdapter.delete_object` on missing key:** idempotent, returns `None` silently. The M16 tenant-offboarding re-run case is the explicit user.
- **Q6 `StreamMessage` fill sites:** the adapter fills `attempts` (via `XPENDING` on read) and `first_seen_at` (set on first delivery); the M04 consumer fills `last_error` on processing failure before re-acking-or-DLQ-ing.
- **Q7 `Neo4jAdapter.find_path` `max_depth` cap:** 50. `find_path(tenant_a, ..., max_depth=10_000)` raises `ValueError`. Tunable later if M11 lineage needs more.
- **Q8 `FilterBuilder`:** locked at P2 (see Q3 above).
- **Q9 `Record.keys` order:** pinned by the dataclass `frozen=True` + `len(keys) == len(values)` constructor check. No `Mapping` interface.
- **Q10 N=5 poison retry:** conductor default. `002` ships with N=5; raising later is a config change, not a contract change.
- **Q11 `RedisAdapter.publish` `idempotency_key`:** `str | None`; caller-supplied; stored in message metadata; M04 owns dedup.

## (a) Tightening of `006`'s Protocol signatures

### Underspecified return types — concrete shapes

The 14 return types referenced in `006`'s method table but undefined there. They land in `backend/app/storage/types.py` (see (e) for full source). The four implementers import from `types`, never re-declare.

| Return type | Used by | Why it needs a shape now |
|---|---|---|
| `StreamMessage` | `RedisAdapter.consume` | M04 needs `attempts` and `last_error` for DLQ routing; without a typed shape, M04 will dict-peck the message. |
| `StreamHealth` | `RedisAdapter.stream_health` | M16 health endpoint needs `pending_count` / `lag_estimate` as typed fields. |
| `PointStruct` | `QdrantAdapter.upsert` | Vendor-agnostic. The Protocol cannot reference Qdrant's `PointStruct` directly — `006` says the Protocols are vendor-agnostic. |
| `ScoredPoint` | `QdrantAdapter.search` | Same. |
| `CollectionHealth` | `QdrantAdapter.collection_health` | M16 health endpoint. |
| `NodeRef`, `RelRef`, `Path`, `Record` | `Neo4jAdapter.*` | One shape across `merge_node` / `merge_relationship` / `find_path` / `cross_domain_query`. |
| `BucketHealth` | `MinioAdapter.bucket_health` | M16 health endpoint. |
| `LifecycleStatus` | `MinioAdapter.lifecycle_status` | M16 compliance audit. |
| `FilterBuilder` | `QdrantAdapter.payload_filter_builder` | Builder shape with `.tenant(tenant_id) -> FilterBuilder`, `.range(field, *, gte, lte) -> FilterBuilder`, `.term(field, value) -> FilterBuilder`, `.build() -> Any` (Qdrant `Filter`; vendor-agnostic at the Protocol surface). `.tenant()` is the required first call (Q3 P2). |

### Ambiguous error contracts — binding

`006` says "errors are typed" and lists `TenantIsolationViolation`, `StoreUnavailable`, `ConstraintViolation`, `ObjectNotFound`. The method table doesn't bind error types to failure modes. The binding:

| Method | Failure mode | Raise |
|---|---|---|
| `RedisAdapter.publish` | stream write fails (Redis down) | `StoreUnavailable` |
| `RedisAdapter.publish` | `idempotency_key` collision on different payload | `ConstraintViolation` |
| `RedisAdapter.consume` | stream not found | `StoreUnavailable` (the stream is a provisioned resource; missing means bootstrap is broken) |
| `RedisAdapter.ack` | cross-tenant ACK | `TenantIsolationViolation` |
| `RedisAdapter.ack` | `message_id` not in PEL | `ObjectNotFound` |
| `QdrantAdapter.upsert` | `payload["tenant_id"] != tenant_id` parameter | `TenantIsolationViolation` (NOT `ConstraintViolation` — failure is a cross-tenant write attempt) |
| `QdrantAdapter.upsert` | Qdrant write fails | `StoreUnavailable` |
| `QdrantAdapter.search` | collection not found | `StoreUnavailable` |
| `QdrantAdapter.delete_by_tenant` | `filter` would expand scope beyond tenant | `TenantIsolationViolation` |
| `Neo4jAdapter.merge_node` | uniqueness-constraint violation | `ConstraintViolation` |
| `Neo4jAdapter.merge_node` | missing FR-041 `evidence_id` or `confidence` in `props` | `ConstraintViolation` (the constraint is a schema-level existence constraint, FR-041) |
| `Neo4jAdapter.find_path` | cross-tenant traversal | `TenantIsolationViolation` |
| `Neo4jAdapter.cross_domain_query` | caller's Cypher shadows `tenant_id` | `TenantIsolationViolation` (see divergence (iii)) |
| `MinioAdapter.put_object` | write to `saie-reports` on existing key (write-once) | `ConstraintViolation` |
| `MinioAdapter.get_object` | resolved key outside `t/{tenant_id}/` prefix | `TenantIsolationViolation` |
| `MinioAdapter.get_object` | object/version not found | `ObjectNotFound` |
| `MinioAdapter.delete_object` | resolved key outside `t/{tenant_id}/` prefix | `TenantIsolationViolation` |
| `MinioAdapter.delete_object` | key not found inside tenant prefix | `None` (idempotent; see Q5) |
| `MinioAdapter.presigned_url` | URL signing fails | `StoreUnavailable` |

### Cross-Protocol inconsistencies and gaps (post-Q1 resolution)

The four cluster-scoped exceptions to AC-11 are documented in `006` §Cluster-scoped methods. Other gaps:

1. **`RedisAdapter.consume` "auto-claim stale PEL entries on startup"** — resolved at Q2 (a) (per-call `XAUTOCLAIM`, 60 s idle, no startup hook).
2. **`QdrantAdapter.delete_by_tenant` `filter` foot-gun** — the Protocol signature accepts `filter: dict | None = None`; the implementation must validate the caller's filter is a subset (every `must` clause is an additional constraint, never a tenant-narrowing one). Integration test: divergence (ii).
3. **`MinioAdapter.lifecycle_status` key prefix double-prefixing** — the method must reject a `key` that already starts with `t/`. Integration test: divergence (viii).
4. **No async signatures** — `006` writes `def`, not `async def`. Recommendation: keep Protocols sync; implementers may wrap sync calls in `asyncio.to_thread` or expose async shims. M04 concern, not `006` concern.

## (b) RED test spec for AC-6c — `backend/tests/test_storage_adapter_interfaces.py`

**File path:** `backend/tests/test_storage_adapter_interfaces.py`.

**Why this is RED today:** the file imports `from backend.app.storage.protocols import RedisAdapter, QdrantAdapter, Neo4jAdapter, MinioAdapter`, and that module does not exist. `ModuleNotFoundError` on collection. GREEN the moment the `006` implementer lands `protocols.py`.

**Imports:**
```python
from __future__ import annotations
import inspect
from typing import get_type_hints
from uuid import UUID

import pytest

from backend.app.storage.protocols import (
    RedisAdapter, QdrantAdapter, Neo4jAdapter, MinioAdapter,
)
from backend.app.storage import types as storage_types
```

**Test functions (20 total):**

1. `test_protocols_module_imports` — the import block is the test. Body: `assert RedisAdapter is not None` (and other three).
2. `test_storage_types_module_imports_and_exposes_documented_names` — pins the 13 names in `types.py`.
3. `test_redis_adapter_exposes_expected_methods` — `for name in ("publish", "consume", "ack", "dlq_publish", "reconnect", "stream_health"): assert hasattr(RedisAdapter, name)`.
4. `test_qdrant_adapter_exposes_expected_methods` — same shape for `("upsert", "search", "delete_by_tenant", "collection_health", "payload_filter_builder")`.
5. `test_neo4j_adapter_exposes_expected_methods` — `("merge_node", "merge_relationship", "find_path", "cross_domain_query", "temporal_query", "graph_health")`.
6. `test_minio_adapter_exposes_expected_methods` — `("put_object", "get_object", "delete_object", "presigned_url", "bucket_health", "lifecycle_status")`.
7-10. `test_*_adapter_tenant_id_is_first_param_of_tenant_scoped_methods` — per-Protocol signature introspection; uses `inspect.signature(method).parameters[0] == "tenant_id"` and `get_type_hints` to assert annotation is `UUID`. Tenant-scoped sets (per Q1 resolution): Redis = all except `reconnect`; Qdrant = `upsert`, `search`, `delete_by_tenant`; Neo4j = all except `graph_health`; Minio = all except `bucket_health`.
11. `test_protocols_are_runtime_checkable` — `for proto in (RedisAdapter, QdrantAdapter, Neo4jAdapter, MinioAdapter): assert getattr(proto, "_is_runtime_protocol", False) is True`.
12-15. `test_dummy_*_conformer_passes_isinstance` — define a `Dummy*` class implementing every tenant-scoped method; assert `isinstance(Dummy*(), *Adapter) is True`. Proves both `@runtime_checkable` AND the structural shape M04 checks at startup.
16. `test_no_admin_override_or_skip_tenant_param_anywhere` — denylist `{"admin", "admin_override", "skip_tenant", "skip_tenant_filter", "bypass_tenant", "as_admin", "force", "override", "internal", "system"}` (case-insensitive) across all tenant-scoped methods.
17. `test_payload_filter_builder_protocol_shape` — assert `storage_types.FilterBuilder` is a `Protocol` with `.tenant`, `.range`, `.term`, `.build` methods; each chainable method returns `FilterBuilder`.
18. `test_mypy_strict_compatible_signatures` — `get_type_hints(include_extras=True)` on every tenant-scoped method; assert no `Any` leaks. AC-6f safety net without invoking mypy.
19. `test_cross_adapter_import_discipline` — AST walk on `backend/app/storage/`; assert no `*_adapter.py` imports from a sibling `*_adapter`. Pins AC-6e.
20. `test_docstrings_state_idempotency_for_every_tenant_scoped_method` — assert each docstring contains `idempotent` or `non-idempotent`. Pins cross-cutting property #4.

Total runtime: sub-second. No live infrastructure.

## (c) RED test spec for AC-11 — `backend/tests/security/test_tenant_isolation_pattern.py`

**File path:** `backend/tests/security/test_tenant_isolation_pattern.py`.

**Approach:** hybrid (Protocol signature introspection + AST walk on implementation modules). Three approaches considered:
- AST walk only: catches every `def` in adapter files, but misses Protocol drift if the Protocol is wrong.
- `inspect.signature` on the Protocol only: pins the contract, but a conformant adapter can add a non-conformant method the lint doesn't see.
- String grep: fragile, false positives on docstrings.
- Hybrid wins.

**Wiring:** pytest collection, not a separate CI step. The test must run in the same job as the unit tests; if anyone proposes moving security tests to a separate job with a separate gate, that is a regression — flag it.

**Imports:**
```python
from __future__ import annotations
import ast, inspect
from uuid import UUID
import pytest
from backend.app.storage.protocols import (
    RedisAdapter, QdrantAdapter, Neo4jAdapter, MinioAdapter,
)
```

**Test functions (15 total):**

1-4. `test_*_protocol_tenant_id_first_on_every_tenant_scoped_method` — per-Protocol `inspect.signature` check; uses `_format_error` (below) for actionable failure output. Excludes the cluster-scoped set per Q1.
5. `test_tenant_id_param_is_typed_as_uuid` — `get_type_hints(method, localns={"UUID": UUID})["tenant_id"]` resolves to `UUID`. Handles `from __future__ import annotations`.
6. `test_no_admin_override_or_skip_tenant_param_on_any_protocol` — denylist scan.
7-10. `test_*_adapter_implementation_conforms_to_protocol` — load each `*AdapterImpl`; for every public method (not `_`-prefixed), assert first param is `tenant_id`. This is the per-implementation lint.
11-14. `test_no_*_adapter_module_defines_public_method_without_tenant_id` — AST walk on each `*_adapter.py`; for every `FunctionDef` whose name is in the public API, assert `args.args[0].arg == "tenant_id"`. Catches a future escape-hatch method added outside the Protocol.
15. `test_no_cross_adapter_imports` — AST walk on every `*_adapter.py`; assert no `ImportFrom` node's `module` value matches `backend.app.storage.{redis,qdrant,neo4j,minio}_adapter`. Pins AC-6e at the import-graph level.

**`_format_error` helper:**
```python
def _format_error(proto_name, method_name, params):
    return (
        f"TenantIsolationViolation: {proto_name}.{method_name} is missing or "
        f"has 'tenant_id' in the wrong position. First parameter must be "
        f"'tenant_id: UUID' (AC-11, FR-057). Got: {params!r}. "
        f"See docs/26_Open_Issues/006-m03b-storage-adapter-interfaces.md."
    )
```

The file is RED today for the same reason as (b): `backend.app.storage.protocols` does not exist.

## (d) Lintable vs. non-lintable properties

| Property | Lintable? | Test location |
|---|---|---|
| First param is `tenant_id` | YES | (c) #1–4 |
| `tenant_id` typed as `UUID` | YES | (c) #5 |
| No `admin_override` param | YES | (c) #6 |
| `@runtime_checkable` | YES | (b) #11 |
| Idempotency documented | YES (weak, docstring token) | (b) #20 |
| No cross-adapter imports | YES (AST) | (c) #15 |
| FR-041 evidence+confidence on every Neo4j write | NO (runtime property of `props` dict) | (f) #vii integration test |
| `payload_filter_builder().tenant()` non-removable | NO (runtime property of builder chain) | (f) #vi integration test |
| `QdrantAdapter.search` appends tenant filter non-overridably | NO (merge-order property) | (f) #ii integration test |
| `Neo4jAdapter.cross_domain_query` rejects Cypher shadowing `tenant_id` | NO (requires parsing Cypher) | (f) #iii integration test |
| `MinioAdapter.presigned_url` is tenant-bound | NO (requires HTTP integration) | (f) #iv integration test |
| `RedisAdapter.ack` raises `TenantIsolationViolation` on cross-tenant ACK | NO (requires live Redis) | `tests/integration/test_redis_streams_roundtrip.py` |

**The lint is necessary but not sufficient.** The integration tests in (f) are the second line of defense.

## (e) `backend/app/storage/types.py` — full source

The `006` implementer materializes this file verbatim.

```python
"""Shared types for the M03b storage adapters.

Imported by:
  - backend/app/storage/protocols.py       (Protocol annotations)
  - backend/app/storage/redis_adapter.py   (002)
  - backend/app/storage/qdrant_adapter.py  (003)
  - backend/app/storage/neo4j_adapter.py   (004)
  - backend/app/storage/minio_adapter.py   (005)
  - backend/app/storage/__init__.py        (M04 wiring)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


# ---- Redis ----

@dataclass(frozen=True)
class StreamMessage:
    message_id: str
    stream: str
    payload: bytes
    idempotency_key: str | None
    attempts: int = 0
    first_seen_at: datetime | None = None
    last_error: str | None = None


@dataclass(frozen=True)
class StreamHealth:
    stream: str
    pending_count: int
    delivered_count: int
    consumer_count: int
    last_delivered_id: str | None
    lag_estimate: int | None = None


# ---- Qdrant ----

@dataclass(frozen=True)
class PointStruct:
    id: str
    vector: list[float]
    payload: dict[str, Any]  # MUST include tenant_id (keyword); validated at upsert


@dataclass(frozen=True)
class ScoredPoint:
    id: str
    score: float
    payload: dict[str, Any]


@dataclass(frozen=True)
class CollectionHealth:
    collection: str
    vector_count: int
    segment_count: int
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    p99_latency_ms: float | None
    hnsw_m: int
    hnsw_ef_construct: int
    hnsw_ef: int


class FilterBuilder(Protocol):
    """Locked at Q3 (P2): no-arg builder; .tenant() is the required first call.
    .range/.term/.build without prior .tenant() raises TenantIsolationViolation."""
    def tenant(self, tenant_id: UUID) -> FilterBuilder: ...
    def range(self, field: str, *, gte: float | None = None, lte: float | None = None) -> FilterBuilder: ...
    def term(self, field: str, value: Any) -> FilterBuilder: ...
    def build(self) -> Any: ...


# ---- Neo4j ----

@dataclass(frozen=True)
class NodeRef:
    label: str
    canonical_key: str
    internal_id: int | None = None


@dataclass(frozen=True)
class RelRef:
    rel_type: str
    from_ref: NodeRef
    to_ref: NodeRef
    internal_id: int | None = None
    props: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Path:
    nodes: list[NodeRef]
    rels: list[RelRef]


@dataclass(frozen=True)
class Record:
    keys: list[str]
    values: list[Any]


# ---- MinIO ----

@dataclass(frozen=True)
class BucketHealth:
    bucket: str
    versioning_state: str  # "Enabled" | "Suspended" | "Disabled"
    object_count: int
    total_bytes: int
    lifecycle_rule_count: int
    lifecycle_rules_synced: bool


@dataclass(frozen=True)
class LifecycleStatus:
    bucket: str
    key: str  # the tenant-scoped key (includes t/{tenant_id}/ prefix)
    current_tier: str  # "hot" | "warm" | "cold" | "expired"
    current_version_id: str | None
    expires_at: datetime | None
    rule_id: str | None


@dataclass(frozen=True)
class ObjectRef:
    bucket: str
    key: str
    version_id: str | None
    etag: str | None
    size_bytes: int | None
```

### HNSW values (Q4, locked)

`m=16`, `ef_construct=100`, `ef=128` (Qdrant defaults). Validated by `backend/tests/perf/test_qdrant_p95.py`. 10 k vectors at the OpenAI `text-embedding-3-small` dim (1536) is ~60 MB of vector data; HNSW overhead at `m=16` is ~30 % — total ~80 MB, fits in 4 GB RAM. For `top_k=10` at 10 k vectors, p95 should be 100–500 ms on 2 vCPU. The values are recorded in `infra/qdrant/config.yaml` with the benchmark date so they can be re-validated on infra changes.

## (f) Implementation-divergence ledger

The lint is necessary but not sufficient. Each row names a divergence the lint cannot catch, the file + test name that catches it, and the assertion.

| # | Divergence risk | Lint gap | Integration test |
|---|---|---|---|
| (i) | `RedisAdapter.publish` accepts `tenant_id` but ignores it in the Redis key (writes to `s:{stream}` not `t:{tenant_id}:s:{stream}`) | Lint only checks signature | `test_redis_streams_roundtrip.py::test_publish_key_includes_tenant_id` — assert key is `t:{tenant_a}:s:saie.crawl` |
| (ii) | `QdrantAdapter.search` appends tenant filter to caller's filter, but caller's filter overrides via `must=[{key: tenant_id, match: tenant_b}]` | Merge order not in signature | `test_qdrant_collection.py::test_search_caller_filter_cannot_override_tenant` — assert result set is zero (or call raises) |
| (iii) | `Neo4jAdapter.cross_domain_query` prepends `WITH {tenant_id: $tenant_id}` but caller's Cypher shadows `tenant_id` | Lint cannot parse Cypher | `test_neo4j_constraints.py::test_cross_domain_query_rejects_cypher_that_shadows_tenant_id` |
| (iv) | `MinioAdapter.presigned_url` signs URL with right bucket+key but IAM principal is global | Signature not provable from inspection | `test_minio_lifecycle.py::test_presigned_url_tenant_bound` — rewrite path to other tenant; must 403 |
| (v) | `RedisAdapter.consume` does `XREADGROUP` without `XAUTOCLAIM`; "auto-claim on startup" is unimplemented | Lint only checks method exists | `test_redis_streams_roundtrip.py::test_consume_auto_claims_stale_pel_entries` — set idle < 60 s, call consume, assert stale entry delivered |
| (vi) | `QdrantAdapter.payload_filter_builder` allows `.build()` without `.tenant()` — tenant filter omitted silently | Builder chain state not parseable | `test_qdrant_filter_builder.py::test_builder_requires_tenant_first` (Q3 P2 pinned) |
| (vii) | `Neo4jAdapter.merge_node` accepts `props: dict` without FR-041 enforcement | Runtime property of body | `test_neo4j_constraints.py::test_merge_node_requires_evidence_id_and_confidence` |
| (viii) | `MinioAdapter.get_object` accepts path-traversal `../t/{tenant_b}/k` | Lint only checks signature | `test_minio_lifecycle.py::test_get_object_rejects_path_traversal` |
| (ix) | `RedisAdapter.dlq_publish` ignores `tenant_id` (same shape as (i), DLQ path) | Same as (i) | `test_redis_streams_roundtrip.py::test_dlq_publish_key_includes_tenant_id` |
| (x) | `Neo4jAdapter.find_path` with `max_depth=10_000` runs unbounded | Lint cannot prove runtime cap | `test_neo4j_constraints.py::test_find_path_caps_max_depth` — must raise `ValueError` |
| (xi) | `QdrantAdapter.upsert` detects tenant_id mismatch and silently rewrites (instead of raising) | Raise-vs-rewrite is runtime | `test_qdrant_collection.py::test_upsert_rejects_tenant_id_mismatch` — must raise `TenantIsolationViolation` |

The four implementers (`002`, `003`, `004`, `005`) are responsible for materializing the integration tests for their store-side rows in the same PR as the adapter implementation.

## (g) Sequencing recommendation

The order that minimizes rework:

1. **`008` (this design) lands as doc-only.** Provides the dataclass shapes, the FilterBuilder contract (Q3 P2), the cluster-method exception list (Q1), the divergence ledger. Already done at this commit.
2. **`006` lands.** `backend/app/storage/protocols.py`, `backend/app/storage/types.py`, `backend/tests/test_storage_adapter_interfaces.py`, `backend/tests/security/test_tenant_isolation_pattern.py`. The 35 AC-6c + AC-11 tests go GREEN here.
3. **`002`, `003`, `004`, `005` land in parallel after `006` merges.** No cross-dependencies; merge in any order. The four implementers materialize the divergence-ledger integration tests from (f) for their respective rows.
4. **`007` (provisioner CLI) lands after the four store-side PRs.** Ties the four bootstrap scripts into `saie.bootstrap`. Ships the AC-1 cross-cutting integration test (provisioner idempotency on clean + post-bootstrap state).
5. **`001` (epic close).** All 11 ACs checked; module exit gate per `docs/22 §6` green.

**Why not parallel `002`–`005` with `006`?** `006` is the dependency gate. If `006` changes after the four implementers start (likely, as Q1–Q3 are resolved), the four PRs need to rebase. Sequential `006` → four parallel is cheaper than 4× rebase.

## (h) Open questions

Resolved: Q1, Q2, Q3 (Severity-1; locked by conductor).
Locked at architect defaults: Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q11 (Severity-2; conductor can override before any of `002`–`005` merge).

## Hand-off note

- **`006` (Protocols + types + RED tests):** `backend-expert`. Reads `006` (now amended at commit `f3add4f`) and this `008`. Materializes `protocols.py`, `types.py`, the two test files verbatim.
- **`002`–`005` (implementations):** `backend-expert` per store. Each reads `006` and this `008`. Each ships the adapter implementation + the store-side bootstrap + the integration tests (their AC + the relevant divergence-ledger rows from (f)).
- **`007` (provisioner CLI):** new sub-issue (filed by orchestrator at task #16). `backend-expert` after `002`–`005` merge.
- **No production code, no test files, no `.py` files were written by the architect.** The design credit is the architect's; the implementation credit is the implementer's.

## Filed by

Architect agent (via orchestrator, wizard run, 2026-08-13) on behalf of the conductor, after the conductor's three locked decisions (Q1 a, Q2 a, Q3 P2). Sub-issue of epic `001-m03b-storage-substrate`. Pairs with `006` (the spine) as the implementation guide for `006`, `002`, `003`, `004`, `005`, `007`.
