from __future__ import annotations

from datetime import UTC, datetime

from application.decision_evidence import (
    calculate_completed_workflow_node_evidence_digest,
    calculate_evaluation_artifact_evidence_digest,
    calculate_evaluation_metric_result_evidence_digest,
    calculate_evaluation_run_evidence_digest,
    calculate_rag_citation_source_evidence_digest,
    calculate_rag_retrieval_context_evidence_digest,
    calculate_trace_context_evidence_digest,
)
from application.decision_evidence._reconstruction_digest import stable_content_digest
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunRecord,
)
from core.storage.persistence.evaluation import (
    EvaluationArtifactRecord,
    EvaluationMetricResultRecord,
    EvaluationRunRecord,
)
from core.storage.persistence.rag import RagChunkRecord, RagDocumentRecord
from core.storage.persistence.telemetry import TelemetryTraceRecord
from domain.evaluation import EvaluationStatus, EvaluationTargetType


def test_decision_evidence_digest_vectors_are_stable() -> None:
    run = CompletedRunRecord(
        run_id="run-1",
        workflow_name="strategy_review",
        workflow_id=None,
        execution_id="exec-1",
        runtime_id=None,
        status="succeeded",
        success=True,
        context_json={},
        inputs_json={},
        outputs_json={},
        metadata={},
        errors_json=(),
        started_at=None,
        completed_at=None,
        duration_seconds=None,
        node_count=1,
        completed_node_count=1,
        failed_node_count=0,
    )
    node_output = CompletedNodeOutputRecord(
        node_output_id="node-output-1",
        run_id="run-1",
        workflow_name="strategy_review",
        execution_id="exec-1",
        node_name="synthesis",
        node_type=None,
        output_contract="strategy_synthesis",
        output_schema_version=2,
        status="succeeded",
        success=True,
        outputs={"decision": {"selected_perspective": "bull"}},
        metadata={"quality_status": "normal"},
        errors_json=(),
        started_at=None,
        completed_at=None,
        duration_seconds=None,
    )
    evaluation_run = EvaluationRunRecord(
        run_id="evaluation-run-1",
        target_type=EvaluationTargetType.STRATEGY_SYNTHESIS,
        status=EvaluationStatus.PASSED,
        evaluator_provider="openai",
        evaluator_model="gpt-4.1-2026-07-25",
        dataset_id="dataset-strategy-synthesis",
        case_ids=("case-1",),
        started_at=datetime(2026, 7, 25, 13, 6, tzinfo=UTC),
        completed_at=datetime(2026, 7, 25, 13, 7, tzinfo=UTC),
    )
    metric_result = EvaluationMetricResultRecord(
        metric_result_id="metric-result-1",
        run_id=evaluation_run.run_id,
        case_id="case-1",
        metric_name="faithfulness",
        score=0.92,
        status=EvaluationStatus.PASSED,
        evaluator_provider="openai",
        evaluator_model="gpt-4.1-2026-07-25",
    )
    artifact = EvaluationArtifactRecord(
        artifact_id="artifact-1",
        run_id=evaluation_run.run_id,
        artifact_type="evaluation_summary",
        case_id="case-1",
        payload={"summary": "Evaluation artifact summary."},
        created_at=datetime(2026, 7, 25, 13, 11, tzinfo=UTC),
    )
    rag_document = RagDocumentRecord(
        document_id="rag-document-1",
        source_table="curated_strategy_decisions",
        source_id="strategy-decision-1",
        source_type="strategy_decision",
        title="Strategy decision",
        content_text="Strategy evidence supports a bullish perspective.",
        generated_at=datetime(2026, 7, 25, 13, 8, tzinfo=UTC),
        metadata={"section_name": "decision"},
    )
    rag_chunk = RagChunkRecord(
        chunk_id="rag-chunk-1",
        document_id=rag_document.document_id,
        chunk_index=0,
        chunk_text="Strategy evidence supports a bullish perspective.",
        metadata={"section_name": "rationale"},
    )
    rag_context: dict[str, object] = {
        "context_id": "context-1",
        "retrieval_route": "hybrid",
        "source": {
            "source_table": rag_document.source_table,
            "source_id": rag_document.source_id,
            "document_id": rag_document.document_id,
            "chunk_id": rag_chunk.chunk_id,
        },
        "text": rag_chunk.chunk_text,
    }
    trace = TelemetryTraceRecord(
        trace_record_id="trace-record-1",
        trace_id="trace-1",
        span_id="span-1",
        operation_name="decision_evidence.reconstruct",
        source="application.decision_evidence",
        started_at=datetime(2026, 7, 25, 13, 10, tzinfo=UTC),
        ended_at=datetime(2026, 7, 25, 13, 10, 1, tzinfo=UTC),
        duration_seconds=1.0,
        status="succeeded",
        correlation_id="correlation-1",
    )

    assert (
        calculate_completed_workflow_node_evidence_digest(
            run=run,
            node_output=node_output,
        )
        == "f0c665f69050456fd32d3985c5e78f9045ab75b47057f3d3e90e036f21644478"
    )
    assert (
        calculate_evaluation_run_evidence_digest(run=evaluation_run)
        == "ce510ac3b1035cf43a9ea9ce931fee7dbffc0895c543d486ffe681fa9ea9ea9e"
    )
    assert (
        calculate_evaluation_metric_result_evidence_digest(
            metric_result=metric_result,
        )
        == "0761a5f804fac58c2324325065e863588dbc18eff758a5cf3c3cd23674e8d346"
    )
    assert (
        calculate_evaluation_artifact_evidence_digest(artifact=artifact)
        == "7bc349160d6206ff9e536e74d5ad52752ccfd85a89c1b2f1bd6dc4f57a8c59e0"
    )
    assert (
        calculate_rag_retrieval_context_evidence_digest(
            context_payload=rag_context,
        )
        == "2e209f1ff417d8759817b1bf217e68997f827a53df05db33c73f148b04a8a4ce"
    )
    assert (
        calculate_rag_citation_source_evidence_digest(
            document=rag_document,
            chunk=rag_chunk,
        )
        == "d330295dbb3dc657ae881b3755fc570d25fc7c977e9bc7a5466c59773f017026"
    )
    assert (
        calculate_trace_context_evidence_digest(trace=trace)
        == "56b61f2ed8403dfb092f665515325cca73e32b77913b4c5b9e44c0ddce08da7f"
    )
    assert (
        stable_content_digest(
            {
                "record_id": "strategy-decision-1",
                "decision": "bull",
                "note": "café",
                "signals": {"z": 2, "a": 1},
            }
        )
        == "c3f144e592663de52c9f64e3d37b2cfa38236c12114b8ecddd553b37c26372f6"
    )
