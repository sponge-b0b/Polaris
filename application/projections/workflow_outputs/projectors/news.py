from __future__ import annotations

import json
from collections.abc import Mapping
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from typing import Final
from typing import cast

from application.persistence.news import NewsPersistenceService
from application.projections.workflow_outputs.projection_identity import (
    build_projected_record_id,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionOutcome,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionStatus,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectorRegistration,
)
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.news import NewsAnalysisSnapshotRecord
from core.storage.persistence.news import NewsArticleRecord
from domain.workflow_outputs import NEWS_ANALYSIS_OUTPUT_CONTRACT
from domain.workflow_outputs import WORKFLOW_OUTPUT_SCHEMA_VERSION_V1

NEWS_ANALYSIS_PROJECTOR_NAME: Final = "news_analysis_projector"
NEWS_ANALYSIS_PROJECTOR_NODE_NAMES: Final = ("news_agent",)
NEWS_ANALYSIS_OBSERVED_AT_FIELD: Final = "observed_at"
NEWS_ANALYSIS_SOURCE_FIELD: Final = "news_source"
NEWS_ANALYSIS_ARTICLES_FIELD: Final = "news_articles"


class NewsAnalysisWorkflowOutputProjector:
    """Project news-agent workflow evidence into curated news records."""

    def __init__(
        self,
        news_persistence_service: NewsPersistenceService,
    ) -> None:
        self._news_persistence_service = news_persistence_service

    @property
    def projector_name(self) -> str:
        return NEWS_ANALYSIS_PROJECTOR_NAME

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        outputs = _mapping(request.node_output.outputs)
        observed_at = _parse_timestamp(outputs.get(NEWS_ANALYSIS_OBSERVED_AT_FIELD))
        if observed_at is None:
            return _skipped(
                request,
                "News output is missing first-class observed_at timestamp.",
            )

        source = _optional_identifier(outputs.get(NEWS_ANALYSIS_SOURCE_FIELD))
        symbol = _coalesce_identifier(
            outputs.get("symbol"),
            _execution_metadata(request).get("symbol"),
        )
        query = _optional_text(outputs.get("query"))
        features = _mapping(outputs.get("features"))
        themes = _identifier_tuple(
            _coalesce_sequence(features.get("primary_themes"), outputs.get("themes"))
        )
        metadata = _projection_metadata(request)

        articles = _article_mappings(
            _coalesce_sequence(
                outputs.get(NEWS_ANALYSIS_ARTICLES_FIELD),
                features.get("articles"),
            )
        )
        article_records = _build_article_records(
            request=request,
            articles=articles,
            symbol=symbol,
            themes=themes,
            metadata=metadata,
        )

        degraded = _quality_status(request) == "degraded" or "error" in _mapping(
            outputs.get("llm_response")
        )
        snapshot_records: tuple[NewsAnalysisSnapshotRecord, ...] = ()
        if not degraded:
            snapshot_records = (
                _build_analysis_snapshot_record(
                    request=request,
                    observed_at=observed_at,
                    source=source,
                    symbol=symbol,
                    query=query,
                    themes=themes,
                    article_records=article_records,
                    metadata=metadata,
                    outputs=outputs,
                    features=features,
                ),
            )

        if not article_records and not snapshot_records:
            return _skipped(
                request,
                "News output contains no eligible article or analysis records.",
            )

        result = await self._news_persistence_service.persist_records(
            articles=article_records,
            analysis_snapshots=snapshot_records,
        )
        if not result.success:
            return _failed(request, result.error or "News persistence failed.")

        return _outcome(
            request=request,
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            records_written=result.records_persisted,
            message="News output projected into curated news records.",
        )


def build_news_analysis_projector_registration(
    news_persistence_service: NewsPersistenceService,
) -> WorkflowOutputProjectorRegistration:
    """Build the canonical news-analysis projector registration."""
    projector = NewsAnalysisWorkflowOutputProjector(news_persistence_service)
    return WorkflowOutputProjectorRegistration(
        projector_name=NEWS_ANALYSIS_PROJECTOR_NAME,
        output_contract=NEWS_ANALYSIS_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        projector=projector,
        supported_node_names=NEWS_ANALYSIS_PROJECTOR_NODE_NAMES,
    )


