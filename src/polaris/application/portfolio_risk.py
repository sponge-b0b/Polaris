"""Inward-owned production and history ports for Portfolio Risk assessments."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from polaris.domain.actors import ActorAttribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.evidence.judgments import (
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
)
from polaris.domain.portfolio import PortfolioStateId, RecordedPortfolioState
from polaris.domain.portfolio_consequences import RecordedProjectedPortfolioConsequence
from polaris.domain.portfolio_judgment_history import PortfolioClaimCatalog
from polaris.domain.portfolio_risk import (
    PortfolioRiskAssessment,
    RecordedPortfolioRiskAssessment,
    RiskSupport,
    assess_portfolio_risk,
)


class PortfolioRiskConflict(Exception):
    """An assessment identity already denotes a durable judgment."""


class PortfolioRiskStoreFailure(Exception):
    """The Portfolio Risk store could not complete an operation."""


class PortfolioRiskStore(Protocol):
    async def append(
        self,
        assessment: PortfolioRiskAssessment,
        initial_claim_catalog: PortfolioClaimCatalog,
    ) -> RecordedPortfolioRiskAssessment:
        """Append one assessment without overwriting prior Risk or uncertainty."""

    async def get(
        self, assessment_id: PortfolioRiskAssessmentRef
    ) -> RecordedPortfolioRiskAssessment | None:
        """Read an exact historical Risk judgment."""


class PortfolioStateReader(Protocol):
    async def get(self, state_id: PortfolioStateId) -> RecordedPortfolioState | None:
        """Read the exact actual State assessed."""


class PortfolioConsequenceReader(Protocol):
    async def get(
        self, consequence_id: ProjectedPortfolioConsequenceRef
    ) -> RecordedProjectedPortfolioConsequence | None:
        """Read the exact hypothetical consequence assessed."""


class PortfolioRiskService:
    def __init__(
        self,
        state_reader: PortfolioStateReader,
        consequence_reader: PortfolioConsequenceReader,
        risk_store: PortfolioRiskStore,
    ) -> None:
        self._state_reader = state_reader
        self._consequence_reader = consequence_reader
        self._risk_store = risk_store

    async def assess(
        self,
        *,
        assessment_id: PortfolioRiskAssessmentRef,
        source_state_id: PortfolioStateId,
        projected_consequence_id: ProjectedPortfolioConsequenceRef | None,
        horizon: InvestmentHorizon,
        scenario: str,
        support: RiskSupport,
        attribution: ActorAttribution,
        formed_at: datetime,
        initial_claim_catalog: PortfolioClaimCatalog,
    ) -> RecordedPortfolioRiskAssessment:
        """Assess actual or projected Portfolio Risk against one immutable basis."""
        if type(source_state_id) is not PortfolioStateId:
            raise TypeError("source_state_id must be PortfolioStateId")
        if type(initial_claim_catalog) is not PortfolioClaimCatalog:
            raise TypeError("initial_claim_catalog must be PortfolioClaimCatalog")
        source = await self._state_reader.get(source_state_id)
        if source is None:
            raise ValueError("source Portfolio State does not exist")
        consequence = None
        if projected_consequence_id is not None:
            if type(projected_consequence_id) is not ProjectedPortfolioConsequenceRef:
                raise TypeError("projected_consequence_id must be typed")
            recorded = await self._consequence_reader.get(projected_consequence_id)
            if recorded is None:
                raise ValueError("projected Portfolio Consequence does not exist")
            consequence = recorded.consequence
        assessment = assess_portfolio_risk(
            assessment_id=assessment_id,
            state=source.state,
            consequence=consequence,
            horizon=horizon,
            scenario=scenario,
            support=support,
            attribution=attribution,
            formed_at=formed_at,
        )
        return await self._risk_store.append(assessment, initial_claim_catalog)
