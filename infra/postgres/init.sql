-- infra/postgres/init.sql
--
-- First-run bootstrap of the SAIE Postgres roles + database. Idempotent
-- via DO $$ ... EXCEPTION WHEN duplicate_object ... END $$; guards —
-- running this script on an already-bootstrapped DB is a no-op.
--
-- Three roles:
--   - saie_migrator      — owns the schema, has BYPASSRLS, used by Alembic
--   - saie_app           — RLS-bound, used by the FastAPI app (M04+)
--   - saie_platform_admin — RLS-bound but with a permissive policy
--                           on every tenant-scoped table so cross-tenant
--                           reads (e.g. governance, support) work without
--                           app-layer inspection of every query
--
-- The platform-admin escape is a SCHEMA-LAYER concern and ships in M03a
-- (per docs/28_M03a_Design.md §1.4). The application role detection
-- (M04's JWT-driven role selection) is an APPLICATION-LAYER concern.
--
-- Traceability: FR-057, NFR-004, NFR-007.
--
-- Execute as the Postgres superuser, e.g.:
--   psql -U postgres -d postgres -f infra/postgres/init.sql
--
-- Defaults assume a local dev cluster at localhost:5432. In production
-- inject the passwords via secrets and run this script out of band.

\set ON_ERROR_STOP on

----------------------------------------------------------------------
-- 1. Roles (idempotent)
----------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'saie_migrator') THEN
        CREATE ROLE saie_migrator WITH LOGIN PASSWORD 'saie_migrator';
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'saie_app') THEN
        CREATE ROLE saie_app WITH LOGIN PASSWORD 'saie_app';
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'saie_platform_admin') THEN
        CREATE ROLE saie_platform_admin WITH LOGIN PASSWORD 'saie_platform_admin';
    END IF;
END
$$;

-- saie_migrator must own the schema and have BYPASSRLS so the Alembic
-- migration can create tables + policies without tripping RLS.
ALTER ROLE saie_migrator BYPASSRLS;

----------------------------------------------------------------------
-- 2. Database (idempotent — SELECT-only check)
----------------------------------------------------------------------

SELECT 'CREATE DATABASE saie OWNER saie_migrator'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'saie')
\gexec

----------------------------------------------------------------------
-- 3. Grants (run after connecting to the saie DB)
----------------------------------------------------------------------

-- Use a function so the grants survive even if the migration script
-- is re-run on a fresh cluster where the public schema is already
-- present.
DO $$
BEGIN
    EXECUTE 'GRANT USAGE, CREATE ON SCHEMA public TO saie_migrator';
    EXECUTE 'GRANT USAGE ON SCHEMA public TO saie_app, saie_platform_admin';
    EXECUTE 'GRANT CONNECT ON DATABASE saie TO saie_app, saie_platform_admin';
END
$$;

-- Default privileges so future tables (added by later migrations)
-- are automatically granted to saie_app + saie_platform_admin. The
-- default-privileges record is owned by saie_migrator (the role that
-- runs migrations), so it takes effect for every new relation.
ALTER DEFAULT PRIVILEGES FOR ROLE saie_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
    TO saie_app, saie_platform_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE saie_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES
    TO saie_app, saie_platform_admin;
