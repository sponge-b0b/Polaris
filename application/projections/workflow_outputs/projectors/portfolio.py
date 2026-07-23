from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import fields
from datetime import UTC, datetime
from typing import Any, Final, cast

from application.persistence.portfolio import PortfolioPersistenceService
from application.projections.workflow_outputs.projection_identity import (
    build_projected_record_id,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectorRegistration,
)
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.portfolio import (
    PortfolioAllocationSnapshotRecord,
    PortfolioEquityHistoryPointRecord,
    PortfolioExposureSnapshotRecord,
    PortfolioPositionHistoryRecord,
    PortfolioPositionLatestRecord,
    PortfolioRiskSnapshotRecord,
    new_portfolio_allocation_snapshot_id,
    new_portfolio_equity_history_point_id,
    new_portfolio_exposure_snapshot_id,
    new_portfolio_position_history_id,
    new_portfolio_position_latest_id,
    new_portfolio_risk_snapshot_id,
)
from domain.portfolio.models.portfolio_state import PortfolioState
from domain.workflow_outputs import (
    PORTFOLIO_STATE_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)

PORTFOLIO_STATE_PROJECTOR_NAME: Final = "portfolio_state_projector"
PORTFOLIO_STATE_PROJECTOR_NODE_NAMES: Final = ("portfolio_state_builder",)
CANONICAL_PORTFOLIO_STATE_FIELD: Final = "canonical_portfolio_state"
PORTFOLIO_EQUITY_HISTORY_POINTS_FIELD: Final = "equity_history_points"
PORTFOLIO_POSITIONS_FIELD: Final = "positions"
PORTFOLIO_EXPOSURES_FIELD: Final = "exposures"
PORTFOLIO_RISK_METRICS_FIELD: Final = "risk_metrics"
PORTFOLIO_ALLOCATION_DATA_FIELD: Final = "allocation_data"

_PORTFOLIO_SCALAR_EXPOSURE_FIELDS: Final[tuple[str, ...]] = (
    "gross_exposure",
    "net_exposure",
    "long_exposure",
    "short_exposure",
    "leverage",
    "long_market_value",
    "short_market_value",
    "gross_market_value",
    "net_market_value",
)


