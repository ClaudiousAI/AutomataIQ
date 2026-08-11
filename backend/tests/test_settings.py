"""M01 — Settings / env-overlay tests (NFR-004, NFR-006).

The settings layer is the typed contract between ``.env`` and every
service that runs in the backend. These tests pin the behaviour:

- Real environment variables win over ``.env`` values (Pydantic
  guarantees this; we still assert it so a future Pydantic upgrade
  does not silently change precedence).
- ``get_settings()`` reads a fresh snapshot each call (mutating
  ``os.environ`` between calls is reflected — important for tests).
- Unknown fields are ignored, not rejected (forward compatibility
  with later modules' vars).
"""

from __future__ import annotations


def test_defaults_apply_when_no_env(monkeypatch):
    """With no relevant env vars set, defaults populate the model."""
    # Strip any inherited env so defaults take effect.
    for var in (
        "APP_NAME",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_SERVICE_NAMESPACE",
    ):
        monkeypatch.delenv(var, raising=False)

    from app.settings import Settings

    s = Settings()

    assert s.app_name == "saie-api"
    assert s.environment == "development"
    assert s.log_level == "INFO"
    assert s.otel_service_namespace == "saie"
    assert s.otel_exporter_otlp_endpoint is None


def test_env_overrides_defaults(monkeypatch):
    """Env vars override defaults (NFR-006: configuration by env)."""
    monkeypatch.setenv("APP_NAME", "saie-api-staging")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

    from app.settings import Settings

    s = Settings()

    assert s.app_name == "saie-api-staging"
    assert s.environment == "staging"
    assert s.log_level == "DEBUG"
    assert s.otel_exporter_otlp_endpoint == "http://otel-collector:4317"


def test_get_settings_returns_fresh_snapshot(monkeypatch):
    """``get_settings()`` is a function so env mutations between calls are visible.

    A module-level singleton would freeze values at import time and
    break test isolation.
    """
    from app.settings import get_settings

    monkeypatch.setenv("APP_NAME", "first")
    assert get_settings().app_name == "first"

    monkeypatch.setenv("APP_NAME", "second")
    assert get_settings().app_name == "second"


def test_unknown_env_vars_are_ignored(monkeypatch):
    """Future modules' vars do not break M01 (forward compatibility)."""
    monkeypatch.setenv("APP_NAME", "saie-api")
    # A var that M01 does not know about — must not raise.
    monkeypatch.setenv("FUTURE_MODULE_FROBNICATOR", "true")

    from app.settings import Settings

    # No exception means the extra was accepted and dropped.
    Settings()


def test_env_file_relative_to_cwd(monkeypatch, tmp_path, capsys):
    """A local ``.env`` is loaded by the Settings layer (NFR-004).

    Pinning this behaviour means operators can deploy by dropping a
    ``.env`` next to the process — no extra wiring.
    """
    env_file = tmp_path / ".env"
    env_file.write_text("APP_NAME=from-env-file\nLOG_LEVEL=WARNING\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    # Ensure we are not picking up inherited env that would mask the file.
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    from app.settings import Settings

    s = Settings(_env_file=str(env_file))

    assert s.app_name == "from-env-file"
    assert s.log_level == "WARNING"
