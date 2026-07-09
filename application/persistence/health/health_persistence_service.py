from __future__ import annotations

import importlib
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy import text

from core.database.base import Base
from core.database.postgres import create_database_engine
from core.storage.persistence.health import PersistenceHealthCheckCategory
from core.storage.persistence.health import PersistenceHealthCheckResult
from core.storage.persistence.health import PersistenceHealthReport
from core.storage.persistence.lineage import JsonValue
from core.storage.persistence.lineage import clean_optional_identifier


ConnectivityChecker = Callable[[], Awaitable[None]]
DatabaseTableLoader = Callable[[], Awaitable[Sequence[str]]]
CurrentRevisionLoader = Callable[[], Awaitable[str | None]]
HeadRevisionLoader = Callable[[], str | None]
MetadataTableLoader = Callable[[], Sequence[str]]


@dataclass(
    frozen=True,
    slots=True,
)
class HealthPersistenceFilters:
    """
    Typed options for application persistence health checks.
    """

    required_tables: tuple[str, ...] = ()
    repository_components: tuple[str, ...] = ()
    service_components: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "required_tables",
            _normalize_names(
                self.required_tables,
                name="required_tables",
            ),
        )
        object.__setattr__(
            self,
            "repository_components",
            _normalize_names(
                self.repository_components,
                name="repository_components",
            ),
        )
        object.__setattr__(
            self,
            "service_components",
            _normalize_names(
                self.service_components,
                name="service_components",
            ),
        )