class PortfolioStateWorkflowOutputProjector:
    """Project portfolio-state workflow evidence into curated portfolio records."""

    def __init__(
        self,
        portfolio_persistence_service: PortfolioPersistenceService,
    ) -> None:
        self._portfolio_persistence_service = portfolio_persistence_service

    @property
    def projector_name(self) -> str:
        return PORTFOLIO_STATE_PROJECTOR_NAME

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        outputs = _mapping(request.node_output.outputs)
        state_payload = _mapping(outputs.get(CANONICAL_PORTFOLIO_STATE_FIELD))
        if not state_payload:
            return _skipped(
                request,
                "Portfolio output has no canonical_portfolio_state payload.",
            )

        observed_at = _parse_timestamp(state_payload.get("timestamp"))
        if observed_at is None:
            return _skipped(
                request,
                "Portfolio output is missing canonical state timestamp.",
            )

        account_id = _optional_identifier(state_payload.get("account_id"))
        if account_id is None:
            return _skipped(
                request,
                "Portfolio output is missing canonical state account_id.",
            )

        snapshot_id = build_projected_record_id(
            record_type="portfolio_state_snapshot",
            execution_id=request.lineage.execution_id or request.run.execution_id,
            node_name=request.lineage.node_name or request.node_output.node_name,
            domain_natural_key=account_id,
            source_timestamp=observed_at,
        )
        state = _portfolio_state_from_payload(
            payload=state_payload,
            snapshot_id=snapshot_id,
        )
        metadata = _projection_metadata(request)
        execution_id = request.lineage.execution_id or request.run.execution_id

        positions = tuple(_sequence_of_mappings(outputs.get(PORTFOLIO_POSITIONS_FIELD)))
        position_history = _build_position_history_records(
            request=request,
            account_id=account_id,
            timestamp=observed_at,
            snapshot_id=snapshot_id,
            positions=positions,
            metadata=metadata,
            execution_id=execution_id,
        )
        latest_positions = _build_latest_position_records(
            request=request,
            account_id=account_id,
            timestamp=observed_at,
            snapshot_id=snapshot_id,
            positions=positions,
            metadata=metadata,
        )
        equity_history = _build_equity_history_records(
            request=request,
            account_id=account_id,
            equity_points=tuple(
                _sequence_of_mappings(
                    outputs.get(PORTFOLIO_EQUITY_HISTORY_POINTS_FIELD)
                )
            ),
        )
        exposure_snapshots = _build_exposure_snapshot_records(
            account_id=account_id,
            timestamp=observed_at,
            snapshot_id=snapshot_id,
            exposures=_mapping(outputs.get(PORTFOLIO_EXPOSURES_FIELD)),
            state_payload=state_payload,
            metadata=metadata,
            execution_id=execution_id,
            lineage=request.lineage,
        )
        risk_snapshots = _build_risk_snapshot_records(
            account_id=account_id,
            timestamp=observed_at,
            snapshot_id=snapshot_id,
            risk_metrics=_mapping(outputs.get(PORTFOLIO_RISK_METRICS_FIELD)),
            state_payload=state_payload,
            metadata=metadata,
            execution_id=execution_id,
            lineage=request.lineage,
        )
        allocation_snapshots = _build_allocation_snapshot_records(
            account_id=account_id,
            timestamp=observed_at,
            snapshot_id=snapshot_id,
            allocation_data=_mapping(outputs.get(PORTFOLIO_ALLOCATION_DATA_FIELD)),
            positions=positions,
            state_payload=state_payload,
            metadata=metadata,
            execution_id=execution_id,
            lineage=request.lineage,
        )

        try:
            await self._portfolio_persistence_service.persist_state_snapshot(state)
            result = (
                await self._portfolio_persistence_service.persist_expansion_records(
                    equity_history_points=equity_history,
                    position_history=position_history,
                    position_latest=latest_positions,
                    exposure_snapshots=exposure_snapshots,
                    risk_snapshots=risk_snapshots,
                    allocation_snapshots=allocation_snapshots,
                )
            )
        except Exception as exc:  # pragma: no cover - exercised by integration adapters
            return _failed(
                request,
                str(exc),
            )

        if not result.success:
            return _failed(request, result.error or "Portfolio persistence failed.")

        return _outcome(
            request=request,
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            records_written=result.records_persisted + 1,
            message="Portfolio output projected into curated portfolio records.",
        )


def build_portfolio_state_projector_registration(
    portfolio_persistence_service: PortfolioPersistenceService,
) -> WorkflowOutputProjectorRegistration:
    """Build the canonical portfolio-state projector registration."""
    projector = PortfolioStateWorkflowOutputProjector(portfolio_persistence_service)
    return WorkflowOutputProjectorRegistration(
        projector_name=PORTFOLIO_STATE_PROJECTOR_NAME,
        output_contract=PORTFOLIO_STATE_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        projector=projector,
        supported_node_names=PORTFOLIO_STATE_PROJECTOR_NODE_NAMES,
    )


def _portfolio_state_from_payload(
    *,
    payload: Mapping[str, object],
    snapshot_id: str,
) -> PortfolioState:
    kwargs: dict[str, Any] = {}
    for field in fields(PortfolioState):
        value = payload.get(field.name)
        if field.name == "timestamp":
            kwargs[field.name] = _parse_timestamp(value) or _required_timestamp(value)
        elif field.name in {"sector_exposure", "asset_class_exposure"}:
            kwargs[field.name] = _float_mapping(value)
        elif field.name == "risk_signals":
            kwargs[field.name] = _json_mapping(value)
        elif field.name == "snapshot_id":
            kwargs[field.name] = snapshot_id
        elif value is not None:
            kwargs[field.name] = value

    return PortfolioState(**kwargs)


def _required_timestamp(value: object) -> datetime:
    raise ValueError(f"portfolio state timestamp is invalid: {value!r}")


