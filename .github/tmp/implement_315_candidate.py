from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ["CANDIDATE_ROOT"])
SOURCE = ROOT / "src/polaris/application/decisions/relationships.py"
TESTS = ROOT / "tests/application/decisions/test_relationships.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")

source = replace_once(
    source,
    '''        facts = tuple(
            relationship_fact(
                source_decision_id=decision_id,
                target_decision_id=item.decision_id,
                relationship_type=DecisionRelationshipType.RENEWED_FROM,
                relationship_effective_at=command.envelope.effective_at,
                relationship_basis=item.basis,
                mutation=_relationship_mutation(
                    command.envelope, recorded_at, self._new_uuid
                ),
            )
            for item in command.predecessors
        )
        try:
            renewal = renew_decision(
''',
    '''        try:
            facts = tuple(
                relationship_fact(
                    source_decision_id=decision_id,
                    target_decision_id=item.decision_id,
                    relationship_type=DecisionRelationshipType.RENEWED_FROM,
                    relationship_effective_at=command.envelope.effective_at,
                    relationship_basis=item.basis,
                    mutation=_relationship_mutation(
                        command.envelope, recorded_at, self._new_uuid
                    ),
                )
                for item in command.predecessors
            )
            renewal = renew_decision(
''',
    "renewal relationship construction boundary",
)

source = replace_once(
    source,
    '''        facts = tuple(
            relationship_fact(
                source_decision_id=command.source_decision_id,
                target_decision_id=item.decision_id,
                relationship_type=DecisionRelationshipType.SUPERSEDES,
                relationship_effective_at=item.effective_at,
                relationship_basis=item.basis,
                mutation=_relationship_mutation(
                    command.envelope, recorded_at, self._new_uuid
                ),
            )
            for item in command.targets
        )
        try:
            applied = apply_relationship_command(
''',
    '''        try:
            facts = tuple(
                relationship_fact(
                    source_decision_id=command.source_decision_id,
                    target_decision_id=item.decision_id,
                    relationship_type=DecisionRelationshipType.SUPERSEDES,
                    relationship_effective_at=item.effective_at,
                    relationship_basis=item.basis,
                    mutation=_relationship_mutation(
                        command.envelope, recorded_at, self._new_uuid
                    ),
                )
                for item in command.targets
            )
            applied = apply_relationship_command(
''',
    "Supersession relationship construction boundary",
)

source = replace_once(
    source,
    '''        correction = relationship_correction(
            target_relationship_fact_id=command.target_relationship_fact_id,
            effect=command.effect,
            correction_effective_at=command.correction_effective_at,
            correction_basis=command.correction_basis,
            replacement_relationship_effective_at=(
                command.replacement_relationship_effective_at
            ),
            replacement_relationship_basis=command.replacement_relationship_basis,
            mutation=_relationship_mutation(
                command.envelope, recorded_at, self._new_uuid
            ),
        )
        try:
            applied = apply_relationship_command(
''',
    '''        try:
            correction = relationship_correction(
                target_relationship_fact_id=command.target_relationship_fact_id,
                effect=command.effect,
                correction_effective_at=command.correction_effective_at,
                correction_basis=command.correction_basis,
                replacement_relationship_effective_at=(
                    command.replacement_relationship_effective_at
                ),
                replacement_relationship_basis=command.replacement_relationship_basis,
                mutation=_relationship_mutation(
                    command.envelope, recorded_at, self._new_uuid
                ),
            )
            applied = apply_relationship_command(
''',
    "relationship correction construction boundary",
)

SOURCE.write_text(source, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
sentinel = "def test_renewal_relationship_constructor_failure_is_translated() -> None:"
if sentinel in tests:
    raise SystemExit("ticket 315 focused constructor tests already present")

tests += '''\n\n\ndef test_renewal_relationship_constructor_failure_is_translated() -> None:\n    predecessor = _decision(resolved=True)\n    store = FakeRelationshipStore((predecessor,))\n    predecessor_spec = RenewalPredecessor(\n        predecessor.decision_id,\n        RenewedFromRelationshipBasis(("renewal",)),\n    )\n    object.__setattr__(\n        predecessor_spec,\n        "basis",\n        SupersedesRelationshipBasis(("wrong-purpose-basis",)),\n    )\n    command = RenewDecisionCommand(\n        envelope=_envelope((predecessor,)),\n        need_statement="Revisit portfolio exposure",\n        subject=DecisionSubject("Portfolio exposure"),\n        scope=DecisionScope.unresolved(),\n        predecessors=(predecessor_spec,),\n    )\n\n    with pytest.raises(RelationshipConflict):\n        asyncio.run(_service(store).renew(command))\n\n    assert store.history == ()\n    assert store.receipts == {}\n\n\ndef test_supersession_relationship_constructor_cycle_is_translated() -> None:\n    source = _decision()\n    store = FakeRelationshipStore((source,))\n    command = EstablishSupersessionCommand(\n        _envelope((source,)),\n        source.decision_id,\n        (\n            SupersessionTarget(\n                source.decision_id,\n                SupersedesRelationshipBasis(("self-supersession",)),\n                NOW,\n            ),\n        ),\n    )\n\n    with pytest.raises(RelationshipCycle):\n        asyncio.run(_service(store).establish_supersession(command))\n\n    assert store.history == ()\n    assert store.receipts == {}\n\n\ndef test_relationship_correction_constructor_history_failure_is_translated() -> None:\n    source = _decision()\n    target = _decision()\n    store = FakeRelationshipStore((source, target))\n    command = CorrectDecisionRelationshipCommand(\n        envelope=_envelope((source, target)),\n        target_relationship_fact_id=DecisionRelationshipFactId(uuid4()),\n        effect=DecisionRelationshipCorrectionEffect.QUALIFY,\n        correction_effective_at=NOW,\n        correction_basis=DecisionRelationshipCorrectionBasis(("qualification",)),\n    )\n\n    with pytest.raises(RelationshipHistoryInvalidOrIncomplete):\n        asyncio.run(\n            DecisionRelationshipCorrectionService(\n                store=store,\n                now=lambda: NOW,\n                new_uuid=uuid4,\n            ).correct(command)\n        )\n\n    assert store.history == ()\n    assert store.receipts == {}\n'''

TESTS.write_text(tests, encoding="utf-8")