class HealthPersistenceService:
    """
    Application service for non-mutating PostgreSQL persistence health checks.

    The service reports connectivity, Alembic migration state, SQLAlchemy
    metadata/table availability, and optional repository/service readiness as
    typed health-check contracts. It does not mutate database state.
    """

    def __init__(
        self,
        *,
        connectivity_checker: ConnectivityChecker | None = None,
        database_table_loader: DatabaseTableLoader | None = None,
        current_revision_loader: CurrentRevisionLoader | None = None,
        head_revision_loader: HeadRevisionLoader | None = None,
        metadata_table_loader: MetadataTableLoader | None = None,
    ) -> None:
        self._connectivity_checker = (
            connectivity_checker or _check_database_connectivity
        )
        self._database_table_loader = database_table_loader or _load_database_tables
        self._current_revision_loader = (
            current_revision_loader or _load_current_alembic_revision
        )
        self._head_revision_loader = head_revision_loader or _load_head_alembic_revision
        self._metadata_table_loader = metadata_table_loader or _load_metadata_tables

    async def check_health(
        self,
        *,
        checked_at: datetime | None = None,
        filters: HealthPersistenceFilters | None = None,
    ) -> PersistenceHealthReport:
        active_checked_at = checked_at or datetime.now(
            UTC,
        )
        active_filters = filters or HealthPersistenceFilters()
        required_tables = active_filters.required_tables or tuple(
            self._metadata_table_loader()
        )

        checks = [
            await self._check_connectivity(
                checked_at=active_checked_at,
            ),
            await self._check_migration_state(
                checked_at=active_checked_at,
            ),
            self._check_metadata_tables(
                checked_at=active_checked_at,
                required_tables=required_tables,
            ),
            await self._check_database_tables(
                checked_at=active_checked_at,
                required_tables=required_tables,
            ),
        ]
        checks.extend(
            _component_readiness_checks(
                checked_at=active_checked_at,
                category=PersistenceHealthCheckCategory.REPOSITORY_READINESS,
                check_name="repository_readiness",
                components=active_filters.repository_components,
                empty_message="No repository readiness components were provided.",
                ready_message="Repository readiness components are configured.",
            )
        )
        checks.extend(
            _component_readiness_checks(
                checked_at=active_checked_at,
                category=PersistenceHealthCheckCategory.SERVICE_READINESS,
                check_name="service_readiness",
                components=active_filters.service_components,
                empty_message="No service readiness components were provided.",
                ready_message="Service readiness components are configured.",
            )
        )

        return PersistenceHealthReport(
            checked_at=active_checked_at,
            checks=tuple(
                checks,
            ),
            metadata={
                "service": "application.persistence.health",
                "required_table_count": len(
                    required_tables,
                ),
            },
        )

    async def _check_connectivity(
        self,
        *,
        checked_at: datetime,
    ) -> PersistenceHealthCheckResult:
        try:
            await self._connectivity_checker()
        except Exception as exc:  # pragma: no cover - default integration guard
            return PersistenceHealthCheckResult.unhealthy(
                category=PersistenceHealthCheckCategory.DATABASE_CONNECTIVITY,
                check_name="postgres_connectivity",
                component="postgresql",
                checked_at=checked_at,
                message="PostgreSQL connectivity check failed.",
                metadata={
                    "error": str(
                        exc,
                    ),
                },
            )

        return PersistenceHealthCheckResult.healthy(
            category=PersistenceHealthCheckCategory.DATABASE_CONNECTIVITY,
            check_name="postgres_connectivity",
            component="postgresql",
            checked_at=checked_at,
            message="PostgreSQL connectivity check succeeded.",
        )

    async def _check_migration_state(
        self,
        *,
        checked_at: datetime,
    ) -> PersistenceHealthCheckResult:
        try:
            current_revision = await self._current_revision_loader()
            head_revision = self._head_revision_loader()
        except Exception as exc:  # pragma: no cover - default integration guard
            return PersistenceHealthCheckResult.unhealthy(
                category=PersistenceHealthCheckCategory.MIGRATION_STATE,
                check_name="alembic_head",
                component="alembic",
                checked_at=checked_at,
                message="Alembic migration state check failed.",
                metadata={
                    "error": str(
                        exc,
                    ),
                },
            )

        metadata: dict[str, JsonValue] = {
            "current_revision": current_revision,
            "head_revision": head_revision,
        }
        if current_revision is None or head_revision is None:
            return PersistenceHealthCheckResult.unknown(
                category=PersistenceHealthCheckCategory.MIGRATION_STATE,
                check_name="alembic_head",
                component="alembic",
                checked_at=checked_at,
                message="Alembic migration state could not be determined.",
                metadata=metadata,
            )

        if current_revision != head_revision:
            return PersistenceHealthCheckResult.unhealthy(
                category=PersistenceHealthCheckCategory.MIGRATION_STATE,
                check_name="alembic_head",
                component="alembic",
                checked_at=checked_at,
                message="Database migration revision is not at Alembic head.",
                metadata=metadata,
            )

        return PersistenceHealthCheckResult.healthy(
            category=PersistenceHealthCheckCategory.MIGRATION_STATE,
            check_name="alembic_head",
            component="alembic",
            checked_at=checked_at,
            message="Database migration revision matches Alembic head.",
            metadata=metadata,
        )

    def _check_metadata_tables(
        self,
        *,
        checked_at: datetime,
        required_tables: Sequence[str],
    ) -> PersistenceHealthCheckResult:
        try:
            metadata_tables = set(
                self._metadata_table_loader(),
            )
        except Exception as exc:  # pragma: no cover - default integration guard
            return PersistenceHealthCheckResult.unhealthy(
                category=PersistenceHealthCheckCategory.METADATA_TABLE_AVAILABILITY,
                check_name="metadata_imports",
                component="sqlalchemy_metadata",
                checked_at=checked_at,
                message="SQLAlchemy metadata import check failed.",
                metadata={
                    "error": str(
                        exc,
                    ),
                },
            )

        missing_tables = tuple(
            table for table in required_tables if table not in metadata_tables
        )
        metadata: dict[str, JsonValue] = {
            "required_tables": tuple(
                required_tables,
            ),
            "missing_tables": missing_tables,
            "metadata_table_count": len(
                metadata_tables,
            ),
        }
        if missing_tables:
            return PersistenceHealthCheckResult.unhealthy(
                category=PersistenceHealthCheckCategory.METADATA_TABLE_AVAILABILITY,
                check_name="metadata_imports",
                component="sqlalchemy_metadata",
                checked_at=checked_at,
                message="SQLAlchemy metadata is missing required persistence tables.",
                metadata=metadata,
            )

        return PersistenceHealthCheckResult.healthy(
            category=PersistenceHealthCheckCategory.METADATA_TABLE_AVAILABILITY,
            check_name="metadata_imports",
            component="sqlalchemy_metadata",
            checked_at=checked_at,
            message="SQLAlchemy metadata includes required persistence tables.",
            metadata=metadata,
        )

    async def _check_database_tables(
        self,
        *,
        checked_at: datetime,
        required_tables: Sequence[str],
    ) -> PersistenceHealthCheckResult:
        try:
            database_tables = set(
                await self._database_table_loader(),
            )
        except Exception as exc:  # pragma: no cover - default integration guard
            return PersistenceHealthCheckResult.unhealthy(
                category=PersistenceHealthCheckCategory.METADATA_TABLE_AVAILABILITY,
                check_name="database_tables",
                component="postgresql",
                checked_at=checked_at,
                message="Database table availability check failed.",
                metadata={
                    "error": str(
                        exc,
                    ),
                },
            )

        missing_tables = tuple(
            table for table in required_tables if table not in database_tables
        )
        metadata: dict[str, JsonValue] = {
            "required_tables": tuple(
                required_tables,
            ),
            "missing_tables": missing_tables,
            "database_table_count": len(
                database_tables,
            ),
        }
        if missing_tables:
            return PersistenceHealthCheckResult.unhealthy(
                category=PersistenceHealthCheckCategory.METADATA_TABLE_AVAILABILITY,
                check_name="database_tables",
                component="postgresql",
                checked_at=checked_at,
                message="Database is missing required persistence tables.",
                metadata=metadata,
            )

        return PersistenceHealthCheckResult.healthy(
            category=PersistenceHealthCheckCategory.METADATA_TABLE_AVAILABILITY,
            check_name="database_tables",
            component="postgresql",
            checked_at=checked_at,
            message="Database includes required persistence tables.",
            metadata=metadata,
        )