def _build_position_history_records(
    *,
    request: WorkflowOutputProjectorRequest,
    account_id: str,
    timestamp: datetime,
    snapshot_id: str,
    positions: tuple[Mapping[str, object], ...],
    metadata: JsonObject,
    execution_id: str,
) -> tuple[PortfolioPositionHistoryRecord, ...]:
    records: list[PortfolioPositionHistoryRecord] = []
    for index, position in enumerate(positions):
        symbol = _optional_symbol(position.get("symbol"))
        quantity = _coalesce_float(position.get("quantity"), position.get("qty"))
        market_value = _optional_float(position.get("market_value"))
        if symbol is None or quantity is None or market_value is None:
            continue
        records.append(
            PortfolioPositionHistoryRecord(
                position_history_id=new_portfolio_position_history_id(
                    account_id=account_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    execution_id=execution_id,
                    position_key=f"{request.node_output.node_output_id}:{index}",
                ),
                account_id=account_id,
                symbol=symbol,
                timestamp=timestamp,
                quantity=max(0.0, quantity),
                market_value=max(0.0, market_value),
                lineage=request.lineage,
                snapshot_id=snapshot_id,
                cost_basis=_optional_non_negative_float(position.get("cost_basis")),
                weight=_coalesce_ratio(
                    position.get("weight"),
                    position.get("exposure_weight"),
                ),
                sector=_optional_identifier(position.get("sector")),
                theme=_optional_identifier(position.get("theme")),
                beta=_optional_float(position.get("beta")),
                risk_weight=_optional_ratio(position.get("risk_weight")),
                metadata=metadata,
            )
        )
    return tuple(records)


def _build_latest_position_records(
    *,
    request: WorkflowOutputProjectorRequest,
    account_id: str,
    timestamp: datetime,
    snapshot_id: str,
    positions: tuple[Mapping[str, object], ...],
    metadata: JsonObject,
) -> tuple[PortfolioPositionLatestRecord, ...]:
    records: list[PortfolioPositionLatestRecord] = []
    for position in positions:
        symbol = _optional_symbol(position.get("symbol"))
        quantity = _coalesce_float(position.get("quantity"), position.get("qty"))
        market_value = _optional_float(position.get("market_value"))
        if symbol is None or quantity is None or market_value is None:
            continue
        records.append(
            PortfolioPositionLatestRecord(
                position_latest_id=new_portfolio_position_latest_id(
                    account_id=account_id,
                    symbol=symbol,
                ),
                account_id=account_id,
                symbol=symbol,
                timestamp=timestamp,
                quantity=max(0.0, quantity),
                market_value=max(0.0, market_value),
                lineage=request.lineage,
                snapshot_id=snapshot_id,
                cost_basis=_optional_non_negative_float(position.get("cost_basis")),
                weight=_coalesce_ratio(
                    position.get("weight"),
                    position.get("exposure_weight"),
                ),
                sector=_optional_identifier(position.get("sector")),
                theme=_optional_identifier(position.get("theme")),
                beta=_optional_float(position.get("beta")),
                risk_weight=_optional_ratio(position.get("risk_weight")),
                metadata=metadata,
            )
        )
    return tuple(records)


def _build_equity_history_records(
    *,
    request: WorkflowOutputProjectorRequest,
    account_id: str,
    equity_points: tuple[Mapping[str, object], ...],
) -> tuple[PortfolioEquityHistoryPointRecord, ...]:
    records: list[PortfolioEquityHistoryPointRecord] = []
    for point in equity_points:
        source = _optional_identifier(point.get("source"))
        timeframe = _optional_identifier(point.get("timeframe"))
        observed_at = _parse_timestamp(point.get("observed_at"))
        equity = _optional_float(point.get("equity"))
        profit_loss = _optional_float(point.get("profit_loss"))
        if (
            source is None
            or timeframe is None
            or observed_at is None
            or equity is None
            or profit_loss is None
        ):
            continue
        records.append(
            PortfolioEquityHistoryPointRecord(
                portfolio_equity_history_point_id=(
                    new_portfolio_equity_history_point_id(
                        account_id=account_id,
                        source=source,
                        timeframe=timeframe,
                        observed_at=observed_at,
                    )
                ),
                account_id=account_id,
                source=source,
                timeframe=timeframe,
                observed_at=observed_at,
                equity=max(0.0, equity),
                profit_loss=profit_loss,
                lineage=request.lineage,
                profit_loss_pct=_optional_float(point.get("profit_loss_pct")),
                base_value=_optional_non_negative_float(point.get("base_value")),
                cashflow_payload=_json_mapping(point.get("cashflow_payload")),
            )
        )
    return tuple(records)


