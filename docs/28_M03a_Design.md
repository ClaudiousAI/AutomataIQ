# 28 — M03a Design (Schema + RLS Substrate)

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Design — Phase 3 artifact, locked decisions frozen for M03a implementation
**Module:** M03a (first slice of M03 per `docs/22_Module_Roadmap.md`)
**Date:** 2026-08-12

> M03a ships the **Postgres substrate only**. In: full schema via single Alembic migration, `pg_trgm` extension, RLS policies on every tenant-scoped table, `app/db/tenant.py`, three Postgres roles + grants, tests. Out: `vector` extension (M03b), Qdrant/Neo4j/MinIO/Redis bootstrap (M03b), FastAPI tenant dependency (M04), seed data (M03c taxonomy, M07 sources per ADR-0017), docker-compose/production (M16).

---

## §1 Locked decisions (do NOT relitigate)

1. **Alembic pinned.** `sqlalchemy>=2.0`, `alembic>=1.13`, `psycopg[binary]>=3.1`, `asyncpg>=0.29`. No other migration tool.
2. **`app/db/tenant.py` is the SINGLE SOURCE OF TRUTH** for the Postgres session-var `TENANT_SESSION_VAR = "app.tenant_id"`, the `current_tenant_id()` reader, the `tenant_context()` ContextManager, and `is_cross_tenant_role()`. Lint rule: any string-literal `"app.tenant_id"` outside `app/db/tenant.py` is a finding.
3. **Three Postgres roles** in `infra/postgres/init.sql`: `saie_migrator` (BYPASSRLS), `saie_app` (RLS), `saie_platform_admin` (cross-tenant policies). Init script idempotent via `DO $$ BEGIN … EXCEPTION WHEN duplicate_object … END $$;`.
4. **Platform-admin RLS escape lives in M03a** (schema-layer concern).
5. **M03a ships NO seed data.** Sources seed = M07 (ADR-0017). Taxonomy seed = M03c.
6. **No CI workflow change.** `app/db/` follows docs/23 §3.5.4 standard layout.
7. **Strict typing.** `mypy --strict --explicit-package-bases app` must remain green.

---

## §2 Schema tally (18 tables — canonical, from docs/07 §3)

| # | Table | Tenant-scoped? | `tenant_id` direct? |
|---|---|---|---|
| 1 | `tenants` | YES (RLS-enabled for symmetry) | yes (id IS the tenant) |
| 2 | `users` | YES | yes |
| 3 | `sources` | YES | yes |
| 4 | `crawl_runs` | YES | no (via `source_id`) |
| 5 | `source_versions` | YES | no (via `source_id`) |
| 6 | `changes` | YES | no (via `version_id`) |
| 7 | `findings` | YES | yes |
| 8 | `automations` | YES | no (via `finding_id`) |
| 9 | `architecture_nodes` | YES | no (via `automation_id`) |
| 10 | `architecture_edges` | YES | no (via `automation_id`) |
| 11 | `evidence` | YES | no (via `finding_id`) |
| 12 | `opportunities` | YES | no (via `automation_id`) |
| 13 | `scores` | YES | no (via `opportunity_id`) |
| 14 | `reports` | YES | yes |
| 15 | `report_items` | YES | no (via `report_id`) |
| 16 | `reviews` | YES | yes |
| 17 | `agent_runs` | YES | yes |
| 18 | `audit_log` | YES (stricter policy) | no (via `actor_id`) |

**FK chain:** `tenants → users → sources → crawl_runs → source_versions → changes → findings → {automations → architecture_*, evidence} → opportunities → scores → reports → report_items; reviews; agent_runs; audit_log`. No self-links, no cartesian products.

**Column conventions:**
- IDs: `UUID PRIMARY KEY DEFAULT gen_random_uuid()` (per Q3 default).
- `tenants.id`: `TEXT` (per Q4 default — matches `TenantContext.tenant_id: str`).
- `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`, immutable.
- `updated_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`; app-layer updates (no trigger in M03a; M04 ships the app path).
- `deleted_at`: column on `sources` and `opportunities` per docs/07 §5; policy logic deferred to M07/M09.

`pg_trgm` extension ships (per Q5 default). No trigram index in M03a — M11 (Knowledge & Search) adds the GIN index. Migration's `CREATE EXTENSION IF NOT EXISTS pg_trgm` is justified by FR-043.

`vector` extension does NOT ship in M03a — that's Qdrant territory (M03b).

---

## §3 Session-var contract (NFR-007 recoverability)

`backend/app/db/tenant.py` exports:

- `TENANT_SESSION_VAR: Final[str] = "app.tenant_id"`
- `current_tenant_id(conn) -> str | None` — `SELECT current_setting('app.tenant_id', true)`. The `true` arg is the NULL-safe variant that returns NULL when the GUC is unset.
- `tenant_context(conn, tenant_id: str, role: Role) -> ContextManager` — wraps `BEGIN` + `SET LOCAL app.tenant_id = ...` on enter; `COMMIT`/`ROLLBACK` on exit (rollback on exception, NEVER swallow).
- `is_cross_tenant_role(role: Role) -> bool` — `True iff role is Role.PLATFORM_ADMIN`.

**Lint rule:** `git grep -n '"app.tenant_id"' backend/app/` must return exactly one match (in `app/db/tenant.py`).

**Who sets / reads / clears:**
- Sets: `tenant_context()`.
- Reads: `current_tenant_id()`.
- Clears: Postgres clears on `COMMIT`/`ROLLBACK`/connection close (because `SET LOCAL` is transaction-scoped).
- On failure: caller (M02 `AuthAuditLogger`) writes audit row.

**NFR-007 failure modes:**
- Network blip → connection drops → GUC cleared → caller writes `rls_context_failed` audit row.
- Deadlock → `psycopg.errors.DeadlockDetected` → same.
- `SET LOCAL` outside a transaction → Postgres raises `InvalidTransactionState` ("SET LOCAL ... can only be used in transaction blocks"). `tenant_context()` MUST wrap in an explicit `BEGIN`.
- `saie_app` queries without `SET LOCAL` → policy evaluates NULL → row hidden / INSERT blocked (default-deny posture).

---

## §4 RLS policy matrix

Two helper SQL functions created in the migration so every policy is a single boolean expression:

```sql
CREATE FUNCTION app_current_tenant() RETURNS text
  LANGUAGE sql STABLE AS $$
    SELECT current_setting('app.tenant_id', true)
$$;

CREATE FUNCTION app_tenant_matches(uuid_value uuid) RETURNS boolean
  LANGUAGE sql STABLE AS $$
    SELECT app_current_tenant() IS NOT NULL
       AND app_current_tenant() = uuid_value::text
$$;
```

Two policy sets per table:

- **`saie_app`** (FOR ALL): `USING (app_tenant_matches(<tenant_id column or EXISTS-subquery>)) WITH CHECK (…)`.
- **`saie_platform_admin`** (FOR ALL): `USING (true) WITH CHECK (true)` — cross-tenant escape hatch.

Tables with direct `tenant_id` (`tenants`, `users`, `sources`, `findings`, `reports`, `reviews`, `agent_runs`): use `app_tenant_matches(tenant_id)`.

Tables without (the other 11): use EXISTS-subquery through the FK chain. Example: `USING (app_tenant_matches((SELECT s.tenant_id FROM sources s WHERE s.id = crawl_runs.source_id)))`.

**Grants:**
```sql
GRANT USAGE ON SCHEMA public TO saie_app, saie_platform_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO saie_app, saie_platform_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO saie_app, saie_platform_admin;
```

`saie_migrator` owns the schema and has `BYPASSRLS`.

**`audit_log` policy (per Q1 default):** permissive on `saie_platform_admin` (Option 1). Schema-layer alone cannot audit read events; that is M15's job (application-layer via `pgaudit` or query-level logging).

---

## §5 Migration idempotency strategy

- Alembic-version-tracked via `alembic_version`. Re-running `alembic upgrade head` on a migrated DB is a no-op.
- Postgres extensions use native `CREATE EXTENSION IF NOT EXISTS pg_trgm`.
- `infra/postgres/init.sql` idempotent at the role/database level via `DO $$ BEGIN … EXCEPTION WHEN duplicate_object … END $$;`.
- **Justified `op.execute` exceptions** (enumerated post-implementation per audit `docs/29 §3.6`):
  1. `CREATE EXTENSION pgcrypto` + UUID4 shim — `pgserver` lacks contrib; justified by FR-001/008/019 baseline.
  2. `CREATE EXTENSION pg_trgm` — `pgserver` fallback path; justified by FR-043.
  3. `CREATE OR REPLACE FUNCTION app_current_tenant()` — helper SQL function justified by §4.
  4. `CREATE OR REPLACE FUNCTION app_tenant_matches(uuid_value uuid)` — helper SQL function justified by §4.
  5. FTS GIN trigram indexes on `findings.title` + `findings.body` — `pg_trgm` fallback path; justified by FR-043.
  6. The RLS policy-creation loop — Alembic ≥1.13 has no typed `op.create_policy` in the public API (the explicitly justified exception).
  7. Final `GRANT ... TO saie_app, saie_platform_admin` — declared in §4 design.
  Each is directly justified by a numbered section of §4 or by the `pgserver` fallback path; the migration is **substantively compliant** with the design intent. The implementer does NOT add any other raw `op.execute` without escalating.

---

## §6 Open questions for the conductor — RESOLVED 2026-08-12