def _build_article_records(
    *,
    request: WorkflowOutputProjectorRequest,
    articles: Sequence[Mapping[str, object]],
    symbol: str | None,
    themes: tuple[str, ...],
    metadata: JsonObject,
) -> tuple[NewsArticleRecord, ...]:
    records: list[NewsArticleRecord] = []
    for article in articles:
        source = _optional_identifier(article.get("source"))
        title = _optional_text(article.get("title"))
        published_at = _parse_timestamp(article.get("published_at"))
        external_id = _optional_identifier(article.get("id"))
        url = _optional_identifier(article.get("url"))
        if (
            source is None
            or title is None
            or published_at is None
            or (external_id is None and url is None)
        ):
            continue

        natural_key = f"{source}:{external_id or url}"
        records.append(
            NewsArticleRecord(
                article_id=build_projected_record_id(
                    record_type="news_article",
                    execution_id=request.lineage.execution_id
                    or request.run.execution_id,
                    node_name=request.lineage.node_name
                    or request.node_output.node_name,
                    domain_natural_key=natural_key,
                    source_timestamp=published_at,
                ),
                source=source,
                title=title,
                published_timestamp=published_at,
                lineage=request.lineage,
                external_id=external_id,
                url=url,
                summary=_optional_text(article.get("summary")),
                symbols=(symbol,) if symbol is not None else (),
                themes=themes,
                headline_score=_optional_ratio(article.get("headline_score")),
                relevance_score=_optional_ratio(article.get("relevance_score")),
                sentiment_score=_optional_stability_score(
                    article.get("sentiment_hint")
                ),
                normalized_article_payload=_compact_json_object(
                    {
                        "id": external_id,
                        "title": title,
                        "summary": _optional_text(article.get("summary")),
                        "source": source,
                        "url": url,
                        "published_at": published_at.isoformat(),
                        "headline_score": _optional_ratio(
                            article.get("headline_score")
                        ),
                        "relevance_score": _optional_ratio(
                            article.get("relevance_score")
                        ),
                        "sentiment_hint": _optional_stability_score(
                            article.get("sentiment_hint")
                        ),
                    }
                ),
                raw_payload=_json_mapping(article.get("raw")),
                metadata=metadata,
            )
        )
    return tuple(records)


def _build_analysis_snapshot_record(
    *,
    request: WorkflowOutputProjectorRequest,
    observed_at: datetime,
    source: str | None,
    symbol: str | None,
    query: str | None,
    themes: tuple[str, ...],
    article_records: Sequence[NewsArticleRecord],
    metadata: JsonObject,
    outputs: Mapping[str, object],
    features: Mapping[str, object],
) -> NewsAnalysisSnapshotRecord:
    llm_response = _mapping(outputs.get("llm_response"))
    natural_key = ":".join(
        part for part in (symbol, query or "market_news") if part is not None
    )
    return NewsAnalysisSnapshotRecord(
        analysis_snapshot_id=build_projected_record_id(
            record_type="news_analysis_snapshot",
            execution_id=request.lineage.execution_id or request.run.execution_id,
            node_name=request.lineage.node_name or request.node_output.node_name,
            domain_natural_key=natural_key,
            source_timestamp=observed_at,
        ),
        timestamp=observed_at,
        lineage=request.lineage,
        source=source,
        article_ids=tuple(record.article_id for record in article_records),
        symbols=(symbol,) if symbol is not None else (),
        themes=themes,
        sentiment_score=_optional_stability_score(outputs.get("directional_score")),
        impact_score=_optional_stability_score(outputs.get("directional_score")),
        confidence=_optional_ratio(outputs.get("confidence")),
        llm_summary=_optional_text(llm_response.get("summary")),
        full_llm_response=_json_text(llm_response),
        analysis_model=_optional_identifier(_execution_metadata(request).get("model")),
        inputs=_compact_json_object(
            {
                "query": query,
                "article_count": len(article_records),
            }
        ),
        outputs=_compact_json_object(
            {
                "directional_score": _optional_stability_score(
                    outputs.get("directional_score")
                ),
                "confidence": _optional_ratio(outputs.get("confidence")),
                "regime": _optional_identifier(outputs.get("regime")),
                "market_relevance": _optional_identifier(
                    features.get("market_relevance")
                ),
                "signals": _json_sequence(outputs.get("signals")),
                "risks": _json_sequence(outputs.get("risks")),
                "recommendations": _json_sequence(outputs.get("recommendations")),
                "llm_response": _json_mapping(llm_response),
            }
        ),
        metadata=metadata,
    )


