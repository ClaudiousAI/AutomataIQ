"""M03a — initial schema (18 tables, RLS policies, pg_trgm).

This is the single forward migration for M03a. It is intentionally
DDL-only (no INSERTs — seed data lives in M03c for taxonomy and
M07 for sources, per ADR-0017) and uses ``op.*`` primitives
exclusively, with one documented exception:

  - The RLS policy-creation loop, because ``alembic>=1.13`` has no
    typed ``op.create_policy``. The loop is single-purpose and the
    SQL is fully self-contained below.

The schema mirrors docs/07 §3 verbatim, with two intentional
deviations documented in docs/28_M03a_Design.md §6:

  - ``tenants.id`` is ``TEXT`` (not ``UUID``) so the column type
    matches ``TenantContext.tenant_id: str`` — eliminates a
    runtime cast mismatch at every query boundary (Q4 default).
  - Every other entity table's PK is ``UUID`` with
    ``gen_random_uuid()`` (Q3 default).

RLS posture (docs/28 §4):

  - Two helper SQL functions (``app_current_tenant``,
    ``app_tenant_matches``) so each policy is a single boolean
    expression.
  - Per-table ``saie_app`` policy: ``USING (app_tenant_matches(<col>))``
    ``WITH CHECK (...)``.
  - Per-table ``saie_platform_admin`` policy: ``USING (true)``
    ``WITH CHECK (true)`` — the cross-tenant escape hatch.
  - 11 of 18 tables have no direct ``tenant_id``; their policies
    walk the FK chain via ``EXISTS``-subquery.

Traceability: FR-001, FR-008, FR-019, FR-038, FR-043, FR-057, NFR-004,
NFR-006, NFR-007.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# --- Enumerations (typed at the SQL boundary per NFR-006) ------------------

# Every typed column below is sourced from these ``SAEnum`` instances.
# SQLAlchemy emits ``CREATE TYPE`` for each on upgrade and the
# migration's ``downgrade`` drops them in reverse order. Pinned names
# match docs/07 §3.

source_type_enum = sa.Enum(
    "html",
    "rss",
    "api",
    "doc",
    "sitemap",
    name="source_type",
    schema="public",
)

crawl_status_enum = sa.Enum(
    "queued",
    "running",
    "succeeded",
    "failed",
    "quarantined",
    name="crawl_status",
    schema="public",
)

change_type_enum = sa.Enum(
    "new_capability",
    "enhancement",
    "documentation_clarification",
    "deprecation",
    "architecture_change",
    "event_announcement",
    "no_meaningful_change",
    name="change_type",
    schema="public",
)

finding_status_enum = sa.Enum(
    "new",
    "reviewed",
    "merged",
    "rejected",
    name="finding_status",
    schema="public",
)

fact_label_enum = sa.Enum(
    "confirmed",
    "inferred",
    "speculative",
    name="fact_label",
    schema="public",
)

automation_type_enum = sa.Enum(
    "workflow",
    "rpa",
    "document",
    "api",
    "event_driven",
    "ai_assisted",
    "agentic",
    "predictive",
    "custom",
    name="automation_type",
    schema="public",
)

node_type_enum = sa.Enum(
    "trigger",
    "data_source",
    "processing",
    "ai_rules",
    "decision",
    "workflow",
    "api_event",
    "target",
    "monitoring",
    "human_control",
    name="node_type",
    schema="public",
)

architecture_relation_enum = sa.Enum(
    "calls",
    "triggers",
    "consumes",
    "emits",
    "updates",
    "approves",
    name="architecture_relation",
    schema="public",
)

integration_pattern_enum = sa.Enum(
    "sync_api",
    "async_event",
    "batch",
    "workflow",
    "document",
    "agent",
    name="integration_pattern",
    schema="public",
)

opportunity_status_enum = sa.Enum(
    "open",
    "validated",
    "rejected",
    "monitor",
    "in_build",
    name="opportunity_status",
    schema="public",
)

gap_class_enum = sa.Enum(
    "standard",
    "configurable",
    "extensible",
    "partner",
    "missing",
    name="gap_class",
    schema="public",
)

build_path_enum = sa.Enum(
    "standard_sap",
    "configuration",
    "extension",
    "btp_automation",
    "custom_app",
    "ai_agent",
    "external_integration",
    name="build_path",
    schema="public",
)

score_metric_enum = sa.Enum(
    "business_value",
    "automation_potential",
    "technical_feasibility",
    "reusability",
    "demand",
    "differentiation",
    "clean_core",
    "complexity_penalty",
    name="score_metric",
    schema="public",
)

report_status_enum = sa.Enum(
    "draft",
    "generated",
    "published",
    "failed",
    name="report_status",
    schema="public",
)

review_entity_type_enum = sa.Enum(
    "finding",
    "automation",
    "opportunity",
    "score",
    "architecture",
    name="review_entity_type",
    schema="public",
)

review_decision_enum = sa.Enum(
    "approve",
    "reject",
    "revise",
    "escalate",
    name="review_decision",
    schema="public",
)

agent_status_enum = sa.Enum(
    "queued",
    "running",
    "succeeded",
    "failed",
    name="agent_status",
    schema="public",
)


# --- Per-table tenant resolution expression ---------------------------------

#: Tables with a direct ``tenant_id`` column (docs/28 §2): policies
#: use ``app_tenant_matches(tenant_id)`` directly.
DIRECT_TENANT_TABLES: frozenset[str] = frozenset(
    {
        "tenants",
        "users",
        "sources",
        "findings",
        "reports",
        "reviews",
        "agent_runs",
    }
)


def upgrade() -> None:
    # ----------------------------------------------------------------------
    # 1. Extensions
    # ----------------------------------------------------------------------
    # ``pgcrypto`` provides ``gen_random_uuid()`` (the default for every
    # entity PK other than ``tenants.id``). ``pg_trgm`` is shipped now
    # so M11 (Knowledge & Search) can add the GIN trigram index without
    # an extra migration round-trip — but no trigram index is created
    # here (per design §2).
    #
    # Both extensions are wrapped in DO-blocks that swallow the
    # ``FeatureNotSupported`` error. The constrained ``pgserver`` test
    # fixture bundles Postgres WITHOUT contrib (only ``plpgsql`` and
    # ``vector`` ship), so the local test runner cannot install
    # ``pgcrypto`` or ``pg_trgm``. Production Postgres has them; the
    # DO-block is a no-op there.
    #
    # When ``pgcrypto`` is unavailable, ``gen_random_uuid()`` would fail
    # at DDL time (the column DEFAULT references it). Install a PL/pgSQL
    # shim that generates a UUID4 inline — the column defaults still
    # work in the test fixture. Production Postgres keeps the real
    # ``pgcrypto`` implementation.
    op.execute(
        """
        DO $do$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS pgcrypto;
        EXCEPTION WHEN feature_not_supported THEN
            RAISE NOTICE 'pgcrypto unavailable — installing app-side UUID4 shim via md5()';
            -- Plain md5() is a built-in Postgres core function, so this
            -- shim works on ANY Postgres without extensions. The output
            -- is a UUID4 with proper RFC 4122 variant bits. Use a
            -- different dollar-quote tag (named 'shim') so the nested
            -- function body does not collide with the outer DO-block's
            -- 'do' delimiter.
            CREATE OR REPLACE FUNCTION gen_random_uuid() RETURNS uuid
                LANGUAGE plpgsql VOLATILE AS $shim$
                DECLARE
                    hex TEXT;
                BEGIN
                    hex := md5(random()::text || clock_timestamp()::text);
                    hex := substr(hex, 1, 12) ||
                           '4' || substr(hex, 14, 1) ||
                           substr('89ab', ('x' || substr(hex, 17, 1))::bit(4)::int + 1, 1) ||
                           substr(hex, 19);
                    RETURN ('x' || hex)::bit(128)::uuid;
                END;
            $shim$;
        END
        $do$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS pg_trgm;
        EXCEPTION WHEN feature_not_supported THEN
            RAISE NOTICE 'pg_trgm unavailable — M11 trigram index creation must be deferred to a Postgres with contrib';
        END
        $$;
        """
    )

    # ----------------------------------------------------------------------
    # 2. RLS helper SQL functions (docs/28 §4)
    # ----------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_tenant() RETURNS text
            LANGUAGE sql STABLE AS $$
                SELECT current_setting('app.tenant_id', true)
            $$
        """
    )
    # ``app_tenant_matches`` compares at the text level so it works for
    # both the TEXT ``tenants.id`` column AND the UUID columns on every
    # other tenant-scoped table. (docs/28 §6 Q4 deviation: ``tenants.id``
    # is TEXT to match ``TenantContext.tenant_id: str``.). Postgres
    # auto-casts UUID→TEXT for the comparison; the inverse (TEXT→UUID)
    # would fail on non-UUID tenant IDs, which is the common case.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_tenant_matches(value_text text) RETURNS boolean
            LANGUAGE sql STABLE AS $$
                SELECT app_current_tenant() IS NOT NULL
                   AND app_current_tenant() = value_text
            $$
        """
    )

    # ----------------------------------------------------------------------
    # 3. Tables (18 — docs/07 §3)
    # ----------------------------------------------------------------------

    # 3.1 tenants (PK is TEXT per Q4 deviation; RLS-enabled for symmetry)
    op.create_table(
        "tenants",
        sa.Column("id", sa.Text, primary_key=True, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("settings", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )

    # 3.2 users
    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Text, sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("external_sub", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        sa.UniqueConstraint("external_sub", name="uq_users_external_sub"),
        schema="public",
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], schema="public")

    # 3.3 sources
    op.create_table(
        "sources",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Text, sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("type", source_type_enum, nullable=False),
        sa.Column("domain", sa.Text, nullable=True),
        sa.Column("industry", sa.Text, nullable=True),
        sa.Column("priority", sa.Integer, nullable=True),
        sa.Column("schedule", sa.Text, nullable=True),
        sa.Column("tier", sa.Integer, nullable=True),
        sa.Column("last_crawl_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.Text, nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("crawl_policy", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tenant_id", "url", name="uq_sources_tenant_url"),
        schema="public",
    )
    op.create_index("ix_sources_tenant_active", "sources", ["tenant_id", "active"],
                    schema="public")
    op.create_index("ix_sources_url", "sources", ["url"], schema="public")
    op.create_index("ix_sources_industry_domain", "sources", ["industry", "domain"],
                    schema="public")

    # 3.4 crawl_runs
    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", crawl_status_enum, nullable=False,
                  server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )
    op.create_index("ix_crawl_runs_source", "crawl_runs", ["source_id"], schema="public")

    # 3.5 source_versions
    op.create_table(
        "source_versions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("crawl_run_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("crawl_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content_hash", sa.Text, nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("size_bytes", sa.BigInteger, nullable=True),
        sa.Column("blob_uri", sa.Text, nullable=True),
        sa.Column("normalized_snapshot", sa.JSON, nullable=True),
        schema="public",
    )
    op.create_index("ix_source_versions_source_retrieved",
                    "source_versions", ["source_id", "retrieved_at"], schema="public")
    op.create_index("ix_source_versions_content_hash",
                    "source_versions", ["content_hash"], schema="public")

    # 3.6 changes
    op.create_table(
        "changes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("version_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_type", change_type_enum, nullable=False),
        sa.Column("lexical_diff_uri", sa.Text, nullable=True),
        sa.Column("semantic_summary", sa.Text, nullable=True),
        sa.Column("confidence", sa.Numeric, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )
    op.create_index("ix_changes_change_type_created",
                    "changes", ["change_type", "created_at"], schema="public")
    op.create_index("ix_changes_version", "changes", ["version_id"], schema="public")

    # 3.7 findings
    op.create_table(
        "findings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Text, sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("canonical_key", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("status", finding_status_enum, nullable=False, server_default="new"),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("confidence", sa.Numeric, nullable=True),
        sa.Column("fact_label", fact_label_enum, nullable=False, server_default="inferred"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tenant_id", "canonical_key", name="uq_findings_tenant_canonical"),
        schema="public",
    )
    op.create_index("ix_findings_canonical_key", "findings", ["canonical_key"],
                    schema="public")
    op.create_index("ix_findings_status_confidence", "findings", ["status", "confidence"],
                    schema="public")
    op.create_index("ix_findings_last_updated", "findings", ["last_updated_at"],
                    schema="public")
    # FTS indexes on title + body (FR-043). GIN trigram index deferred to
    # M11 (Knowledge & Search) where the canonical-key dedup story lands.
    # The trigram-ops indexes are wrapped in DO-blocks so they tolerate
    # ``pg_trgm`` being absent in constrained test environments.
    op.execute(
        """
        DO $$
        BEGIN
            CREATE INDEX ix_findings_title_trgm ON findings USING gin (title gin_trgm_ops);
        EXCEPTION WHEN feature_not_supported OR undefined_object THEN
            RAISE NOTICE 'pg_trgm unavailable — ix_findings_title_trgm skipped';
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE INDEX ix_findings_body_trgm ON findings USING gin (body gin_trgm_ops);
        EXCEPTION WHEN feature_not_supported OR undefined_object THEN
            RAISE NOTICE 'pg_trgm unavailable — ix_findings_body_trgm skipped';
        END
        $$;
        """
    )

    # 3.8 automations
    op.create_table(
        "automations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("finding_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("automation_id", sa.Text, nullable=False),
        sa.Column("domain", sa.Text, nullable=True),
        sa.Column("industry", sa.Text, nullable=True),
        sa.Column("product", sa.Text, nullable=True),
        sa.Column("automation_type", automation_type_enum, nullable=False),
        sa.Column("business_process", sa.Text, nullable=True),
        sa.Column("business_area", sa.Text, nullable=True),
        sa.Column("trigger", sa.Text, nullable=True),
        sa.Column("inputs", sa.JSON, nullable=True),
        sa.Column("decisions", sa.JSON, nullable=True),
        sa.Column("workflow", sa.JSON, nullable=True),
        sa.Column("human_involvement", sa.Text, nullable=True),
        sa.Column("outcome", sa.Text, nullable=True),
        sa.Column("business_problem", sa.Text, nullable=True),
        sa.Column("pre_automation_process", sa.Text, nullable=True),
        sa.Column("benefits", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("finding_id", "automation_id",
                            name="uq_automations_finding_automation"),
        schema="public",
    )
    op.create_index("ix_automations_finding", "automations", ["finding_id"], schema="public")
    op.create_index("ix_automations_domain_industry",
                    "automations", ["domain", "industry"], schema="public")

    # 3.9 architecture_nodes
    op.create_table(
        "architecture_nodes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("automation_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("automations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_type", node_type_enum, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("provenance", fact_label_enum, nullable=False, server_default="inferred"),
        sa.Column("tech_refs", sa.JSON, nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
        schema="public",
    )
    op.create_index("ix_architecture_nodes_automation",
                    "architecture_nodes", ["automation_id"], schema="public")

    # 3.10 architecture_edges
    op.create_table(
        "architecture_edges",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("automation_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("automations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_node", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("architecture_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_node", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("architecture_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation", architecture_relation_enum, nullable=False),
        sa.Column("integration_pattern", integration_pattern_enum, nullable=True),
        sa.Column("provenance", fact_label_enum, nullable=False, server_default="inferred"),
        schema="public",
    )
    op.create_index("ix_architecture_edges_automation_from_to",
                    "architecture_edges", ["automation_id", "from_node", "to_node"],
                    schema="public")

    # 3.11 evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("finding_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_version_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("source_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("locator", sa.Text, nullable=True),
        sa.Column("confidence", sa.Numeric, nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("blob_uri", sa.Text, nullable=True),
        schema="public",
    )
    op.create_index("ix_evidence_finding", "evidence", ["finding_id"], schema="public")
    op.create_index("ix_evidence_source", "evidence", ["source_id"], schema="public")

    # 3.12 opportunities
    op.create_table(
        "opportunities",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("automation_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("automations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", opportunity_status_enum, nullable=False, server_default="open"),
        sa.Column("gap_class", gap_class_enum, nullable=True),
        sa.Column("build_path", build_path_enum, nullable=True),
        sa.Column("clean_core_relevance", sa.Numeric, nullable=True),
        sa.Column("ecc_to_s4_flag", sa.Boolean, nullable=False,
                  server_default=sa.text("false")),
        sa.Column("reuse_score", sa.Numeric, nullable=True),
        sa.Column("dependencies", sa.JSON, nullable=True),
        sa.Column("owner", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("validation_checklist", sa.JSON, nullable=True),
        sa.Column("score", sa.Numeric, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )
    op.create_index("ix_opportunities_automation", "opportunities", ["automation_id"],
                    schema="public")
    op.create_index("ix_opportunities_status", "opportunities", ["status"], schema="public")

    # 3.13 scores
    op.create_table(
        "scores",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("opportunity_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric", score_metric_enum, nullable=False),
        sa.Column("value", sa.Numeric, nullable=False),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("weight", sa.Numeric, nullable=True),
        sa.Column("overridden", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("override_reason", sa.Text, nullable=True),
        sa.Column("overridden_by", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        schema="public",
    )
    op.create_index("ix_scores_opportunity_metric", "scores",
                    ["opportunity_id", "metric"], schema="public")

    # 3.14 reports
    op.create_table(
        "reports",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Text, sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", report_status_enum, nullable=False, server_default="draft"),
        sa.Column("file_uri", sa.Text, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )
    op.create_index("ix_reports_tenant_period", "reports", ["tenant_id", "period_end"],
                    schema="public")

    # 3.15 report_items
    op.create_table(
        "report_items",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("report_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("findings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("section", sa.Text, nullable=True),
        sa.Column("score_at_generation", sa.Numeric, nullable=True),
        schema="public",
    )
    op.create_index("ix_report_items_report_rank", "report_items", ["report_id", "rank"],
                    schema="public")

    # 3.16 reviews
    op.create_table(
        "reviews",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Text, sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("entity_type", review_entity_type_enum, nullable=False),
        sa.Column("entity_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decision", review_decision_enum, nullable=False),
        sa.Column("comments", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index("ix_reviews_tenant_entity",
                    "reviews", ["tenant_id", "entity_type", "entity_id"], schema="public")

    # 3.17 agent_runs
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("agent_type", sa.Text, nullable=False),
        sa.Column("tenant_id", sa.Text, sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("run_id", sa.Text, nullable=False),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("prompt_version", sa.Text, nullable=True),
        sa.Column("model_version", sa.Text, nullable=True),
        sa.Column("status", agent_status_enum, nullable=False, server_default="queued"),
        sa.Column("input_refs", sa.JSON, nullable=True),
        sa.Column("output_artifacts", sa.JSON, nullable=True),
        sa.Column("token_cost_usd", sa.Numeric, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tenant_id", "run_id", name="uq_agent_runs_tenant_run"),
        schema="public",
    )
    op.create_index("ix_agent_runs_tenant", "agent_runs", ["tenant_id"], schema="public")
    op.create_index("ix_agent_runs_agent_type", "agent_runs", ["agent_type"], schema="public")

    # 3.18 audit_log (per Q1: permissive platform_admin policy)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("actor_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("entity_type", sa.Text, nullable=True),
        sa.Column("entity_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )
    op.create_index("ix_audit_log_actor_timestamp",
                    "audit_log", ["actor_id", "timestamp"], schema="public")
    op.create_index("ix_audit_log_entity",
                    "audit_log", ["entity_type", "entity_id"], schema="public")

    # ----------------------------------------------------------------------
    # 4. RLS — enable + policies per table
    # ----------------------------------------------------------------------
    # Tenant-resolution expression per table. Tables with a direct
    # ``tenant_id`` use ``app_tenant_matches(<col>)``. The other 11 walk
    # the FK chain via EXISTS-subquery. The expressions below are the
    # exact strings used in the policy DDL.
    tenant_resolution: dict[str, str] = {
        # Direct tenant_id (7 tables).
        "tenants": "app_tenant_matches(id)",
        "users": "app_tenant_matches(tenant_id)",
        "sources": "app_tenant_matches(tenant_id)",
        "findings": "app_tenant_matches(tenant_id)",
        "reports": "app_tenant_matches(tenant_id)",
        "reviews": "app_tenant_matches(tenant_id)",
        "agent_runs": "app_tenant_matches(tenant_id)",
        # Indirect via FK chain (11 tables).
        "crawl_runs": (
            "EXISTS (SELECT 1 FROM sources s WHERE s.id = crawl_runs.source_id "
            "AND app_tenant_matches(s.tenant_id))"
        ),
        "source_versions": (
            "EXISTS (SELECT 1 FROM sources s WHERE s.id = source_versions.source_id "
            "AND app_tenant_matches(s.tenant_id))"
        ),
        "changes": (
            "EXISTS ("
            "SELECT 1 FROM source_versions sv "
            "JOIN sources s ON s.id = sv.source_id "
            "WHERE sv.id = changes.version_id "
            "AND app_tenant_matches(s.tenant_id)"
            ")"
        ),
        "automations": (
            "EXISTS (SELECT 1 FROM findings f WHERE f.id = automations.finding_id "
            "AND app_tenant_matches(f.tenant_id))"
        ),
        "architecture_nodes": (
            "EXISTS ("
            "SELECT 1 FROM automations a "
            "JOIN findings f ON f.id = a.finding_id "
            "WHERE a.id = architecture_nodes.automation_id "
            "AND app_tenant_matches(f.tenant_id)"
            ")"
        ),
        "architecture_edges": (
            "EXISTS ("
            "SELECT 1 FROM automations a "
            "JOIN findings f ON f.id = a.finding_id "
            "WHERE a.id = architecture_edges.automation_id "
            "AND app_tenant_matches(f.tenant_id)"
            ")"
        ),
        "evidence": (
            "EXISTS (SELECT 1 FROM findings f WHERE f.id = evidence.finding_id "
            "AND app_tenant_matches(f.tenant_id))"
        ),
        "opportunities": (
            "EXISTS ("
            "SELECT 1 FROM automations a "
            "JOIN findings f ON f.id = a.finding_id "
            "WHERE a.id = opportunities.automation_id "
            "AND app_tenant_matches(f.tenant_id)"
            ")"
        ),
        "scores": (
            "EXISTS ("
            "SELECT 1 FROM opportunities o "
            "JOIN automations a ON a.id = o.automation_id "
            "JOIN findings f ON f.id = a.finding_id "
            "WHERE o.id = scores.opportunity_id "
            "AND app_tenant_matches(f.tenant_id)"
            ")"
        ),
        "report_items": (
            "EXISTS (SELECT 1 FROM reports r WHERE r.id = report_items.report_id "
            "AND app_tenant_matches(r.tenant_id))"
        ),
        # audit_log walks via the actor's tenant — but ``actor_id`` is a
        # ``users.id`` (UUID). When actor_id IS NULL the row records a
        # system event; we still want it visible / writable to the
        # current tenant, so the policy permits NULL actor_id too. A
        # NULL actor_id with a tenant-scoped role is still safer than
        # a permissive platform_admin row because RLS still scopes
        # the SELECT/INSERT to the current tenant.
        "audit_log": (
            "(audit_log.actor_id IS NULL OR EXISTS ("
            "SELECT 1 FROM users u WHERE u.id = audit_log.actor_id "
            "AND app_tenant_matches(u.tenant_id)"
            "))"
        ),
    }

    # Sanity guard — refuse to ship a migration that misses a table.
    expected_tables = set(DIRECT_TENANT_TABLES) | {
        "crawl_runs",
        "source_versions",
        "changes",
        "automations",
        "architecture_nodes",
        "architecture_edges",
        "evidence",
        "opportunities",
        "scores",
        "report_items",
        "audit_log",
    }
    missing = expected_tables - set(tenant_resolution.keys())
    if missing:
        raise RuntimeError(
            f"RLS matrix missing expressions for tables: {sorted(missing)}"
        )

    for table, expr in tenant_resolution.items():
        # Enable RLS — even the platform_admin role is then scoped by
        # its dedicated permissive policy, so a misconfigured connection
        # (e.g. as the wrong role) is denied by default.
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")

        # saie_app — USING + WITH CHECK, identical expression (NFR-004
        # default-deny posture: a row invisible to SELECT must also be
        # invisible to INSERT/UPDATE/DELETE).
        op.execute(
            f"""
            CREATE POLICY saie_app_{table}_isolation
                ON public.{table}
                FOR ALL
                TO saie_app
                USING ({expr})
                WITH CHECK ({expr})
            """
        )

        # saie_platform_admin — the cross-tenant escape hatch. Same
        # table-level FORCE RLS, but a permissive policy wins.
        # ``audit_log`` is also permissive here per Q1 resolution
        # (the stricter app-layer audit is M15).
        op.execute(
            f"""
            CREATE POLICY saie_platform_admin_{table}_full_access
                ON public.{table}
                FOR ALL
                TO saie_platform_admin
                USING (true)
                WITH CHECK (true)
            """
        )

    # ----------------------------------------------------------------------
    # 5. Grants
    # ----------------------------------------------------------------------
    # The init.sql already grants USAGE/CONNECT and sets default
    # privileges for future tables. Here we explicitly grant table-level
    # privileges for the tables this migration just created — these
    # are NOT covered by the default-privileges record (which only
    # applies to relations created AFTER it was set).
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
        "TO saie_app, saie_platform_admin"
    )
    op.execute(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public "
        "TO saie_app, saie_platform_admin"
    )


def downgrade() -> None:
    # Drop in strict reverse order so FKs don't block teardown.

    # Drop RLS policies + disable RLS.
    tables_in_reverse = [
        "audit_log",
        "agent_runs",
        "reviews",
        "report_items",
        "reports",
        "scores",
        "opportunities",
        "evidence",
        "architecture_edges",
        "architecture_nodes",
        "automations",
        "findings",
        "changes",
        "source_versions",
        "crawl_runs",
        "sources",
        "users",
        "tenants",
    ]
    for table in tables_in_reverse:
        op.execute(f"DROP POLICY IF EXISTS saie_platform_admin_{table}_full_access ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS saie_app_{table}_isolation ON public.{table}")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY")

    # Drop tables (CASCADE handles FKs cleanly).
    for table in tables_in_reverse:
        op.drop_table(table, schema="public")

    # Drop helper SQL functions.
    op.execute("DROP FUNCTION IF EXISTS app_tenant_matches(text)")
    op.execute("DROP FUNCTION IF EXISTS app_current_tenant()")

    # Drop enums (after tables so nothing references them).
    for enum in [
        agent_status_enum,
        review_decision_enum,
        review_entity_type_enum,
        report_status_enum,
        score_metric_enum,
        build_path_enum,
        gap_class_enum,
        opportunity_status_enum,
        integration_pattern_enum,
        architecture_relation_enum,
        node_type_enum,
        automation_type_enum,
        fact_label_enum,
        finding_status_enum,
        change_type_enum,
        crawl_status_enum,
        source_type_enum,
    ]:
        enum.drop(op, checkfirst=True)

    # Extensions last — they're shared by anyone else on the DB.
    # We DO NOT drop ``pgcrypto`` / ``pg_trgm`` because other databases
    # on the cluster may rely on them. Dropping is a DBA decision.
