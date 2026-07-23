from __future__ import annotations

from datetime import datetime

from application.rag.ingestion.curated_rag_models import (
    CuratedRagBuildOptions,
    CuratedRagSource,
    CuratedRagSourceNotEligibleError,
)
from application.rag.ingestion.curated_rag_structured_sources import (
    is_structured_curated_rag_source,
    source_candidate_for_structured_source,
    structured_source_timestamp,
)
from core.storage.persistence.agent_signals import AgentSignalRecord
from core.storage.persistence.rag import (
    DefaultRagEligibilityRules,
    RagEligibilitySourceCandidate,
    RagPersistenceRepository,
    RagSourceEligibilityRecord,
)
from core.storage.persistence.reports import ReportRecord


def evaluate_source_eligibility(
    source: CuratedRagSource,
) -> RagSourceEligibilityRecord:
    return DefaultRagEligibilityRules().evaluate(
        source_candidate(
            source,
        ),
        reviewed_timestamp=source_reviewed_timestamp(
            source,
        ),
    )


async def resolve_persisted_or_default_eligibility(
    repository: RagPersistenceRepository,
    source: CuratedRagSource,
) -> RagSourceEligibilityRecord:
    candidate = source_candidate(
        source,
    )
    persisted = await repository.get_source_eligibility(
        source_table=candidate.source_table,
        source_id=candidate.source_id,
        source_type=candidate.source_type,
    )
    if persisted is not None:
        return persisted

    return DefaultRagEligibilityRules().evaluate(
        candidate,
        reviewed_timestamp=source_reviewed_timestamp(
            source,
        ),
    )


def source_candidate(
    source: CuratedRagSource,
) -> RagEligibilitySourceCandidate:
    if isinstance(
        source,
        ReportRecord,
    ):
        return RagEligibilitySourceCandidate(
            source_table="reports",
            source_id=source.report_id,
            source_type=source.report_type,
            has_meaningful_content=bool(
                source.markdown_body.strip(),
            ),
            metadata={
                "source_kind": "report",
            },
        )

    if isinstance(
        source,
        AgentSignalRecord,
    ):
        return RagEligibilitySourceCandidate(
            source_table="agent_signals",
            source_id=source.signal_id,
            source_type=source.agent_type,
            has_meaningful_content=agent_signal_has_meaningful_content(
                source,
            ),
            metadata={
                "source_kind": "agent_signal",
                "agent_name": source.agent_name,
            },
        )

    if is_structured_curated_rag_source(
        source,
    ):
        return source_candidate_for_structured_source(
            source,
        )

    raise TypeError(
        "RAG eligibility can only be evaluated for curated PostgreSQL source "
        "records; raw runtime, telemetry, provider, or arbitrary JSON payloads "
        "are not supported."
    )


def source_reviewed_timestamp(
    source: CuratedRagSource,
) -> datetime:
    if isinstance(
        source,
        ReportRecord,
    ):
        return source.generated_at
    if isinstance(
        source,
        AgentSignalRecord,
    ):
        return source.timestamp
    if is_structured_curated_rag_source(
        source,
    ):
        return structured_source_timestamp(
            source,
        )

    raise TypeError(
        "RAG eligibility can only be evaluated for curated PostgreSQL source "
        "records; raw runtime, telemetry, provider, or arbitrary JSON payloads "
        "are not supported."
    )


def raise_if_ineligible(
    eligibility: RagSourceEligibilityRecord,
    *,
    options: CuratedRagBuildOptions,
) -> None:
    if not options.require_source_eligibility or eligibility.eligible:
        return

    raise CuratedRagSourceNotEligibleError(
        eligibility_error_message(
            eligibility,
        )
    )


def eligibility_error_message(
    eligibility: RagSourceEligibilityRecord,
) -> str:
    return (
        "Curated RAG source is not eligible: "
        f"{eligibility.source_table}/{eligibility.source_type}/"
        f"{eligibility.source_id}. Reason: {eligibility.reason}"
    )


def report_metadata(
    *,
    report: ReportRecord,
    eligibility: RagSourceEligibilityRecord,
    options: CuratedRagBuildOptions,
) -> dict[str, object]:
    return {
        "curated_source": True,
        "source_kind": "report",
        "report_type": report.report_type,
        "status": report.status,
        "runtime_id": report.runtime_id,
        "rag_builder_version": "1",
        "rag_eligibility_id": eligibility.eligibility_id,
        "rag_eligibility_rule_name": eligibility.metadata.get(
            "rule_name",
        ),
        "rag_eligibility_required": options.require_source_eligibility,
    }


def agent_signal_metadata(
    *,
    signal: AgentSignalRecord,
    eligibility: RagSourceEligibilityRecord,
    options: CuratedRagBuildOptions,
) -> dict[str, object]:
    return {
        "curated_source": True,
        "source_kind": "agent_signal",
        "agent_name": signal.agent_name,
        "agent_type": signal.agent_type,
        "runtime_id": signal.runtime_id,
        "node_name": signal.node_name,
        "symbol": signal.symbol,
        "regime": signal.regime,
        "confidence": signal.confidence,
        "directional_score": signal.directional_score,
        "rag_builder_version": "1",
        "rag_eligibility_id": eligibility.eligibility_id,
        "rag_eligibility_rule_name": eligibility.metadata.get(
            "rule_name",
        ),
        "rag_eligibility_required": options.require_source_eligibility,
    }


def agent_signal_has_meaningful_content(
    signal: AgentSignalRecord,
) -> bool:
    return any(
        (
            bool(signal.signals),
            bool(signal.risks),
            bool(signal.recommendations),
            bool(signal.features),
            bool(signal.reasoning_text and signal.reasoning_text.strip()),
            bool(signal.llm_response and signal.llm_response.strip()),
        )
    )
