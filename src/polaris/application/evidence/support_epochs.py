from __future__ import annotations

from datetime import datetime
from typing import Protocol

from polaris.domain.evidence.judgments import (
    EvidenceJudgmentRef,
    EvidenceScope,
    EvidenceUse,
)
from polaris.domain.evidence.observations import EvidenceSupportVersion


class EvidenceSupportEpochReader(Protocol):
    """Read the Evidence-owned epoch for one exact target/scope/use key."""

    async def load_support_version(
        self,
        target: EvidenceJudgmentRef,
        scope: EvidenceScope,
        evidence_use: EvidenceUse,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceSupportVersion: ...
