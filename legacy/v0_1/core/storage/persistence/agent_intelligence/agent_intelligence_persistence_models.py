from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, cast
from uuid import uuid4

from core.storage.persistence.lineage import (
    JsonObject,
    PersistenceLineage,
    PersistenceRecordIdentity,
    clean_optional_identifier,
    require_non_empty_identifier,
)
from domain.llm import (
    sanitize_reasoning_trace_payload,
    sanitize_reasoning_trace_text_for_boundary,
)


class _CommonOptionalFieldsRecord(Protocol):
    @property
    def symbol(self) -> str | None: ...

    @property
    def universe(self) -> str | None: ...


@dataclass(
    frozen=True,
    slots=True,
)
class AgentReasoningRecord:
    """
    Append-friendly full reasoning record linked to an agent signal.

    This record preserves full, untruncated reasoning and optional LLM output at
    the persistence boundary. Intelligence agents should work with typed domain
    signals internally and create this record only when durable audit/history is
    required.
    """

    reasoning_id: str
    agent_signal_id: str
    agent_name: str
    agent_type: str
    timestamp: datetime
    reasoning_text: str
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    symbol: str | None = None
    universe: str | None = None
    reasoning_type: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    full_llm_response: str | None = None
    inputs: JsonObject = field(default_factory=dict)
    outputs: JsonObject = field(default_factory=dict)
    linked_records: tuple[PersistenceRecordIdentity, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(
            self,
            "reasoning_id",
            self.reasoning_id,
        )
        _set_required_identifier(
            self,
            "agent_signal_id",
            self.agent_signal_id,
        )
        _set_required_identifier(
            self,
            "agent_name",
            self.agent_name,
        )
        _set_required_identifier(
            self,
            "agent_type",
            self.agent_type,
        )
        _set_required_text(
            self,
            "reasoning_text",
            self.reasoning_text,
        )
        _set_common_optional_fields(
            self,
        )
        object.__setattr__(
            self,
            "reasoning_type",
            clean_optional_identifier(
                self.reasoning_type,
                "reasoning_type",
            ),
        )
        object.__setattr__(
            self,
            "model_name",
            clean_optional_identifier(
                self.model_name,
                "model_name",
            ),
        )
        object.__setattr__(
            self,
            "prompt_version",
            clean_optional_identifier(
                self.prompt_version,
                "prompt_version",
            ),
        )
        object.__setattr__(
            self,
            "full_llm_response",
            _clean_optional_model_text(
                self.full_llm_response,
                boundary_name="AgentReasoningRecord.full_llm_response",
            ),
        )
        _set_sanitized_json_object_fields(
            self,
            "inputs",
            "outputs",
            "metadata",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AgentRecommendationRecord:
    """
    Agent-level recommendation output linked to an agent signal.

    This is not an autonomous execution instruction. It captures the agent's
    typed recommendation contribution and full rationale for audit,
    attribution, reporting, and future curated RAG projections.
    """

    agent_recommendation_id: str
    agent_signal_id: str
    agent_name: str
    agent_type: str
    timestamp: datetime
    recommendation_type: str
    recommendation_text: str
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    symbol: str | None = None
    universe: str | None = None
    bias: str | None = None
    action: str | None = None
    confidence: float | None = None
    conviction: float | None = None
    time_horizon: str | None = None
    rationale_text: str | None = None
    full_llm_response: str | None = None
    supporting_signals: tuple[PersistenceRecordIdentity, ...] = ()
    inputs: JsonObject = field(default_factory=dict)
    outputs: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(
            self,
            "agent_recommendation_id",
            self.agent_recommendation_id,
        )
        _set_required_identifier(
            self,
            "agent_signal_id",
            self.agent_signal_id,
        )
        _set_required_identifier(
            self,
            "agent_name",
            self.agent_name,
        )
        _set_required_identifier(
            self,
            "agent_type",
            self.agent_type,
        )
        _set_required_identifier(
            self,
            "recommendation_type",
            self.recommendation_type,
        )
        _set_required_text(
            self,
            "recommendation_text",
            self.recommendation_text,
        )
        _set_common_optional_fields(
            self,
        )
        object.__setattr__(
            self,
            "bias",
            clean_optional_identifier(
                self.bias,
                "bias",
            ),
        )
        object.__setattr__(
            self,
            "action",
            clean_optional_identifier(
                self.action,
                "action",
            ),
        )
        object.__setattr__(
            self,
            "time_horizon",
            clean_optional_identifier(
                self.time_horizon,
                "time_horizon",
            ),
        )
        object.__setattr__(
            self,
            "rationale_text",
            _clean_optional_model_text(
                self.rationale_text,
                boundary_name="AgentRecommendationRecord.rationale_text",
            ),
        )
        object.__setattr__(
            self,
            "full_llm_response",
            _clean_optional_model_text(
                self.full_llm_response,
                boundary_name="AgentRecommendationRecord.full_llm_response",
            ),
        )
        _set_sanitized_json_object_fields(
            self,
            "inputs",
            "outputs",
            "metadata",
        )
        _require_optional_ratio(
            self.confidence,
            "confidence",
        )
        _require_optional_ratio(
            self.conviction,
            "conviction",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AgentRiskAssessmentRecord:
    """
    Agent-level risk assessment linked to an agent signal.
    """

    risk_assessment_id: str
    agent_signal_id: str
    agent_name: str
    agent_type: str
    timestamp: datetime
    risk_type: str
    assessment_text: str
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    symbol: str | None = None
    universe: str | None = None
    risk_level: str | None = None
    risk_score: float | None = None
    confidence: float | None = None
    mitigation: str | None = None
    full_llm_response: str | None = None
    inputs: JsonObject = field(default_factory=dict)
    outputs: JsonObject = field(default_factory=dict)
    supporting_signals: tuple[PersistenceRecordIdentity, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(
            self,
            "risk_assessment_id",
            self.risk_assessment_id,
        )
        _set_required_identifier(
            self,
            "agent_signal_id",
            self.agent_signal_id,
        )
        _set_required_identifier(
            self,
            "agent_name",
            self.agent_name,
        )
        _set_required_identifier(
            self,
            "agent_type",
            self.agent_type,
        )
        _set_required_identifier(
            self,
            "risk_type",
            self.risk_type,
        )
        _set_required_text(
            self,
            "assessment_text",
            self.assessment_text,
        )
        _set_common_optional_fields(
            self,
        )
        object.__setattr__(
            self,
            "risk_level",
            clean_optional_identifier(
                self.risk_level,
                "risk_level",
            ),
        )
        object.__setattr__(
            self,
            "mitigation",
            _clean_optional_model_text(
                self.mitigation,
                boundary_name="AgentRiskAssessmentRecord.mitigation",
            ),
        )
        object.__setattr__(
            self,
            "full_llm_response",
            _clean_optional_model_text(
                self.full_llm_response,
                boundary_name="AgentRiskAssessmentRecord.full_llm_response",
            ),
        )
        _set_sanitized_json_object_fields(
            self,
            "inputs",
            "outputs",
            "metadata",
        )
        _require_optional_ratio(
            self.risk_score,
            "risk_score",
        )
        _require_optional_ratio(
            self.confidence,
            "confidence",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AgentIntelligencePersistenceBundle:
    """
    Atomic enriched agent-intelligence persistence payload.
    """

    reasoning: tuple[AgentReasoningRecord, ...] = ()
    recommendations: tuple[AgentRecommendationRecord, ...] = ()
    risk_assessments: tuple[AgentRiskAssessmentRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class AgentIntelligencePersistenceResult:
    """
    Typed result returned by agent-intelligence persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    primary_record_id: str | None = None
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
                self.primary_record_id,
                "primary_record_id",
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
        primary_record_id: str,
        records_persisted: int = 1,
    ) -> AgentIntelligencePersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            primary_record_id=primary_record_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> AgentIntelligencePersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_agent_reasoning_id(
    *,
    agent_signal_id: str,
    timestamp: datetime,
    reasoning_key: str | None = None,
) -> str:
    return _new_agent_intelligence_id(
        prefix="agent_reasoning",
        agent_signal_id=agent_signal_id,
        timestamp=timestamp,
        key=reasoning_key,
    )


def new_agent_recommendation_id(
    *,
    agent_signal_id: str,
    timestamp: datetime,
    recommendation_key: str | None = None,
) -> str:
    return _new_agent_intelligence_id(
        prefix="agent_recommendation",
        agent_signal_id=agent_signal_id,
        timestamp=timestamp,
        key=recommendation_key,
    )


def new_agent_risk_assessment_id(
    *,
    agent_signal_id: str,
    timestamp: datetime,
    risk_key: str | None = None,
) -> str:
    return _new_agent_intelligence_id(
        prefix="agent_risk_assessment",
        agent_signal_id=agent_signal_id,
        timestamp=timestamp,
        key=risk_key,
    )


def _new_agent_intelligence_id(
    *,
    prefix: str,
    agent_signal_id: str | None,
    timestamp: datetime,
    key: str | None,
) -> str:
    clean_signal_id = require_non_empty_identifier(
        agent_signal_id,
        "agent_signal_id",
    )
    clean_key = clean_optional_identifier(
        key,
        "key",
    )
    parts = [
        prefix,
        clean_signal_id,
        timestamp.isoformat(),
    ]
    if clean_key is not None:
        parts.append(clean_key)

    return ":".join(parts)


def new_random_agent_intelligence_id(
    prefix: str,
) -> str:
    clean_prefix = require_non_empty_identifier(
        prefix,
        "prefix",
    )
    return f"{clean_prefix}:{uuid4().hex}"


def _set_required_identifier(
    record: object,
    field_name: str,
    value: str,
) -> None:
    object.__setattr__(
        record,
        field_name,
        require_non_empty_identifier(
            value,
            field_name,
        ),
    )


def _set_required_text(
    record: object,
    field_name: str,
    value: str,
) -> None:
    clean_value = _require_non_empty_text(
        value,
        field_name,
    )
    object.__setattr__(
        record,
        field_name,
        sanitize_reasoning_trace_text_for_boundary(
            clean_value,
            boundary_name=f"{type(record).__name__}.{field_name}",
            allow_empty=False,
        ),
    )


def _set_common_optional_fields(
    record: _CommonOptionalFieldsRecord,
) -> None:
    symbol = record.symbol
    object.__setattr__(
        record,
        "symbol",
        _clean_optional_symbol(
            symbol,
        ),
    )
    universe = record.universe
    object.__setattr__(
        record,
        "universe",
        clean_optional_identifier(
            universe,
            "universe",
        ),
    )


def _clean_optional_symbol(
    symbol: str | None,
) -> str | None:
    clean_symbol = clean_optional_identifier(
        symbol,
        "symbol",
    )
    if clean_symbol is None:
        return None

    return clean_symbol.upper()


def _clean_optional_model_text(
    value: str | None,
    *,
    boundary_name: str,
) -> str | None:
    if value is None:
        return None

    clean_value = value.strip()
    if not clean_value:
        return None

    sanitized = sanitize_reasoning_trace_text_for_boundary(
        clean_value,
        boundary_name=boundary_name,
    )
    return sanitized or None


def _set_sanitized_json_object_fields(
    record: object,
    *field_names: str,
) -> None:
    for field_name in field_names:
        sanitized = sanitize_reasoning_trace_payload(
            getattr(
                record,
                field_name,
            ),
            boundary_name=f"{type(record).__name__}.{field_name}",
        )
        object.__setattr__(
            record,
            field_name,
            cast(
                JsonObject,
                sanitized,
            ),
        )


def _require_non_empty_text(
    value: str,
    field_name: str,
) -> str:
    clean_value = value.strip()
    if not clean_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return clean_value


def _require_optional_ratio(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