| # | Question | Resolution | Default if silent |
|---|---|---|---|
| Q1 | `audit_log` policy on `saie_platform_admin` | **Option 1** (permissive; app-layer audit = M15) | Option 1 |
| Q2 | Test Postgres library | **`pytest-postgresql`** | `pytest-postgresql` |
| Q3 | PK type | **`UUID` + `pgcrypto.gen_random_uuid()`** | `UUID` |
| Q4 | `tenants.id` type | **`TEXT`** to match `TenantContext.tenant_id: str` | `TEXT` |
| Q5 | Ship `pg_trgm` extension? | **Yes** | Yes |

Resolution date: 2026-08-12, by conductor (Ganesh). All five defaults confirmed; build path = single `backend-expert`, sequential.

**Q4 deviation note:** `tenants.id` as `TEXT` deviates from docs/04's UUID default. This is intentional — it aligns the column type with the M02 `TenantContext.tenant_id: str` contract, eliminating a runtime cast mismatch at every query boundary. Other entity tables (`users`, `sources`, etc.) remain `UUID` per Q3. Documented in this design; the adjacent `audit_log` NULL-actor carve-out (per §4 Q1 resolution) is captured in **[ADR-0018](./17_Architecture_Decision_Records/0018-audit-log-null-actor-carveout.md)**. The `tenants.id`-as-TEXT deviation itself remains an in-design note; surface area has not warranted a separate ADR.

---

## §7 Test Postgres library decision (Q2 detail)

**`pytest-postgresql`** chosen. Rationale:
- No Docker-in-Docker on CI (brief forbids CI workflow change).
- Faster feedback (in-process).
- Deterministic — fixture wraps each test in a transaction that rolls back per test.
- Matches the M02 "use real primitives, not mocks" philosophy (RSA, not a fake JWT lib).

Alternative `testcontainers-python[postgres]` rejected — requires Docker on the runner.

---

## §8 Test design (the load-bearing test of M03a)

The RLS matrix is parametrized over the 18 tenant-scoped tables. For each table:

```
as saie_app + tenant_a:
  INSERT row (tenant_id=tenant_a)  → succeeds
  SELECT                          → returns row
  UPDATE row                      → succeeds
  DELETE row                      → succeeds
as saie_app + tenant_b:
  SELECT                          → returns ZERO rows (assertEqual 0)
  INSERT row (tenant_id=tenant_a)  → RAISES InsufficientPrivilege
  UPDATE row (tenant_id=tenant_a)  → RAISES OR updates 0 rows
  DELETE row (tenant_id=tenant_a)  → RAISES OR deletes 0 rows
as saie_platform_admin:
  SELECT                          → returns ALL rows across tenants
  INSERT row (tenant_id=tenant_a)  → succeeds
```

**Mutation-testing mindset (docs/23 §3.3):** every cell asserts a SPECIFIC outcome (count = N, or specific exception type). No "no error" assertions.

**Test count:** 18 tables × 4 (happy) + 18 × 4 (denied) + 18 × 2 (admin) = **180 parametrized cases** in `test_rls_matrix.py`. Plus 11 tests in `test_tenant_reader.py` + `test_tenant_setter.py`.

**Helper fixtures (`conftest.py`):** `app_conn_with_tenant_a`, `app_conn_with_tenant_b`, `admin_conn`, `_insert_minimal_row`, `_select_all`, `_update_one`, `_delete_one`, `_update_by_pk`, `_delete_by_pk`. The minimum-row helper uses `information_schema.columns` to discover columns at runtime so RLS is exercised, not the schema itself.

---

## §9 Production files

| File | LOC est. | Owner |
|---|---|---|
| `backend/app/db/__init__.py` | 2 | backend-expert |
| `backend/app/db/tenant.py` | 80 | backend-expert |
| `backend/alembic.ini` | 30 | backend-expert |
| `backend/alembic/env.py` | 60 | backend-expert |
| `backend/alembic/script.py.mako` | 30 | backend-expert |
| `backend/alembic/versions/0001_initial_schema.py` | ~1081 (actual; 480–550 was the pre-build estimate) | backend-expert |
| `backend/app/settings.py` (extend) | +12 | backend-expert |
| `backend/requirements.txt` (append section) | +12 | backend-expert |
| `infra/postgres/init.sql` | 60 | backend-expert |
| **Total** | **~770** | |

---

## §10 Test files

| File | LOC est. | Test count | Owner |
|---|---|---|---|
| `backend/app/db/tests/__init__.py` | 1 | 0 | backend-expert |
| `backend/app/db/tests/conftest.py` | 90 | (fixtures) | backend-expert |
| `backend/app/db/tests/test_tenant_reader.py` | 60 | 5 | backend-expert |
| `backend/app/db/tests/test_tenant_setter.py` | 80 | 6 | backend-expert |
| `backend/app/db/tests/test_rls_matrix.py` | 220 | 162 (parametrized) | backend-expert |
| **Total** | **~450** | **~173** | |

