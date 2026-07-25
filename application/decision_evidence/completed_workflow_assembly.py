from __future__ import annotations

import logging
from dataclasses import dataclass, field

from application.projections.workflow_outputs import (
    calculate_workflow_output_source_fingerprint,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArchive,
    CompletedRunBundle,
    CompletedRunRecord,
)
from domain.authority import RiskAuthorityContract, SourceOfTruthCategory
from domain.decision_evidence import (
    DecisionEvidencePacket,
    DecisionEvidencePacketValidationError,
    EvidenceConstraint,
    EvidenceLimitation,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    EvidenceUncertainty,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
)

logger = logging.getLogger(__name__)


class CompletedWorkflowEvidencePacketAssemblyError(ValueError):
    """Raised when workflow evidence cannot safely assemble a packet."""


class MissingCompletedWorkflowEvidenceError(
    CompletedWorkflowEvidencePacketAssemblyError,
):
    """Raised when the required completed workflow run is absent."""


class MissingWorkflowNodeOutputEvidenceError(
    CompletedWorkflowEvidencePacketAssemblyError,
):
    """Raised when a required runtime node-output record is absent."""


class StaleWorkflowEvidenceError(CompletedWorkflowEvidencePacketAssemblyError):
    """Raised when archived workflow evidence no longer matches a requirement."""


class SubstitutedWorkflowEvidenceError(
    CompletedWorkflowEvidencePacketAssemblyError,
):
    """Raised when workflow evidence belongs to a different run than requested."""