def _build_exposure_snapshot_records(
    *,
    account_id: str,
    timestamp: datetime,
    snapshot_id: str,
    exposures: Mapping[str, object],
    state_payload: Mapping[str, object],
    metadata: JsonObject,
    execution_id: str,
    lineage: object,
) -> tuple[PortfolioExposureSnapshotRecord, ...]:
    records: list[PortfolioExposureSnapshotRecord] = []
    payloads: tuple[Mapping[str, object], ...] = (exposures, state_payload)
    for field_name in _PORTFOLIO_SCALAR_EXPOSURE_FIELDS:
        value = _first_float(field_name, *payloads)
        if value is None:
            continue
        records.append(
            _exposure_record(
                account_id=account_id,
                timestamp=timestamp,
                snapshot_id=snapshot_id,
                exposure_type="portfolio_metric",
                exposure_name=field_name,
                exposure_value=value,
                weight=_ratio_or_none(value),
                metadata=metadata,
                execution_id=execution_id,
                lineage=lineage,
            )
        )

    for exposure_type, exposure_map in (
        ("sector", _float_mapping(_first_value("sector_exposure", *payloads))),
        (
            "asset_class",
            _float_mapping(_first_value("asset_class_exposure", *payloads)),
        ),
    ):
        for exposure_name, exposure_value in sorted(exposure_map.items()):
            records.append(
                _exposure_record(
                    account_id=account_id,
                    timestamp=timestamp,
                    snapshot_id=snapshot_id,
                    exposure_type=exposure_type,
                    exposure_name=exposure_name,
                    exposure_value=exposure_value,
                    weight=_ratio_or_none(exposure_value),
                    metadata=metadata,
                    execution_id=execution_id,
                    lineage=lineage,
                )
            )

    return tuple(records)


def _exposure_record(
    *,
    account_id: str,
    timestamp: datetime,
    snapshot_id: str,
    exposure_type: str,
    exposure_name: str,
    exposure_value: float,
    weight: float | None,
    metadata: JsonObject,
    execution_id: str,
    lineage: object,
) -> PortfolioExposureSnapshotRecord:
    return PortfolioExposureSnapshotRecord(
        exposure_snapshot_id=new_portfolio_exposure_snapshot_id(
            account_id=account_id,
            exposure_type=exposure_type,
            exposure_name=exposure_name,
            timestamp=timestamp,
            execution_id=execution_id,
        ),
        account_id=account_id,
        timestamp=timestamp,
        exposure_type=exposure_type,
        exposure_name=exposure_name,
        exposure_value=exposure_value,
        lineage=cast(Any, lineage),
        snapshot_id=snapshot_id,
        weight=weight,
        metadata=metadata,
    )


def _build_risk_snapshot_records(
    *,
    account_id: str,
    timestamp: datetime,
    snapshot_id: str,
    risk_metrics: Mapping[str, object],
    state_payload: Mapping[str, object],
    metadata: JsonObject,
    execution_id: str,
    lineage: object,
) -> tuple[PortfolioRiskSnapshotRecord, ...]:
    risk_score = _coalesce_ratio(
        risk_metrics.get("risk_score"),
        risk_metrics.get("risk_intensity"),
        state_payload.get("risk_intensity"),
    )
    return (
        PortfolioRiskSnapshotRecord(
            risk_snapshot_id=new_portfolio_risk_snapshot_id(
                account_id=account_id,
                timestamp=timestamp,
                execution_id=execution_id,
                risk_key="portfolio",
            ),
            account_id=account_id,
            timestamp=timestamp,
            lineage=cast(Any, lineage),
            snapshot_id=snapshot_id,
            portfolio_value=_optional_non_negative_float(
                state_payload.get("portfolio_value")
            ),
            cash=_optional_non_negative_float(state_payload.get("cash")),
            account_health=_coalesce_identifier(
                risk_metrics.get("account_health"),
                state_payload.get("account_health"),
            ),
            risk_score=risk_score,
            risk_level=_risk_level(risk_score),
            drawdown_risk=_coalesce_ratio(
                risk_metrics.get("drawdown_risk"),
                risk_metrics.get("drawdown_percent"),
                state_payload.get("drawdown_percent"),
            ),
            concentration_risk=_coalesce_ratio(
                risk_metrics.get("concentration_risk"),
                risk_metrics.get("concentration"),
                state_payload.get("concentration_score"),
            ),
            beta=_coalesce_float(
                risk_metrics.get("beta_exposure"),
                state_payload.get("beta_exposure"),
            ),
            cash_ratio=_coalesce_ratio(
                risk_metrics.get("cash_ratio"),
                risk_metrics.get("cash_buffer"),
                state_payload.get("cash_ratio"),
            ),
            equity_retention_ratio=_optional_ratio(
                state_payload.get("equity_retention_ratio")
            ),
            risk_signals=_json_mapping(state_payload.get("risk_signals")),
            metadata=metadata,
        ),
    )


