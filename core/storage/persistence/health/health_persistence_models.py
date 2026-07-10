from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from uuid import uuid4

from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import JsonValue
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.lineage import require_non_empty_identifier


class PersistenceHealthStatus(str, Enum):
    """
    Aggregated or individual health status for persistence diagnostics.
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class PersistenceHealthCheckCategory(str, Enum):
    """
    Persistence health-check categories required before API/RAG expansion.
    """

    DATABASE_CONNECTIVITY = "database_connectivity"
    MIGRATION_STATE = "migration_state"
    METADATA_TABLE_AVAILABILITY = "metadata_table_availability"
    REPOSITORY_READINESS = "repository_readiness"
    SERVICE_READINESS = "service_readiness"


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceHealthCheckResult:
    """
    Typed result for one persistence health check.

    These are diagnostic contracts only. They do not open database connections,
    inspect migrations, mutate repositories, or execute services.
    """

    category: PersistenceHealthCheckCategory | str
    check_name: str
    status: PersistenceHealthStatus | str
    message: str
    checked_at: datetime
    component: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "category",
            _coerce_health_category(
                self.category,
            ),
        )
        object.__setattr__(
            self,
            "check_name",
            require_non_empty_identifier(
                self.check_name,
                "check_name",
            ),
        )
        object.__setattr__(
            self,
            "status",
            _coerce_health_status(
                self.status,
            ),
        )
        object.__setattr__(
            self,
            "message",
            require_non_empty_identifier(
                self.message,
                "message",
            ),
        )
        object.__setattr__(
            self,
            "component",
            clean_optional_identifier(
                self.component,
                "component",
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @classmethod
    def healthy(
        cls,
        *,
        category: PersistenceHealthCheckCategory | str,
        check_name: str,
        message: str,
        checked_at: datetime,
        component: str | None = None,
        metadata: JsonObject | None = None,
    ) -> PersistenceHealthCheckResult:
        return cls(
            category=category,
            check_name=check_name,
            status=PersistenceHealthStatus.HEALTHY,
            message=message,
            checked_at=checked_at,
            component=component,
            metadata=metadata or {},
        )

    @classmethod
    def degraded(
        cls,
        *,
        category: PersistenceHealthCheckCategory | str,
        check_name: str,
        message: str,
        checked_at: datetime,
        component: str | None = None,
        metadata: JsonObject | None = None,
    ) -> PersistenceHealthCheckResult:
        return cls(
            category=category,
            check_name=check_name,
            status=PersistenceHealthStatus.DEGRADED,
            message=message,
            checked_at=checked_at,
            component=component,
            metadata=metadata or {},
        )

    @classmethod
    def unhealthy(
        cls,
        *,
        category: PersistenceHealthCheckCategory | str,
        check_name: str,
        message: str,
        checked_at: datetime,
        component: str | None = None,
        metadata: JsonObject | None = None,
    ) -> PersistenceHealthCheckResult:
        return cls(
            category=category,
            check_name=check_name,
            status=PersistenceHealthStatus.UNHEALTHY,
            message=message,
            checked_at=checked_at,
            component=component,
            metadata=metadata or {},
        )

    @classmethod
    def unknown(
        cls,
        *,
        category: PersistenceHealthCheckCategory | str,
        check_name: str,
        message: str,
        checked_at: datetime,
        component: str | None = None,
        metadata: JsonObject | None = None,
    ) -> PersistenceHealthCheckResult:
        return cls(
            category=category,
            check_name=check_name,
            status=PersistenceHealthStatus.UNKNOWN,
            message=message,
            checked_at=checked_at,
            component=component,
            metadata=metadata or {},
        )

    @property
    def is_healthy(
        self,
    ) -> bool:
        return self.status is PersistenceHealthStatus.HEALTHY

    @property
    def is_degraded(
        self,
    ) -> bool:
        return self.status is PersistenceHealthStatus.DEGRADED

    @property
    def is_unhealthy(
        self,
    ) -> bool:
        return self.status is PersistenceHealthStatus.UNHEALTHY

    @property
    def is_unknown(
        self,
    ) -> bool:
        return self.status is PersistenceHealthStatus.UNKNOWN

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        category = _coerce_health_category(
            self.category,
        )
        status = _coerce_health_status(
            self.status,
        )
        result: dict[str, JsonValue] = {
            "category": category.value,
            "check_name": self.check_name,
            "status": status.value,
            "message": self.message,
            "checked_at": self.checked_at.isoformat(),
            "metadata": self.metadata,
        }
        if self.component is not None:
            result["component"] = self.component
        return result


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceHealthReport:
    """
    Typed aggregate report for persistence health diagnostics.
    """

    checked_at: datetime
    checks: tuple[PersistenceHealthCheckResult, ...]
    report_id: str = field(
        default_factory=lambda: f"persistence_health_report:{uuid4().hex}",
    )
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "report_id",
            require_non_empty_identifier(
                self.report_id,
                "report_id",
            ),
        )
        object.__setattr__(
            self,
            "checks",
            _normalize_health_checks(
                self.checks,
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def status(
        self,
    ) -> PersistenceHealthStatus:
        if not self.checks:
            return PersistenceHealthStatus.UNKNOWN
        if self.unhealthy_checks:
            return PersistenceHealthStatus.UNHEALTHY
        if self.degraded_checks or self.unknown_checks:
            return PersistenceHealthStatus.DEGRADED
        return PersistenceHealthStatus.HEALTHY

    @property
    def healthy_checks(
        self,
    ) -> tuple[PersistenceHealthCheckResult, ...]:
        return tuple(check for check in self.checks if check.is_healthy)

    @property
    def degraded_checks(
        self,
    ) -> tuple[PersistenceHealthCheckResult, ...]:
        return tuple(check for check in self.checks if check.is_degraded)

    @property
    def unhealthy_checks(
        self,
    ) -> tuple[PersistenceHealthCheckResult, ...]:
        return tuple(check for check in self.checks if check.is_unhealthy)

    @property
    def unknown_checks(
        self,
    ) -> tuple[PersistenceHealthCheckResult, ...]:
        return tuple(check for check in self.checks if check.is_unknown)

    @property
    def database_connectivity_checks(
        self,
    ) -> tuple[PersistenceHealthCheckResult, ...]:
        return self.checks_by_category(
            PersistenceHealthCheckCategory.DATABASE_CONNECTIVITY,
        )

    @property
    def migration_state_checks(
        self,
    ) -> tuple[PersistenceHealthCheckResult, ...]:
        return self.checks_by_category(
            PersistenceHealthCheckCategory.MIGRATION_STATE,
        )

    @property
    def metadata_table_availability_checks(
        self,
    ) -> tuple[PersistenceHealthCheckResult, ...]:
        return self.checks_by_category(
            PersistenceHealthCheckCategory.METADATA_TABLE_AVAILABILITY,
        )

    @property
    def repository_readiness_checks(
        self,
    ) -> tuple[PersistenceHealthCheckResult, ...]:
        return self.checks_by_category(
            PersistenceHealthCheckCategory.REPOSITORY_READINESS,
        )

    @property
    def service_readiness_checks(
        self,
    ) -> tuple[PersistenceHealthCheckResult, ...]:
        return self.checks_by_category(
            PersistenceHealthCheckCategory.SERVICE_READINESS,
        )

    def checks_by_category(
        self,
        category: PersistenceHealthCheckCategory | str,
    ) -> tuple[PersistenceHealthCheckResult, ...]:
        normalized_category = _coerce_health_category(
            category,
        )
        return tuple(
            check for check in self.checks if check.category is normalized_category
        )

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        return {
            "report_id": self.report_id,
            "checked_at": self.checked_at.isoformat(),
            "status": self.status.value,
            "check_count": len(
                self.checks,
            ),
            "healthy_check_count": len(
                self.healthy_checks,
            ),
            "degraded_check_count": len(
                self.degraded_checks,
            ),
            "unhealthy_check_count": len(
                self.unhealthy_checks,
            ),
            "unknown_check_count": len(
                self.unknown_checks,
            ),
            "checks": tuple(check.as_dict() for check in self.checks),
            "metadata": self.metadata,
        }


def _normalize_health_checks(
    checks: tuple[PersistenceHealthCheckResult, ...],
) -> tuple[PersistenceHealthCheckResult, ...]:
    normalized = tuple(
        checks,
    )
    for check in normalized:
        if not isinstance(
            check,
            PersistenceHealthCheckResult,
        ):
            raise TypeError("checks must contain PersistenceHealthCheckResult records.")
    return normalized


def _coerce_health_category(
    category: PersistenceHealthCheckCategory | str,
) -> PersistenceHealthCheckCategory:
    if isinstance(
        category,
        PersistenceHealthCheckCategory,
    ):
        return category

    normalized = category.strip().lower()
    try:
        return PersistenceHealthCheckCategory(
            normalized,
        )
    except ValueError as exc:
        raise ValueError(
            "health check category must be one of: database_connectivity, "
            "migration_state, metadata_table_availability, "
            "repository_readiness, service_readiness."
        ) from exc


def _coerce_health_status(
    status: PersistenceHealthStatus | str,
) -> PersistenceHealthStatus:
    if isinstance(
        status,
        PersistenceHealthStatus,
    ):
        return status

    normalized = status.strip().lower()
    try:
        return PersistenceHealthStatus(
            normalized,
        )
    except ValueError as exc:
        raise ValueError(
            "health status must be one of: healthy, degraded, unhealthy, unknown."
        ) from exc