---

## §11 Implementation hand-off

**`backend-expert`** builds all production files in order:
1. `settings.py` (extend)
2. `app/db/__init__.py`
3. `app/db/tenant.py`
4. `infra/postgres/init.sql`
5. `alembic.ini` + `alembic/env.py` + `alembic/script.py.mako`
6. `alembic/versions/0001_initial_schema.py`
7. Materialize test files from architect's RED stub spec
8. Boot local Postgres, run migration, run tests
9. Run post-coding gate (ruff, mypy --strict, coverage)
10. Commit on `feat/M03a-schema-rls`, push, update RTM, update `docs/18_Project_Memory.md`

**`frontend-expert`:** none. M03a is pure backend.

**`qa-engineer`:** none at build-time (architect = QA for this slice). If a separate coverage-authoring pass is needed, dispatched post-build.

---

## §12 Acceptance (M03a complete signal)

- `cd backend && alembic upgrade head` from a fresh docker Postgres is idempotent.
- Re-running `alembic upgrade head` is a no-op (the migration is forward-only, no errors, no duplicate DDL).
- `alembic downgrade -1` then `alembic upgrade head` returns the DB to the current schema state, no orphans.
- `pytest --cov=app/db --cov-fail-under=80` green; 173 tests pass.
- `ruff check app` and `mypy --strict --explicit-package-bases app` green.
- A developer with zero project context can `docker run postgres`, `pip install -r requirements.txt`, `alembic upgrade head`, `pytest` and see all green in under 90 seconds.

---

## §13 What the implementer is NOT allowed to do

Pinned from the brief:
- Change the session-var name (`app.tenant_id`).
- Add or remove tables without consulting docs/07 §3.
- Add seed INSERTs.
- Edit `.github/workflows/ci.yml`.
- Skip the test-first discipline.
- Add raw `op.execute` beyond the one justified exception (policy-creation loop).

---

## §14 Traceability

- FR-001 (Source registry): table `sources` ships in M03a; CRUD is M07.
- FR-008 (Versioned snapshots): table `source_versions` ships in M03a; snapshot pipeline is M07/M08.
- FR-019 (Taxonomy mapping): schema-supported in M03a (`domain`, `industry`, `industry × domain` index placeholders). Seed is M03c.
- FR-038 (Knowledge graph linking): FKs ship in M03a. Neo4j constraint bootstrap is M03b.
- FR-043 (Semantic search): `findings.title` and `findings.body` indexes ship in M03a. Qdrant collection is M03b.
- FR-057 (Tenant isolation): via NFR-004 RLS policies.
- NFR-004 (Security / tenant isolation): RLS policies.
- NFR-006 (Typed contracts): strict typing, alembic typed enums where supported.
- NFR-007 (Idempotent / replayable): migration idempotency + RLS setter SET LOCAL semantics.

---

## §15 Architectural concerns surfaced

1. **`audit_log` cross-tenant policy** — see §4 Q1 resolution. App-layer audit is M15. The `saie_app` policy's `(actor_id IS NULL OR EXISTS(...))` formulation is the **NULL-actor carve-out** for system-generated rows (job runs without an authenticated user); it is the deliberate exception to the otherwise strict `saie_app` "no INSERT outside a tenant context" posture and is documented in [ADR-0018](./17_Architecture_Decision_Records/0018-audit-log-null-actor-carveout.md) per audit `docs/29 §3.3`.
2. **`tenants.id` as TEXT** — see §6 Q4 deviation note.
3. **Test Postgres library** — see §7.
4. **`alembic_version` is the only idempotency mechanism** — Postgres `CREATE TABLE IF NOT EXISTS` exists but Alembic's `op.create_table` does not emit it. The migration relies on `alembic_version`. If the implementer ever issues `op.execute("CREATE TABLE ...")` raw, idempotency breaks. The full set of justified `op.execute` exceptions is enumerated in §5 (helper functions, FTS indexes via `pg_trgm` fallback, grants, and the policy-creation loop).
5. **No CI workflow change** — `app/db/tests/` is picked up by `testpaths = ["app", ...]` (per docs/23 §3.5.4).
6. **`pg_trgm` extension ships but no trigram index in M03a** — M11 adds the GIN index. Migration's `CREATE EXTENSION IF NOT EXISTS pg_trgm` is justified by FR-043.
7. **FK chain RLS uses EXISTS-subqueries** — 11 of 18 tables have no direct `tenant_id` column; their policies use EXISTS-subqueries. Slight per-query overhead (Postgres optimizes these well). M11/M12 may denormalize `tenant_id` onto hot-path tables; future work, not M03a scope.