async def _check_database_connectivity() -> None:
    engine = create_database_engine()
    try:
        async with engine.connect() as connection:
            await connection.execute(
                text("SELECT 1"),
            )
    finally:
        await engine.dispose()


async def _load_database_tables() -> tuple[str, ...]:
    engine = create_database_engine()
    try:
        async with engine.connect() as connection:
            tables = await connection.run_sync(
                lambda sync_connection: tuple(
                    sorted(
                        inspect(
                            sync_connection,
                        ).get_table_names()
                    )
                )
            )
    finally:
        await engine.dispose()
    return tables


async def _load_current_alembic_revision() -> str | None:
    engine = create_database_engine()
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT version_num FROM alembic_version"),
            )
            revisions = tuple(row[0] for row in result.fetchall())
    finally:
        await engine.dispose()

    if (
        len(
            revisions,
        )
        != 1
    ):
        return None
    return str(
        revisions[0],
    )


def _load_head_alembic_revision() -> str | None:
    config = Config(
        "alembic.ini",
    )
    script = ScriptDirectory.from_config(
        config,
    )
    return script.get_current_head()


def _load_metadata_tables() -> tuple[str, ...]:
    importlib.import_module(
        "core.database.models",
    )
    return tuple(
        sorted(
            Base.metadata.tables,
        )
    )


def _component_readiness_checks(
    *,
    checked_at: datetime,
    category: PersistenceHealthCheckCategory,
    check_name: str,
    components: Sequence[str],
    empty_message: str,
    ready_message: str,
) -> tuple[PersistenceHealthCheckResult, ...]:
    if not components:
        return (
            PersistenceHealthCheckResult.unknown(
                category=category,
                check_name=check_name,
                checked_at=checked_at,
                message=empty_message,
                metadata={
                    "component_count": 0,
                },
            ),
        )

    return tuple(
        PersistenceHealthCheckResult.healthy(
            category=category,
            check_name=check_name,
            checked_at=checked_at,
            component=component,
            message=ready_message,
            metadata={
                "component_count": len(
                    components,
                ),
            },
        )
        for component in components
    )


def _normalize_names(
    values: Sequence[str],
    *,
    name: str,
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(
        values,
    ):
        cleaned = clean_optional_identifier(
            value,
            f"{name}[{index}]",
        )
        if cleaned is None:
            raise ValueError(f"{name}[{index}] cannot be empty.")
        if cleaned in seen:
            continue
        seen.add(
            cleaned,
        )
        normalized.append(
            cleaned,
        )
    return tuple(
        normalized,
    )