def _build_allocation_snapshot_records(
    *,
    account_id: str,
    timestamp: datetime,
    snapshot_id: str,
    allocation_data: Mapping[str, object],
    positions: tuple[Mapping[str, object], ...],
    state_payload: Mapping[str, object],
    metadata: JsonObject,
    execution_id: str,
    lineage: object,
) -> tuple[PortfolioAllocationSnapshotRecord, ...]:
    records: list[PortfolioAllocationSnapshotRecord] = []
    for position in positions or tuple(
        _sequence_of_mappings(allocation_data.get("positions"))
    ):
        symbol = _optional_symbol(position.get("symbol"))
        weight = _coalesce_ratio(
            position.get("current_weight"),
            position.get("weight"),
            position.get("exposure_weight"),
        )
        if symbol is None or weight is None:
            continue
        records.append(
            _allocation_record(
                account_id=account_id,
                timestamp=timestamp,
                snapshot_id=snapshot_id,
                allocation_type="position",
                allocation_name=symbol,
                current_weight=weight,
                market_value=_optional_non_negative_float(position.get("market_value")),
                metadata=metadata,
                execution_id=execution_id,
                lineage=lineage,
            )
        )

    for allocation_type, values in (
        (
            "sector",
            _float_mapping(
                _first_value(
                    "sector_exposure",
                    allocation_data,
                    state_payload,
                )
            ),
        ),
        (
            "asset_class",
            _float_mapping(
                _first_value(
                    "asset_class_exposure",
                    allocation_data,
                    state_payload,
                )
            ),
        ),
    ):
        for allocation_name, current_weight in sorted(values.items()):
            ratio = _ratio_or_none(current_weight)
            if ratio is None:
                continue
            records.append(
                _allocation_record(
                    account_id=account_id,
                    timestamp=timestamp,
                    snapshot_id=snapshot_id,
                    allocation_type=allocation_type,
                    allocation_name=allocation_name,
                    current_weight=ratio,
                    market_value=None,
                    metadata=metadata,
                    execution_id=execution_id,
                    lineage=lineage,
                )
            )
    return tuple(records)


def _allocation_record(
    *,
    account_id: str,
    timestamp: datetime,
    snapshot_id: str,
    allocation_type: str,
    allocation_name: str,
    current_weight: float,
    market_value: float | None,
    metadata: JsonObject,
    execution_id: str,
    lineage: object,
) -> PortfolioAllocationSnapshotRecord:
    return PortfolioAllocationSnapshotRecord(
        allocation_snapshot_id=new_portfolio_allocation_snapshot_id(
            account_id=account_id,
            allocation_type=allocation_type,
            allocation_name=allocation_name,
            timestamp=timestamp,
            execution_id=execution_id,
        ),
        account_id=account_id,
        timestamp=timestamp,
        allocation_type=allocation_type,
        allocation_name=allocation_name,
        current_weight=current_weight,
        lineage=cast(Any, lineage),
        snapshot_id=snapshot_id,
        market_value=market_value,
        metadata=metadata,
    )


