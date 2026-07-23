from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from core.storage.persistence.lineage import (
    JsonObject,
    PersistenceLineage,
    clean_optional_identifier,
    require_non_empty_identifier,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioPositionHistoryRecord:
    """
    Append-only persisted position observation for a portfolio account.

    This record complements the V1 portfolio-state snapshot by capturing the
    position-level facts needed for future exposure, allocation, and RAG
    curation without changing the existing PortfolioState persistence contract.
    """

    position_history_id: str
    account_id: str
    symbol: str
    timestamp: datetime
    quantity: float
    market_value: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    snapshot_id: str | None = None
    cost_basis: float | None = None
    weight: float | None = None
    sector: str | None = None
    theme: str | None = None
    beta: float | None = None
    risk_weight: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "position_history_id",
            require_non_empty_identifier(
                self.position_history_id,
                "position_history_id",
            ),
        )
        _normalize_common_position_fields(self)
        _require_non_negative_float(
            self.quantity,
            "quantity",
        )
        _require_non_negative_float(
            self.market_value,
            "market_value",
        )
        _require_optional_non_negative_float(
            self.cost_basis,
            "cost_basis",
        )
        _require_optional_ratio(
            self.weight,
            "weight",
        )
        _require_optional_ratio(
            self.risk_weight,
            "risk_weight",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioPositionLatestRecord:
    """
    Latest known position state for account + symbol upsert persistence.
    """

    position_latest_id: str
    account_id: str
    symbol: str
    timestamp: datetime
    quantity: float
    market_value: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    snapshot_id: str | None = None
    cost_basis: float | None = None
    weight: float | None = None
    sector: str | None = None
    theme: str | None = None
    beta: float | None = None
    risk_weight: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "position_latest_id",
            require_non_empty_identifier(
                self.position_latest_id,
                "position_latest_id",
            ),
        )
        _normalize_common_position_fields(self)
        _require_non_negative_float(
            self.quantity,
            "quantity",
        )
        _require_non_negative_float(
            self.market_value,
            "market_value",
        )
        _require_optional_non_negative_float(
            self.cost_basis,
            "cost_basis",
        )
        _require_optional_ratio(
            self.weight,
            "weight",
        )
        _require_optional_ratio(
            self.risk_weight,
            "risk_weight",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioExposureSnapshotRecord:
    """
    Append-only portfolio exposure snapshot.

    Exposure values may be positive or negative to support future hedges,
    offsets, and short exposure representations at the persistence boundary.
    """

    exposure_snapshot_id: str
    account_id: str
    timestamp: datetime
    exposure_type: str
    exposure_name: str
    exposure_value: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    snapshot_id: str | None = None
    weight: float | None = None
    beta: float | None = None
    risk_weight: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "exposure_snapshot_id",
            require_non_empty_identifier(
                self.exposure_snapshot_id,
                "exposure_snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "account_id",
            require_non_empty_identifier(
                self.account_id,
                "account_id",
            ),
        )
        object.__setattr__(
            self,
            "exposure_type",
            require_non_empty_identifier(
                self.exposure_type,
                "exposure_type",
            ),
        )
        object.__setattr__(
            self,
            "exposure_name",
            require_non_empty_identifier(
                self.exposure_name,
                "exposure_name",
            ),
        )
        object.__setattr__(
            self,
            "snapshot_id",
            clean_optional_identifier(
                self.snapshot_id,
                "snapshot_id",
            ),
        )
        _require_optional_ratio(
            self.weight,
            "weight",
        )
        _require_optional_ratio(
            self.risk_weight,
            "risk_weight",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioRiskSnapshotRecord:
    """
    Append-only account risk snapshot aligned to the portfolio-state snapshot.
    """

    risk_snapshot_id: str
    account_id: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    snapshot_id: str | None = None
    portfolio_value: float | None = None
    cash: float | None = None
    account_health: str | None = None
    risk_score: float | None = None
    risk_level: str | None = None
    drawdown_risk: float | None = None
    volatility_risk: float | None = None
    concentration_risk: float | None = None
    liquidity_risk: float | None = None
    beta: float | None = None
    cash_ratio: float | None = None
    equity_retention_ratio: float | None = None
    risk_signals: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "risk_snapshot_id",
            require_non_empty_identifier(
                self.risk_snapshot_id,
                "risk_snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "account_id",
            require_non_empty_identifier(
                self.account_id,
                "account_id",
            ),
        )
        object.__setattr__(
            self,
            "snapshot_id",
            clean_optional_identifier(
                self.snapshot_id,
                "snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "account_health",
            clean_optional_identifier(
                self.account_health,
                "account_health",
            ),
        )
        object.__setattr__(
            self,
            "risk_level",
            clean_optional_identifier(
                self.risk_level,
                "risk_level",
            ),
        )
        _require_optional_non_negative_float(
            self.portfolio_value,
            "portfolio_value",
        )
        _require_optional_non_negative_float(
            self.cash,
            "cash",
        )
        _require_optional_ratio(
            self.risk_score,
            "risk_score",
        )
        _require_optional_ratio(
            self.drawdown_risk,
            "drawdown_risk",
        )
        _require_optional_ratio(
            self.volatility_risk,
            "volatility_risk",
        )
        _require_optional_ratio(
            self.concentration_risk,
            "concentration_risk",
        )
        _require_optional_ratio(
            self.liquidity_risk,
            "liquidity_risk",
        )
        _require_optional_ratio(
            self.cash_ratio,
            "cash_ratio",
        )
        _require_optional_ratio(
            self.equity_retention_ratio,
            "equity_retention_ratio",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioAllocationSnapshotRecord:
    """
    Append-only allocation snapshot for current/target portfolio structure.
    """

    allocation_snapshot_id: str
    account_id: str
    timestamp: datetime
    allocation_type: str
    allocation_name: str
    current_weight: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    snapshot_id: str | None = None
    target_weight: float | None = None
    drift: float | None = None
    market_value: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "allocation_snapshot_id",
            require_non_empty_identifier(
                self.allocation_snapshot_id,
                "allocation_snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "account_id",
            require_non_empty_identifier(
                self.account_id,
                "account_id",
            ),
        )
        object.__setattr__(
            self,
            "allocation_type",
            require_non_empty_identifier(
                self.allocation_type,
                "allocation_type",
            ),
        )
        object.__setattr__(
            self,
            "allocation_name",
            require_non_empty_identifier(
                self.allocation_name,
                "allocation_name",
            ),
        )
        object.__setattr__(
            self,
            "snapshot_id",
            clean_optional_identifier(
                self.snapshot_id,
                "snapshot_id",
            ),
        )
        _require_optional_ratio(
            self.current_weight,
            "current_weight",
        )
        _require_optional_ratio(
            self.target_weight,
            "target_weight",
        )
        _require_optional_non_negative_float(
            self.market_value,
            "market_value",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioEquityHistoryPointRecord:
    """Append-only normalized portfolio equity observation."""

    portfolio_equity_history_point_id: str
    account_id: str
    source: str
    timeframe: str
    observed_at: datetime
    equity: float
    profit_loss: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    profit_loss_pct: float | None = None
    base_value: float | None = None
    cashflow_payload: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        for attribute in (
            "portfolio_equity_history_point_id",
            "account_id",
            "source",
            "timeframe",
        ):
            object.__setattr__(
                self,
                attribute,
                require_non_empty_identifier(getattr(self, attribute), attribute),
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware.")
        object.__setattr__(
            self,
            "observed_at",
            self.observed_at.astimezone(UTC),
        )
        _require_optional_non_negative_float(self.equity, "equity")
        _require_optional_non_negative_float(self.base_value, "base_value")


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioExpansionPersistenceBundle:
    """
    Atomic portfolio expansion persistence payload.

    The V1 PortfolioState snapshot remains the account-level source of truth.
    These records add curated position/exposure/risk/allocation facts around
    that snapshot for future history, reporting, and RAG source material.
    """

    equity_history_points: tuple[PortfolioEquityHistoryPointRecord, ...] = ()
    position_history: tuple[PortfolioPositionHistoryRecord, ...] = ()
    position_latest: tuple[PortfolioPositionLatestRecord, ...] = ()
    exposure_snapshots: tuple[PortfolioExposureSnapshotRecord, ...] = ()
    risk_snapshots: tuple[PortfolioRiskSnapshotRecord, ...] = ()
    allocation_snapshots: tuple[PortfolioAllocationSnapshotRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioExpansionPersistenceResult:
    """
    Typed result returned by portfolio expansion persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    account_id: str | None = None
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if self.records_persisted < 0:
            raise ValueError("records_persisted cannot be negative.")

        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")

        if self.success:
            require_non_empty_identifier(
                self.account_id,
                "account_id",
            )

        if not self.success:
            require_non_empty_identifier(
                self.error,
                "error",
            )

    @classmethod
    def succeeded(
        cls,
        *,
        account_id: str,
        records_persisted: int = 0,
    ) -> PortfolioExpansionPersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            account_id=account_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> PortfolioExpansionPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_portfolio_equity_history_point_id(
    *,
    account_id: str,
    source: str,
    timeframe: str,
    observed_at: datetime,
) -> str:
    clean_account_id = require_non_empty_identifier(account_id, "account_id")
    clean_source = require_non_empty_identifier(source, "source")
    clean_timeframe = require_non_empty_identifier(timeframe, "timeframe")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware.")
    normalized_observed_at = observed_at.astimezone(UTC)
    return ":".join(
        (
            "portfolio_equity_history_point",
            clean_account_id,
            clean_source,
            clean_timeframe,
            normalized_observed_at.isoformat(),
        )
    )


def new_portfolio_position_history_id(
    *,
    account_id: str,
    symbol: str,
    timestamp: datetime,
    execution_id: str | None = None,
    position_key: str | None = None,
) -> str:
    clean_account_id = require_non_empty_identifier(
        account_id,
        "account_id",
    )
    clean_symbol = require_non_empty_identifier(
        symbol,
        "symbol",
    ).upper()
    clean_execution_id = clean_optional_identifier(
        execution_id,
        "execution_id",
    )
    clean_position_key = clean_optional_identifier(
        position_key,
        "position_key",
    )

    if clean_execution_id is None:
        return f"portfolio_position_history:{clean_account_id}:{clean_symbol}:{uuid4().hex}"  # noqa: E501

    parts = [
        "portfolio_position_history",
        clean_execution_id,
        clean_account_id,
        clean_symbol,
        timestamp.isoformat(),
    ]
    if clean_position_key is not None:
        parts.append(clean_position_key)
    return ":".join(parts)


def new_portfolio_position_latest_id(
    *,
    account_id: str,
    symbol: str,
) -> str:
    clean_account_id = require_non_empty_identifier(
        account_id,
        "account_id",
    )
    clean_symbol = require_non_empty_identifier(
        symbol,
        "symbol",
    ).upper()

    return f"portfolio_position_latest:{clean_account_id}:{clean_symbol}"


def new_portfolio_exposure_snapshot_id(
    *,
    account_id: str,
    exposure_type: str,
    exposure_name: str,
    timestamp: datetime,
    execution_id: str | None = None,
) -> str:
    return _new_portfolio_snapshot_id(
        record_type="portfolio_exposure_snapshot",
        account_id=account_id,
        timestamp=timestamp,
        execution_id=execution_id,
        parts=(exposure_type, exposure_name),
    )


def new_portfolio_risk_snapshot_id(
    *,
    account_id: str,
    timestamp: datetime,
    execution_id: str | None = None,
    risk_key: str | None = None,
) -> str:
    parts = (risk_key,) if risk_key is not None else ()
    return _new_portfolio_snapshot_id(
        record_type="portfolio_risk_snapshot",
        account_id=account_id,
        timestamp=timestamp,
        execution_id=execution_id,
        parts=parts,
    )


def new_portfolio_allocation_snapshot_id(
    *,
    account_id: str,
    allocation_type: str,
    allocation_name: str,
    timestamp: datetime,
    execution_id: str | None = None,
) -> str:
    return _new_portfolio_snapshot_id(
        record_type="portfolio_allocation_snapshot",
        account_id=account_id,
        timestamp=timestamp,
        execution_id=execution_id,
        parts=(allocation_type, allocation_name),
    )


def _new_portfolio_snapshot_id(
    *,
    record_type: str,
    account_id: str,
    timestamp: datetime,
    execution_id: str | None,
    parts: tuple[str | None, ...] = (),
) -> str:
    clean_record_type = require_non_empty_identifier(
        record_type,
        "record_type",
    )
    clean_account_id = require_non_empty_identifier(
        account_id,
        "account_id",
    )
    clean_execution_id = clean_optional_identifier(
        execution_id,
        "execution_id",
    )
    clean_parts = tuple(
        require_non_empty_identifier(
            value,
            "snapshot_part",
        )
        for value in parts
        if value is not None
    )

    if clean_execution_id is None:
        return f"{clean_record_type}:{clean_account_id}:{uuid4().hex}"

    return ":".join(
        (
            clean_record_type,
            clean_execution_id,
            clean_account_id,
            timestamp.isoformat(),
            *clean_parts,
        )
    )


def _normalize_common_position_fields(
    record: PortfolioPositionHistoryRecord | PortfolioPositionLatestRecord,
) -> None:
    object.__setattr__(
        record,
        "account_id",
        require_non_empty_identifier(
            record.account_id,
            "account_id",
        ),
    )
    object.__setattr__(
        record,
        "symbol",
        require_non_empty_identifier(
            record.symbol,
            "symbol",
        ).upper(),
    )
    object.__setattr__(
        record,
        "snapshot_id",
        clean_optional_identifier(
            record.snapshot_id,
            "snapshot_id",
        ),
    )
    object.__setattr__(
        record,
        "sector",
        clean_optional_identifier(
            record.sector,
            "sector",
        ),
    )
    object.__setattr__(
        record,
        "theme",
        clean_optional_identifier(
            record.theme,
            "theme",
        ),
    )


def _require_non_negative_float(
    value: float,
    field_name: str,
) -> None:
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")


def _require_optional_non_negative_float(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return

    _require_non_negative_float(
        value,
        field_name,
    )


def _require_optional_ratio(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if value < 0.0 or value > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
