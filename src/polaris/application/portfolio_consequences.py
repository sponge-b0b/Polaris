"""Inward-owned production and storage boundary for projected consequences."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from polaris.domain.decisions.facts import InvestmentDecisionId
from polaris.domain.evidence.context_versions import (
    DecisionAlternativeId as EvidenceAlternativeId,
)
from polaris.domain.evidence.context_versions import (
    DecisionAlternativeRevision,
    DecisionAlternativeVersionRef,
)
from polaris.domain.evidence.judgments import ProjectedPortfolioConsequenceRef
from polaris.domain.investment_intelligence import (
    DecisionAlternative,
    require_minimum_alternatives,
)
from polaris.domain.portfolio import PortfolioStateId, RecordedPortfolioState
from polaris.domain.portfolio_consequences import (
    ProjectedPortfolioConsequence,
    RecordedProjectedPortfolioConsequence,
)
from polaris.domain.portfolio_judgment_history import PortfolioClaimCatalog


class PortfolioConsequenceConflict(Exception):
    """A projected consequence identity already denotes a durable judgment."""


class PortfolioConsequenceStoreFailure(Exception):
    """The projected consequence operation did not complete."""


class PortfolioConsequenceStore(Protocol):
    async def append_batch(
        self,
        decision_id: InvestmentDecisionId,
        consequences: tuple[ProjectedPortfolioConsequence, ...],
        initial_claim_catalogs: Mapping[
            ProjectedPortfolioConsequenceRef, PortfolioClaimCatalog
        ],
    ) -> tuple[RecordedProjectedPortfolioConsequence, ...]:
        """Recheck the owner set and atomically append without replacement."""

    async def get(
        self, consequence_id: ProjectedPortfolioConsequenceRef
    ) -> RecordedProjectedPortfolioConsequence | None:
        """Read an exact historical hypothetical judgment."""


class PortfolioStateReader(Protocol):
    async def get(self, state_id: PortfolioStateId) -> RecordedPortfolioState | None:
        """Read the exact immutable source State."""


class MaterialAlternativeReader(Protocol):
    async def for_decision(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[DecisionAlternative, ...]:
        """Read the complete material Alternative set from Investment Intelligence."""


def require_initial_claim_catalogs(
    consequences: tuple[ProjectedPortfolioConsequence, ...],
    catalogs: Mapping[ProjectedPortfolioConsequenceRef, PortfolioClaimCatalog],
) -> dict[ProjectedPortfolioConsequenceRef, PortfolioClaimCatalog]:
    """Require one explicit complete catalog per consequence root."""
    if (
        not isinstance(catalogs, Mapping)
        or set(catalogs) != {item.consequence_id for item in consequences}
        or any(
            type(catalog) is not PortfolioClaimCatalog for catalog in catalogs.values()
        )
    ):
        raise ValueError("each consequence requires its complete initial claim catalog")
    return dict(catalogs)


def _validate_source(
    source: RecordedPortfolioState,
    source_state_id: PortfolioStateId,
    alternatives: tuple[DecisionAlternative, ...],
    expected: dict[DecisionAlternativeVersionRef, DecisionAlternative],
    consequences: tuple[ProjectedPortfolioConsequence, ...],
) -> None:
    if any(
        alternative.instrument_id != source.state.instrument_id
        for alternative in alternatives
    ):
        raise ValueError("Alternatives and source State concern different instruments")
    if any(
        item.source_state_id != source_state_id
        or item.source_as_of != source.state.as_of
        or item.horizon != expected[item.alternative].horizon
        for item in consequences
    ):
        raise ValueError(
            "consequences must use the exact source State, as-of, and horizon"
        )


class PortfolioConsequenceService:
    def __init__(
        self,
        state_store: PortfolioStateReader,
        consequence_store: PortfolioConsequenceStore,
        alternative_reader: MaterialAlternativeReader,
    ) -> None:
        self._state_store = state_store
        self._consequence_store = consequence_store
        self._alternative_reader = alternative_reader

    async def produce(
        self,
        *,
        decision_id: InvestmentDecisionId,
        source_state_id: PortfolioStateId,
        consequences: tuple[ProjectedPortfolioConsequence, ...],
        initial_claim_catalogs: Mapping[
            ProjectedPortfolioConsequenceRef, PortfolioClaimCatalog
        ],
    ) -> tuple[RecordedProjectedPortfolioConsequence, ...]:
        """Preserve one consequence for every owner-issued material Alternative.

        Investment Intelligence supplies the complete set for this Decision.
        This boundary refuses a partial set and checks the actual-State basis.
        """
        if type(decision_id) is not InvestmentDecisionId:
            raise TypeError("decision_id must be InvestmentDecisionId")
        material_alternatives = await self._alternative_reader.for_decision(decision_id)
        if not material_alternatives or not consequences:
            raise ValueError("material alternatives and consequences are required")
        require_minimum_alternatives(material_alternatives)
        if any(item.decision_id != decision_id for item in material_alternatives):
            raise ValueError("material alternatives belong to another Decision")
        if any(
            type(item) is not ProjectedPortfolioConsequence for item in consequences
        ):
            raise TypeError("consequences must be typed")
        expected = {
            DecisionAlternativeVersionRef(
                EvidenceAlternativeId(item.alternative_id.value),
                DecisionAlternativeRevision(item.revision),
            ): item
            for item in material_alternatives
        }
        if len({item.alternative for item in consequences}) != len(consequences):
            raise ValueError("each material Alternative needs one consequence")
        if {item.alternative for item in consequences} != set(expected):
            raise ValueError("consequences must cover exact material Alternatives")
        if len({item.consequence_id for item in consequences}) != len(consequences):
            raise ValueError("consequence identities must be distinct")
        catalogs = require_initial_claim_catalogs(consequences, initial_claim_catalogs)
        source = await self._state_store.get(source_state_id)
        if source is None:
            raise ValueError("source Portfolio State does not exist")
        _validate_source(
            source, source_state_id, material_alternatives, expected, consequences
        )
        return await self._consequence_store.append_batch(
            decision_id, consequences, catalogs
        )