def _projection_metadata(
    request: WorkflowOutputProjectorRequest,
) -> JsonObject:
    return _compact_json_object(
        {
            "source_fingerprint": request.source_fingerprint,
            "projector_name": NEWS_ANALYSIS_PROJECTOR_NAME,
            "node_output_id": request.node_output.node_output_id,
            "quality_status": _quality_status(request),
            "requested_at": request.requested_at.isoformat(),
        }
    )


def _execution_metadata(
    request: WorkflowOutputProjectorRequest,
) -> Mapping[str, object]:
    return _mapping(request.node_output.metadata.get("execution_metadata"))


def _quality_status(request: WorkflowOutputProjectorRequest) -> str | None:
    direct = _optional_identifier(request.node_output.metadata.get("quality_status"))
    if direct is not None:
        return direct
    return _optional_identifier(_execution_metadata(request).get("quality_status"))


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def _article_mappings(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(_mapping(item) for item in value if _mapping(item))


def _coalesce_sequence(*values: object) -> object:
    for value in values:
        if isinstance(value, Sequence) and not isinstance(value, str):
            return value
    return ()


def _json_sequence(value: object) -> tuple[object, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(_to_json_value(item) for item in value)


def _identifier_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    identifiers: list[str] = []
    for item in value:
        identifier = _optional_identifier(item)
        if identifier is not None:
            identifiers.append(identifier)
    return tuple(identifiers)


def _coalesce_identifier(*values: object) -> str | None:
    for value in values:
        identifier = _optional_identifier(value)
        if identifier is not None:
            return identifier
    return None


def _optional_identifier(value: object) -> str | None:
    if value is None:
        return None
    identifier = str(value).strip()
    return identifier or None


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, str | int | float):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _optional_ratio(value: object) -> float | None:
    candidate = _optional_float(value)
    if candidate is None or candidate < 0.0 or candidate > 1.0:
        return None
    return candidate


def _optional_stability_score(value: object) -> float | None:
    candidate = _optional_float(value)
    if candidate is None or candidate < -1.0 or candidate > 1.0:
        return None
    return candidate


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _json_text(value: Mapping[str, object]) -> str | None:
    if not value:
        return None
    return json.dumps(_json_mapping(value), sort_keys=True, default=str)


def _json_mapping(value: object) -> JsonObject:
    if not isinstance(value, Mapping):
        return {}
    return cast(
        JsonObject, {str(key): _to_json_value(raw) for key, raw in value.items()}
    )


def _compact_json_object(value: Mapping[str, object]) -> JsonObject:
    return cast(
        JsonObject,
        {
            str(key): _to_json_value(raw)
            for key, raw in value.items()
            if raw is not None and raw != () and raw != {} and raw != []
        },
    )


def _to_json_value(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _to_json_value(raw) for key, raw in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_to_json_value(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _outcome(
    *,
    request: WorkflowOutputProjectorRequest,
    status: WorkflowOutputProjectionStatus,
    records_written: int,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=status,
        projector_name=NEWS_ANALYSIS_PROJECTOR_NAME,
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract or "unknown",
        output_schema_version=request.node_output.output_schema_version or 0,
        source_fingerprint=request.source_fingerprint,
        records_written=records_written,
        message=message,
        completed_at=datetime.now(UTC),
    )


def _skipped(
    request: WorkflowOutputProjectorRequest,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return _outcome(
        request=request,
        status=WorkflowOutputProjectionStatus.SKIPPED,
        records_written=0,
        message=message,
    )


def _failed(
    request: WorkflowOutputProjectorRequest,
    error: str,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=WorkflowOutputProjectionStatus.FAILED,
        projector_name=NEWS_ANALYSIS_PROJECTOR_NAME,
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract or "unknown",
        output_schema_version=request.node_output.output_schema_version or 0,
        source_fingerprint=request.source_fingerprint,
        records_written=0,
        error_type="persistence_error",
        error_message=error,
        completed_at=datetime.now(UTC),
    )