def _outcome(
    *,
    request: WorkflowOutputProjectorRequest,
    status: WorkflowOutputProjectionStatus,
    records_written: int = 0,
    message: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> WorkflowOutputProjectionOutcome:
    completed_at = datetime.now(UTC)
    return WorkflowOutputProjectionOutcome(
        status=status,
        projector_name=PORTFOLIO_STATE_PROJECTOR_NAME,
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract
        or PORTFOLIO_STATE_OUTPUT_CONTRACT,
        output_schema_version=request.node_output.output_schema_version
        or WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        source_fingerprint=request.source_fingerprint,
        records_written=records_written,
        message=message,
        error_type=error_type,
        error_message=error_message,
        completed_at=completed_at,
    )


def _skipped(
    request: WorkflowOutputProjectorRequest,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return _outcome(
        request=request,
        status=WorkflowOutputProjectionStatus.SKIPPED,
        message=message,
    )


def _failed(
    request: WorkflowOutputProjectorRequest,
    error: str,
) -> WorkflowOutputProjectionOutcome:
    return _outcome(
        request=request,
        status=WorkflowOutputProjectionStatus.FAILED,
        error_type="portfolio_persistence_failed",
        error_message=error,
        message="Portfolio projection failed during persistence.",
    )


def _projection_metadata(request: WorkflowOutputProjectorRequest) -> JsonObject:
    quality_status = _optional_identifier(
        request.node_output.metadata.get("quality_status")
    )
    return _compact_json_object(
        {
            "source_fingerprint": request.source_fingerprint,
            "quality_status": quality_status,
            "projector_name": PORTFOLIO_STATE_PROJECTOR_NAME,
            "node_output_id": request.node_output.node_output_id,
            "provider_source": _optional_identifier(
                request.node_output.outputs.get("provider_source")
            ),
            "history_period": _optional_identifier(
                request.node_output.outputs.get("history_period")
            ),
            "history_timeframe": _optional_identifier(
                request.node_output.outputs.get("history_timeframe")
            ),
        }
    )


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return None
        if raw_value.endswith("Z"):
            raw_value = f"{raw_value[:-1]}+00:00"
        try:
            timestamp = datetime.fromisoformat(raw_value)
        except ValueError:
            return None
    else:
        return None

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def _sequence_of_mappings(value: object) -> Iterable[Mapping[str, object]]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(_mapping(item) for item in value if isinstance(item, Mapping))


def _json_mapping(value: object) -> JsonObject:
    if isinstance(value, Mapping):
        return cast(JsonObject, dict(value))
    if isinstance(value, list | tuple):
        return cast(JsonObject, {"items": list(value)})
    return {}


def _compact_json_object(payload: Mapping[str, object | None]) -> JsonObject:
    return cast(
        JsonObject,
        {key: value for key, value in payload.items() if value is not None},
    )


def _optional_identifier(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _optional_symbol(value: object) -> str | None:
    symbol = _optional_identifier(value)
    return symbol.upper() if symbol is not None else None


def _coalesce_identifier(*values: object) -> str | None:
    for value in values:
        cleaned = _optional_identifier(value)
        if cleaned is not None:
            return cleaned
    return None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _coalesce_float(*values: object) -> float | None:
    for value in values:
        cleaned = _optional_float(value)
        if cleaned is not None:
            return cleaned
    return None


def _optional_non_negative_float(value: object) -> float | None:
    cleaned = _optional_float(value)
    if cleaned is None:
        return None
    return max(0.0, cleaned)


def _optional_ratio(value: object) -> float | None:
    cleaned = _optional_float(value)
    if cleaned is None or not 0.0 <= cleaned <= 1.0:
        return None
    return cleaned


def _coalesce_ratio(*values: object) -> float | None:
    for value in values:
        cleaned = _optional_ratio(value)
        if cleaned is not None:
            return cleaned
    return None


def _ratio_or_none(value: object) -> float | None:
    return _optional_ratio(value)


def _first_value(field_name: str, *payloads: Mapping[str, object]) -> object | None:
    for payload in payloads:
        if field_name in payload:
            return payload[field_name]
    return None


def _first_float(field_name: str, *payloads: Mapping[str, object]) -> float | None:
    return _optional_float(_first_value(field_name, *payloads))


def _float_mapping(value: object) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    mapped: dict[str, float] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            continue
        cleaned = _optional_float(item)
        if cleaned is None:
            continue
        mapped[key] = cleaned
    return mapped


def _risk_level(risk_score: float | None) -> str | None:
    if risk_score is None:
        return None
    if risk_score >= 0.75:
        return "high"
    if risk_score >= 0.45:
        return "medium"
    return "low"