@dataclass(frozen=True, slots=True)
class CompletedWorkflowNodeEvidenceRequirement:
    """Required completed-run node evidence for one packet evidence reference."""

    evidence_id: str
    node_name: str
    node_output_id: str | None = None
    output_contract: str | None = None
    output_schema_version: int | None = None
    expected_content_digest: str | None = None
    summary: str = ""
    require_success: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_id",
            _clean_required_string(self.evidence_id, "evidence_id"),
        )
        object.__setattr__(
            self,
            "node_name",
            _clean_required_string(self.node_name, "node_name"),
        )
        object.__setattr__(
            self,
            "node_output_id",
            _clean_optional_string(self.node_output_id, "node_output_id"),
        )
        object.__setattr__(
            self,
            "output_contract",
            _clean_optional_string(self.output_contract, "output_contract"),
        )
        object.__setattr__(
            self,
            "expected_content_digest",
            _clean_optional_string(
                self.expected_content_digest,
                "expected_content_digest",
            ),
        )
        object.__setattr__(
            self,
            "summary",
            _clean_string(self.summary, "summary", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class CompletedWorkflowEvidencePacketAssemblyRequest:
    """Request to assemble one packet from archived workflow evidence."""

    packet_id: str
    output_id: str
    authority: RiskAuthorityContract
    workflow_name: str
    execution_id: str
    claims: tuple[MaterialClaim, ...]
    required_node_evidence: tuple[CompletedWorkflowNodeEvidenceRequirement, ...]
    retention: EvidenceRetentionRequirement
    constraints: tuple[EvidenceConstraint, ...] = ()
    uncertainties: tuple[EvidenceUncertainty, ...] = ()
    limitations: tuple[EvidenceLimitation, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "packet_id",
            _clean_required_string(self.packet_id, "packet_id"),
        )
        object.__setattr__(
            self,
            "output_id",
            _clean_required_string(self.output_id, "output_id"),
        )
        object.__setattr__(
            self,
            "workflow_name",
            _clean_required_string(self.workflow_name, "workflow_name"),
        )
        object.__setattr__(
            self,
            "execution_id",
            _clean_required_string(self.execution_id, "execution_id"),
        )
        object.__setattr__(self, "claims", tuple(self.claims))
        object.__setattr__(
            self,
            "required_node_evidence",
            tuple(self.required_node_evidence),
        )
        object.__setattr__(self, "constraints", tuple(self.constraints))
        object.__setattr__(self, "uncertainties", tuple(self.uncertainties))
        object.__setattr__(self, "limitations", tuple(self.limitations))


@dataclass(frozen=True, slots=True)
class CompletedWorkflowEvidencePacketAssembler:
    """Assemble decision evidence packets through the completed-run archive."""

    completed_run_archive: CompletedRunArchive = field(repr=False)

    async def assemble(
        self,
        request: CompletedWorkflowEvidencePacketAssemblyRequest,
    ) -> DecisionEvidencePacket:
        """Load archived workflow evidence and assemble a validated packet."""

        bundle = await self.completed_run_archive.load_archived_run(
            request.workflow_name,
            request.execution_id,
        )
        if bundle is None:
            logger.warning(
                "Decision evidence packet assembly missing completed workflow run.",
                extra={
                    "packet_id": request.packet_id,
                    "workflow_name": request.workflow_name,
                    "execution_id": request.execution_id,
                },
            )
            raise MissingCompletedWorkflowEvidenceError(
                "completed workflow run "
                f"'{request.workflow_name}:{request.execution_id}' was not found."
            )

        try:
            return assemble_decision_evidence_packet_from_completed_run(
                request=request,
                bundle=bundle,
            )
        except (
            CompletedWorkflowEvidencePacketAssemblyError,
            DecisionEvidencePacketValidationError,
        ) as exc:
            logger.warning(
                "Decision evidence packet assembly failed closed.",
                extra={
                    "packet_id": request.packet_id,
                    "workflow_name": request.workflow_name,
                    "execution_id": request.execution_id,
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )
            raise


def assemble_decision_evidence_packet_from_completed_run(
    *,
    request: CompletedWorkflowEvidencePacketAssemblyRequest,
    bundle: CompletedRunBundle,
) -> DecisionEvidencePacket:
    """Assemble a packet from a previously loaded completed-run bundle."""

    _validate_bundle_matches_request(request=request, run=bundle.run)
    evidence_references: list[EvidenceReference] = []
    reconstruction_references: list[ReconstructionReference] = []

    for requirement in request.required_node_evidence:
        node_output = _resolve_required_node_output(
            requirement=requirement,
            bundle=bundle,
        )
        content_digest = calculate_completed_workflow_node_evidence_digest(
            run=bundle.run,
            node_output=node_output,
        )
        _validate_node_requirement(
            requirement=requirement,
            node_output=node_output,
            content_digest=content_digest,
        )
        run_reference_id = f"{requirement.evidence_id}:completed-run"
        node_reference_id = f"{requirement.evidence_id}:node-output"
        evidence_references.append(
            EvidenceReference(
                evidence_id=requirement.evidence_id,
                kind=EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT,
                reconstruction_reference_ids=(run_reference_id, node_reference_id),
                summary=requirement.summary,
                source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
            )
        )
        reconstruction_references.extend(
            (
                ReconstructionReference(
                    reference_id=run_reference_id,
                    kind=ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN,
                    record_id=(f"{bundle.run.workflow_name}:{bundle.run.execution_id}"),
                    source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
                    snapshot_id=bundle.run.run_id,
                ),
                ReconstructionReference(
                    reference_id=node_reference_id,
                    kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
                    record_id=node_output.node_output_id,
                    source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
                    snapshot_id=(
                        f"{node_output.workflow_name}:{node_output.execution_id}:"
                        f"{node_output.node_name}"
                    ),
                    content_digest=content_digest,
                ),
            )
        )

    return DecisionEvidencePacket(
        packet_id=request.packet_id,
        output_id=request.output_id,
        authority=request.authority,
        claims=request.claims,
        evidence=tuple(evidence_references),
        reconstruction_references=tuple(reconstruction_references),
        retention=request.retention,
        constraints=request.constraints,
        uncertainties=request.uncertainties,
        limitations=request.limitations,
    )


def calculate_completed_workflow_node_evidence_digest(
    *,
    run: CompletedRunRecord,
    node_output: CompletedNodeOutputRecord,
) -> str:
    """Calculate the stable content digest for archived workflow node evidence."""

    return calculate_workflow_output_source_fingerprint(
        run=run,
        node_output=node_output,
    )


def _validate_bundle_matches_request(
    *,
    request: CompletedWorkflowEvidencePacketAssemblyRequest,
    run: CompletedRunRecord,
) -> None:
    if (
        run.workflow_name != request.workflow_name
        or run.execution_id != request.execution_id
    ):
        raise SubstitutedWorkflowEvidenceError(
            "completed workflow run evidence does not match requested execution "
            f"'{request.workflow_name}:{request.execution_id}'."
        )


def _resolve_required_node_output(
    *,
    requirement: CompletedWorkflowNodeEvidenceRequirement,
    bundle: CompletedRunBundle,
) -> CompletedNodeOutputRecord:
    candidates = tuple(
        node_output
        for node_output in bundle.node_outputs
        if node_output.node_name == requirement.node_name
        and (
            requirement.node_output_id is None
            or node_output.node_output_id == requirement.node_output_id
        )
    )
    if not candidates:
        raise MissingWorkflowNodeOutputEvidenceError(
            f"node output evidence '{requirement.evidence_id}' was not found for "
            f"node '{requirement.node_name}'."
        )
    if len(candidates) > 1:
        raise MissingWorkflowNodeOutputEvidenceError(
            f"node output evidence '{requirement.evidence_id}' matched multiple "
            f"outputs for node '{requirement.node_name}'."
        )

    node_output = candidates[0]
    if (
        node_output.run_id != bundle.run.run_id
        or node_output.workflow_name != bundle.run.workflow_name
        or node_output.execution_id != bundle.run.execution_id
    ):
        raise SubstitutedWorkflowEvidenceError(
            f"node output evidence '{requirement.evidence_id}' does not belong to "
            f"completed workflow run '{bundle.run.run_id}'."
        )
    return node_output


def _validate_node_requirement(
    *,
    requirement: CompletedWorkflowNodeEvidenceRequirement,
    node_output: CompletedNodeOutputRecord,
    content_digest: str,
) -> None:
    if requirement.require_success and node_output.success is not True:
        raise MissingWorkflowNodeOutputEvidenceError(
            f"node output evidence '{requirement.evidence_id}' did not succeed."
        )
    if (
        requirement.output_contract is not None
        and node_output.output_contract != requirement.output_contract
    ):
        raise StaleWorkflowEvidenceError(
            f"node output evidence '{requirement.evidence_id}' output contract "
            "does not match the required contract."
        )
    if (
        requirement.output_schema_version is not None
        and node_output.output_schema_version != requirement.output_schema_version
    ):
        raise StaleWorkflowEvidenceError(
            f"node output evidence '{requirement.evidence_id}' schema version "
            "does not match the required version."
        )
    if (
        requirement.expected_content_digest is not None
        and content_digest != requirement.expected_content_digest
    ):
        raise StaleWorkflowEvidenceError(
            f"node output evidence '{requirement.evidence_id}' content digest mismatch."
        )


def _clean_required_string(value: object, label: str) -> str:
    return _clean_string(value, label, allow_empty=False)


def _clean_optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _clean_string(value, label, allow_empty=False)


def _clean_string(value: object, label: str, *, allow_empty: bool) -> str:
    if not isinstance(value, str):
        raise CompletedWorkflowEvidencePacketAssemblyError(f"{label} must be a string.")
    cleaned = value.strip()
    if not cleaned and not allow_empty:
        raise CompletedWorkflowEvidencePacketAssemblyError(f"{label} cannot be empty.")
    return cleaned


__all__ = [
    "CompletedWorkflowEvidencePacketAssembler",
    "CompletedWorkflowEvidencePacketAssemblyError",
    "CompletedWorkflowEvidencePacketAssemblyRequest",
    "CompletedWorkflowNodeEvidenceRequirement",
    "MissingCompletedWorkflowEvidenceError",
    "MissingWorkflowNodeOutputEvidenceError",
    "StaleWorkflowEvidenceError",
    "SubstitutedWorkflowEvidenceError",
    "assemble_decision_evidence_packet_from_completed_run",
    "calculate_completed_workflow_node_evidence_digest",
]
