"""Complete target-owned Human Decision claim catalog history."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.evidence.claims import ClaimCatalogReadUnavailable
from polaris.domain.evidence.claims import (
    ClaimCatalogRevision,
    ClaimCatalogVersion,
    InvalidClaimCatalogHistory,
    validate_claim_catalog_history,
)
from polaris.domain.evidence.judgments import (
    ClaimId,
    EvidenceJudgmentRef,
    HumanInvestmentDecisionRef,
)
from polaris.domain.governance_claim_catalog import GovernanceClaimCatalog
from polaris.domain.governance_judgment_history import (
    HumanDecisionTargetCorrectionDraft,
    HumanDecisionTargetEffect,
    InvalidHumanDecisionTargetHistory,
)

from .governance import HumanDecisionStoreUnavailable
from .governance_history import archive_governance_act_commits
from .intelligence_contract_codec import (
    contract_value_from_payload,
    contract_value_payload,
)
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    human_decision_act_publications,
    human_decision_claim_catalogs,
    human_decision_target_corrections,
)


async def load_catalog_history(
    connection: AsyncConnection, root: HumanInvestmentDecisionRef
) -> tuple[tuple[GovernanceClaimCatalog, ClaimCatalogRevision], ...]:
    if type(root) is not HumanInvestmentDecisionRef:
        raise TypeError("claim catalog target must be a Human Decision root")
    rows = (
        (
            await connection.execute(
                select(
                    human_decision_claim_catalogs,
                    human_decision_act_publications.c.committed_at.label(
                        "trusted_commit_at"
                    ),
                )
                .outerjoin(
                    human_decision_act_publications,
                    human_decision_act_publications.c.act_id
                    == human_decision_claim_catalogs.c.source_act_id,
                )
                .where(human_decision_claim_catalogs.c.decision_ref == root.value)
                .order_by(human_decision_claim_catalogs.c.catalog_version)
            )
        )
        .mappings()
        .all()
    )
    result: list[tuple[GovernanceClaimCatalog, ClaimCatalogRevision]] = []
    historical_ids: frozenset[ClaimId] = frozenset()
    for version, row in enumerate(rows, start=1):
        catalog = contract_value_from_payload(row["catalog"])
        committed_at = row["trusted_commit_at"]
        if not isinstance(catalog, GovernanceClaimCatalog):
            raise InvalidHumanDecisionTargetHistory(
                "stored Governance claim catalog type differs"
            )
        if row["catalog_version"] != version or not isinstance(committed_at, datetime):
            raise InvalidHumanDecisionTargetHistory(
                "stored Governance claim catalog or commit boundary differs"
            )
        if version == 1:
            if row["source_act_id"] != root.value:
                raise InvalidHumanDecisionTargetHistory(
                    "initial claim catalog is not atomic with its target root"
                )
        else:
            source = await connection.scalar(
                select(human_decision_target_corrections.c.correction_id).where(
                    human_decision_target_corrections.c.correction_id
                    == row["source_act_id"],
                    human_decision_target_corrections.c.decision_ref == root.value,
                )
            )
            if source is None:
                raise InvalidHumanDecisionTargetHistory(
                    "claim catalog has no matching owner correction"
                )
            previous = result[-1][0]
            previous.validate_successor(catalog, historical_ids)
            if previous == catalog:
                raise InvalidHumanDecisionTargetHistory(
                    "unchanged catalog cannot advance its version"
                )
        revision = ClaimCatalogRevision(
            root,
            ClaimCatalogVersion(version),
            catalog.claim_ids,
            row["effective_at"],
            committed_at,
        )
        result.append((catalog, revision))
        historical_ids |= catalog.claim_ids
    if result:
        validate_claim_catalog_history(
            tuple(revision for _, revision in result), target=root
        )
    return tuple(result)


async def insert_initial_catalog(
    connection: AsyncConnection,
    root: HumanInvestmentDecisionRef,
    catalog: GovernanceClaimCatalog,
    effective_at: datetime,
) -> None:
    if type(catalog) is not GovernanceClaimCatalog:
        raise TypeError("root requires one explicitly complete claim catalog")
    await connection.execute(
        insert(human_decision_claim_catalogs).values(
            decision_ref=root.value,
            catalog_version=1,
            source_act_id=root.value,
            effective_at=effective_at,
            catalog=contract_value_payload(catalog),
        )
    )


async def insert_correction_catalog(
    connection: AsyncConnection,
    draft: HumanDecisionTargetCorrectionDraft,
    committed_at: datetime,
) -> None:
    previous = await load_catalog_history(connection, draft.root)
    if not previous:
        raise InvalidHumanDecisionTargetHistory("target has no initial claim catalog")
    catalog = draft.catalog
    if (
        draft.effect is HumanDecisionTargetEffect.RETRACT
        and draft.effective_at <= committed_at
    ):
        catalog = GovernanceClaimCatalog(())
    if catalog is None:
        return
    if draft.effective_at > committed_at:
        raise InvalidHumanDecisionTargetHistory(
            "future-effective catalog changes require a later owner commit"
        )
    old = previous[-1][0]
    if catalog == old:
        return
    historical_ids = frozenset(
        claim_id for item, _ in previous for claim_id in item.claim_ids
    )
    old.validate_successor(catalog, historical_ids)
    await connection.execute(
        insert(human_decision_claim_catalogs).values(
            decision_ref=draft.root.value,
            catalog_version=len(previous) + 1,
            source_act_id=draft.correction_id,
            effective_at=draft.effective_at,
            catalog=contract_value_payload(catalog),
        )
    )


class PostgresGovernanceClaimCatalogStore:
    """Expose Governance's complete historical catalog through the Evidence port."""

    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def load_claim_catalog(
        self, target: EvidenceJudgmentRef
    ) -> tuple[ClaimCatalogRevision, ...]:
        if type(target) is not HumanInvestmentDecisionRef:
            raise TypeError("Governance owns only Human Decision claim catalogs")
        try:
            await archive_governance_act_commits(self._engine)
            async with self._engine.connect() as connection:
                history = await load_catalog_history(connection, target)
                return tuple(revision for _, revision in history)
        except (SQLAlchemyError, HumanDecisionStoreUnavailable) as error:
            raise ClaimCatalogReadUnavailable(
                "Governance claim catalog is unavailable"
            ) from error
        except (InvalidHumanDecisionTargetHistory, ValueError, TypeError) as error:
            raise InvalidClaimCatalogHistory(
                "Governance claim catalog history is invalid"
            ) from error
