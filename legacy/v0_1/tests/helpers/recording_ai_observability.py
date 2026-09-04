from __future__ import annotations

from dataclasses import dataclass, field

from application.observability import AiObservabilityExportResult, AiObservation


@dataclass(slots=True)
class RecordingAiObservabilityProjector:
    observations: list[AiObservation] = field(default_factory=list)

    async def project(
        self,
        observation: AiObservation,
    ) -> AiObservabilityExportResult:
        self.observations.append(observation)
        return AiObservabilityExportResult.exported(
            idempotency_key=observation.idempotency_key(),
            observation_id=observation.correlation_ids.observation_id,
        )
