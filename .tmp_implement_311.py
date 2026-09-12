from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"expected exactly one replacement anchor in {path}, found {count}"
        )
    path.write_text(text.replace(old, new, 1))


ordinary_work = Path("src/polaris/application/decisions/ordinary_work.py")
replace_once(
    ordinary_work,
    '''    if state.applicability is DecisionApplicability.CONTESTED:\n        raise DecisionOperativeStatusContested(\n            "External Resolution requires determinate Decision applicability"\n        )\n    if state.applicability not in (\n        DecisionApplicability.OPERATIVE,\n        DecisionApplicability.NON_OPERATIVE,\n    ):''',
    '''    if state.applicability not in (\n        DecisionApplicability.OPERATIVE,\n        DecisionApplicability.NON_OPERATIVE,\n        DecisionApplicability.CONTESTED,\n    ):''',
)

resolution_tests = Path("tests/application/decisions/test_resolution.py")
replace_once(
    resolution_tests,
    '''@pytest.mark.parametrize(\n    ("kind", "applicability", "error_type"),\n    (\n        (\n            "substantive",\n            DecisionApplicability.NON_OPERATIVE,\n            DecisionNonOperative,\n        ),\n        (\n            "substantive",\n            DecisionApplicability.CONTESTED,\n            DecisionOperativeStatusContested,\n        ),\n        (\n            "external",\n            DecisionApplicability.CONTESTED,\n            DecisionOperativeStatusContested,\n        ),\n    ),\n)\ndef test_nonoperative_and_contested_resolution_fail_closed(\n    kind: str,\n    applicability: DecisionApplicability,\n    error_type: type[Exception],\n) -> None:\n    decision = _decision()\n    store = FakeDecisionStore(decision, applicability=applicability)\n    service = _service(store)\n    if kind == "substantive":\n        call = service.apply_substantive_resolution(\n            ApplySubstantiveResolutionCommand(\n                _envelope(decision), decision.decision_id, _resolving_basis()\n            )\n        )\n    else:\n        call = service.apply_external_resolution(\n            ApplyExternalResolutionCommand(\n                _envelope(decision),\n                decision.decision_id,\n                ExternalResolutionBasis("external-elimination"),\n            )\n        )\n\n    with pytest.raises(error_type):\n        asyncio.run(call)\n    assert store.decision == decision\n    assert store.receipts == ()\n''',
    '''@pytest.mark.parametrize(\n    ("applicability", "error_type"),\n    (\n        (DecisionApplicability.NON_OPERATIVE, DecisionNonOperative),\n        (\n            DecisionApplicability.CONTESTED,\n            DecisionOperativeStatusContested,\n        ),\n    ),\n)\ndef test_substantive_resolution_nonoperative_and_contested_fail_closed(\n    applicability: DecisionApplicability,\n    error_type: type[Exception],\n) -> None:\n    decision = _decision()\n    store = FakeDecisionStore(decision, applicability=applicability)\n    call = _service(store).apply_substantive_resolution(\n        ApplySubstantiveResolutionCommand(\n            _envelope(decision), decision.decision_id, _resolving_basis()\n        )\n    )\n\n    with pytest.raises(error_type):\n        asyncio.run(call)\n    assert store.decision == decision\n    assert store.receipts == ()\n''',
)
replace_once(
    resolution_tests,
    '''def test_external_resolution_accepts_nonoperative_unresolved_decision() -> None:\n    decision = _decision()\n    store = FakeDecisionStore(\n        decision,\n        applicability=DecisionApplicability.NON_OPERATIVE,\n    )\n\n    result = asyncio.run(\n        _service(store).apply_external_resolution(\n            ApplyExternalResolutionCommand(\n                _envelope(decision),\n                decision.decision_id,\n                ExternalResolutionBasis("external-elimination"),\n            )\n        )\n    )\n\n    assert result.kind is DecisionMutationResultKind.APPLIED\n    assert (\n        store.decision.disposition is DecisionLifecycleDisposition.EXTERNALLY_RESOLVED\n    )\n    assert len(store.receipts) == 1\n''',
    '''@pytest.mark.parametrize(\n    "applicability",\n    (DecisionApplicability.NON_OPERATIVE, DecisionApplicability.CONTESTED),\n)\ndef test_external_resolution_accepts_unresolved_regardless_of_applicability(\n    applicability: DecisionApplicability,\n) -> None:\n    decision = _decision()\n    store = FakeDecisionStore(decision, applicability=applicability)\n\n    result = asyncio.run(\n        _service(store).apply_external_resolution(\n            ApplyExternalResolutionCommand(\n                _envelope(decision),\n                decision.decision_id,\n                ExternalResolutionBasis("external-elimination"),\n            )\n        )\n    )\n\n    assert result.kind is DecisionMutationResultKind.APPLIED\n    assert (\n        store.decision.disposition is DecisionLifecycleDisposition.EXTERNALLY_RESOLVED\n    )\n    assert len(store.receipts) == 1\n''',
)

print("ticket 311 implementation applied")
