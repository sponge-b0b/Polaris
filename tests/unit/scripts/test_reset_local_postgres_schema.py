from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.engine import make_url

from core.database.settings import PostgresSettings
from core.storage.persistence.health import PersistenceHealthReport
from scripts import reset_local_postgres_schema as reset_script


def test_reset_script_requires_explicit_destructive_confirmation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = reset_script.main(
        [],
    )

    captured = capsys.readouterr()
    assert result == 2
    assert "--confirm-destroy-local-db" in captured.err


def test_reset_script_refuses_non_local_database_without_printing_secret(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        reset_script,
        "load_dotenv",
        lambda dotenv_path: None,
    )
    monkeypatch.setattr(
        reset_script,
        "_load_settings",
        lambda: PostgresSettings(
            database_url=(
                "postgresql+asyncpg://polaris:secret-password"
                "@db.example.invalid:5432/polaris"
            ),
        ),
    )

    result = reset_script.main(
        [
            "--confirm-destroy-local-db",
        ],
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "non-local database host" in captured.err
    assert "db.example.invalid" in captured.err
    assert "secret-password" not in captured.err
    assert "secret-password" not in captured.out


def test_reset_script_refuses_protected_database_name() -> None:
    with pytest.raises(
        ValueError,
        match="protected database",
    ):
        reset_script._validate_local_database_url(
            make_url(
                "postgresql+asyncpg://polaris:secret@127.0.0.1:5432/postgres",
            )
        )


def test_reset_script_resets_upgrades_and_verifies_in_order(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[str] = []
    settings = PostgresSettings(
        database_url="postgresql+asyncpg://polaris:secret@127.0.0.1:5432/polaris",
    )

    async def reset_schema(
        received_settings: PostgresSettings,
    ) -> None:
        assert received_settings is settings
        calls.append(
            "reset",
        )

    def upgrade() -> None:
        calls.append(
            "upgrade",
        )

    async def health_report() -> PersistenceHealthReport:
        calls.append(
            "health",
        )
        return PersistenceHealthReport(
            checked_at=datetime(
                2026,
                8,
                3,
                12,
                0,
                tzinfo=UTC,
            ),
            checks=(),
        )

    monkeypatch.setattr(
        reset_script,
        "load_dotenv",
        lambda dotenv_path: None,
    )
    monkeypatch.setattr(
        reset_script,
        "_load_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        reset_script,
        "_reset_public_schema",
        reset_schema,
    )
    monkeypatch.setattr(
        reset_script,
        "_upgrade_database_to_head",
        upgrade,
    )
    monkeypatch.setattr(
        reset_script,
        "_load_persistence_health_report",
        health_report,
    )

    result = reset_script.main(
        [
            "--confirm-destroy-local-db",
        ],
    )

    captured = capsys.readouterr()
    assert result == 0
    assert calls == [
        "reset",
        "upgrade",
        "health",
    ]
    assert "host='127.0.0.1' database='polaris'" in captured.out
    assert "secret" not in captured.out
    assert "schema is current" in captured.out
