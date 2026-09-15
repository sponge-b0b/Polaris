from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ["CANDIDATE_ROOT"])


def update(path: str, transform) -> None:
    file_path = ROOT / path
    text = file_path.read_text()
    updated = transform(text)
    if updated == text:
        raise SystemExit(f"no change produced for {path}")
    file_path.write_text(updated)


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def edit_contracts(text: str) -> str:
    text = replace_once(
        text,
        "class PersistenceUnavailable(DecisionApplicationError):\n    pass\n",
        "class DecisionCommandReadUnavailable(Exception):\n"
        "    \"\"\"Technology-neutral failure contract for command-side persistence reads.\"\"\"\n\n\n"
        "class PersistenceUnavailable(DecisionApplicationError):\n    pass\n",
        label="contracts read exception",
    )
    text = replace_once(
        text,
        "class DecisionMemoryReader(Protocol):\n"
        "    async def find_unresolved_continuity_candidates(\n"
        "        self, *, known_at: datetime\n"
        "    ) -> tuple[InvestmentDecisionId, ...]: ...\n",
        "class DecisionMemoryReader(Protocol):\n"
        "    async def find_unresolved_continuity_candidates(\n"
        "        self, *, known_at: datetime\n"
        "    ) -> tuple[InvestmentDecisionId, ...]:\n"
        "        \"\"\"Return candidates or raise DecisionCommandReadUnavailable.\"\"\"\n"
        "        ...\n",
        label="candidate read protocol",
    )
    text = replace_once(
        text,
        "class DecisionCommandStore(Protocol):\n"
        "    async def get_initiation_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> InitiationReceipt | None: ...\n",
        "class DecisionCommandStore(Protocol):\n"
        "    async def get_initiation_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> InitiationReceipt | None:\n"
        "        \"\"\"Return a receipt or raise DecisionCommandReadUnavailable.\"\"\"\n"
        "        ...\n",
        label="initiation receipt protocol",
    )
    return text


def edit_init_export(text: str) -> str:
    text = replace_once(
        text,
        "    DecisionCommandEnvelope,\n    DecisionCommandStore,\n",
        "    DecisionCommandEnvelope,\n    DecisionCommandReadUnavailable,\n    DecisionCommandStore,\n",
        label="export import",
    )
    text = replace_once(
        text,
        '    "DecisionCommandEnvelope",\n    "DecisionCommandState",\n',
        '    "DecisionCommandEnvelope",\n    "DecisionCommandReadUnavailable",\n    "DecisionCommandState",\n',
        label="export all",
    )
    return text


def edit_initiation(text: str) -> str:
    text = replace_once(
        text,
        "    DecisionCommandStore,\n    DecisionMemoryReader,\n",
        "    DecisionCommandReadUnavailable,\n    DecisionCommandStore,\n    DecisionMemoryReader,\n",
        label="initiation import",
    )
    text = replace_once(
        text,
        "        prior = await self._store.get_initiation_receipt(command.envelope.operation_id)\n"
        "        if prior is not None:\n",
        "        try:\n"
        "            prior = await self._store.get_initiation_receipt(\n"
        "                command.envelope.operation_id\n"
        "            )\n"
        "        except DecisionCommandReadUnavailable as error:\n"
        "            raise PersistenceUnavailable(str(error)) from error\n"
        "        if prior is not None:\n",
        label="initiation receipt read translation",
    )
    text = replace_once(
        text,
        "        candidate_ids = frozenset(\n"
        "            await self._reader.find_unresolved_continuity_candidates(\n"
        "                known_at=recorded_at\n"
        "            )\n"
        "        )\n",
        "        try:\n"
        "            candidate_ids = frozenset(\n"
        "                await self._reader.find_unresolved_continuity_candidates(\n"
        "                    known_at=recorded_at\n"
        "                )\n"
        "            )\n"
        "        except DecisionCommandReadUnavailable as error:\n"
        "            raise PersistenceUnavailable(str(error)) from error\n",
        label="initiation candidate read translation",
    )
    return text


def edit_ordinary(text: str) -> str:
    text = replace_once(
        text,
        "    DecisionCommandEnvelope,\n    DecisionCommandStore,\n",
        "    DecisionCommandEnvelope,\n    DecisionCommandReadUnavailable,\n    DecisionCommandStore,\n",
        label="ordinary import",
    )
    text = replace_once(
        text,
        "    async def get_mutation_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> DecisionMutationReceipt | None: ...\n\n"
        "    async def load_decision_for_command(\n"
        "        self,\n"
        "        decision_id: InvestmentDecisionId,\n"
        "        *,\n"
        "        known_at: datetime,\n"
        "    ) -> DecisionCommandState | None: ...\n",
        "    async def get_mutation_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> DecisionMutationReceipt | None:\n"
        "        \"\"\"Return a receipt or raise DecisionCommandReadUnavailable.\"\"\"\n"
        "        ...\n\n"
        "    async def load_decision_for_command(\n"
        "        self,\n"
        "        decision_id: InvestmentDecisionId,\n"
        "        *,\n"
        "        known_at: datetime,\n"
        "    ) -> DecisionCommandState | None:\n"
        "        \"\"\"Return command state or raise DecisionCommandReadUnavailable.\"\"\"\n"
        "        ...\n",
        label="mutation read protocols",
    )
    text = replace_once(
        text,
        "    operation_id = command.envelope.operation_id\n"
        "    prior = await store.get_mutation_receipt(operation_id)\n"
        "    if prior is not None:\n",
        "    operation_id = command.envelope.operation_id\n"
        "    try:\n"
        "        prior = await store.get_mutation_receipt(operation_id)\n"
        "    except DecisionCommandReadUnavailable as error:\n"
        "        raise PersistenceUnavailable(str(error)) from error\n"
        "    if prior is not None:\n",
        label="mutation receipt read translation",
    )
    text = replace_once(
        text,
        "    recorded_at = _recording_time(now())\n"
        "    state = await store.load_decision_for_command(\n"
        "        command.decision_id,\n"
        "        known_at=recorded_at,\n"
        "    )\n",
        "    recorded_at = _recording_time(now())\n"
        "    try:\n"
        "        state = await store.load_decision_for_command(\n"
        "            command.decision_id,\n"
        "            known_at=recorded_at,\n"
        "        )\n"
        "    except DecisionCommandReadUnavailable as error:\n"
        "        raise PersistenceUnavailable(str(error)) from error\n",
        label="mutation state read translation",
    )
    return text


def edit_relationships(text: str) -> str:
    text = replace_once(
        text,
        "    DecisionCommandEnvelope,\n    DecisionMemoryReader,\n",
        "    DecisionCommandEnvelope,\n    DecisionCommandReadUnavailable,\n    DecisionMemoryReader,\n",
        label="relationships import",
    )
    text = replace_once(
        text,
        "class DecisionRelationshipStore(Protocol):\n"
        "    async def get_relationship_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> DecisionRelationshipReceipt | None: ...\n\n"
        "    async def load_relationship_state(\n"
        "        self, *, known_at: datetime\n"
        "    ) -> DecisionRelationshipState: ...\n",
        "class DecisionRelationshipStore(Protocol):\n"
        "    async def get_relationship_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> DecisionRelationshipReceipt | None:\n"
        "        \"\"\"Return a receipt or raise DecisionCommandReadUnavailable.\"\"\"\n"
        "        ...\n\n"
        "    async def load_relationship_state(\n"
        "        self, *, known_at: datetime\n"
        "    ) -> DecisionRelationshipState:\n"
        "        \"\"\"Return relationship state or raise DecisionCommandReadUnavailable.\"\"\"\n"
        "        ...\n",
        label="relationship read protocols",
    )

    receipt_old = (
        "        prior = await self._store.get_relationship_receipt(\n"
        "            command.envelope.operation_id\n"
        "        )\n"
    )
    receipt_new = (
        "        prior = await _read_relationship_receipt(\n"
        "            self._store, command.envelope.operation_id\n"
        "        )\n"
    )
    count = text.count(receipt_old)
    if count != 3:
        raise SystemExit(f"relationship receipt reads: expected 3 matches, found {count}")
    text = text.replace(receipt_old, receipt_new)

    state_old = "        state = await self._store.load_relationship_state(known_at=recorded_at)\n"
    state_new = "        state = await _read_relationship_state(self._store, recorded_at)\n"
    count = text.count(state_old)
    if count != 3:
        raise SystemExit(f"relationship state reads: expected 3 matches, found {count}")
    text = text.replace(state_old, state_new)

    text = replace_once(
        text,
        "        candidate_ids = frozenset(\n"
        "            await self._reader.find_unresolved_continuity_candidates(\n"
        "                known_at=recorded_at\n"
        "            )\n"
        "        )\n",
        "        candidate_ids = await _read_continuity_candidates(\n"
        "            self._reader, recorded_at\n"
        "        )\n",
        label="renewal candidate read translation",
    )

    helper_anchor = "\n\nasync def _commit_relationship(\n"
    helpers = '''\n\nasync def _read_relationship_receipt(\n    store: DecisionRelationshipStore,\n    operation_id: OperationId,\n) -> DecisionRelationshipReceipt | None:\n    try:\n        return await store.get_relationship_receipt(operation_id)\n    except DecisionCommandReadUnavailable as error:\n        raise PersistenceUnavailable(str(error)) from error\n\n\nasync def _read_relationship_state(\n    store: DecisionRelationshipStore,\n    known_at: datetime,\n) -> DecisionRelationshipState:\n    try:\n        return await store.load_relationship_state(known_at=known_at)\n    except DecisionCommandReadUnavailable as error:\n        raise PersistenceUnavailable(str(error)) from error\n\n\nasync def _read_continuity_candidates(\n    reader: DecisionMemoryReader,\n    known_at: datetime,\n) -> frozenset[InvestmentDecisionId]:\n    try:\n        return frozenset(\n            await reader.find_unresolved_continuity_candidates(known_at=known_at)\n        )\n    except DecisionCommandReadUnavailable as error:\n        raise PersistenceUnavailable(str(error)) from error\n'''
    text = replace_once(
        text,
        helper_anchor,
        helpers + helper_anchor,
        label="relationship read helpers",
    )
    return text


def edit_test_initiation(text: str) -> str:
    text = replace_once(
        text,
        "    DecisionCommandEnvelope,\n    DecisionInitiationService,\n",
        "    DecisionCommandEnvelope,\n    DecisionCommandReadUnavailable,\n    DecisionInitiationService,\n",
        label="test initiation import",
    )
    text = replace_once(
        text,
        "        add_after_read: InvestmentDecisionId | None = None,\n"
        "        unavailable: bool = False,\n",
        "        add_after_read: InvestmentDecisionId | None = None,\n"
        "        unavailable: bool = False,\n"
        "        read_failure: str | None = None,\n",
        label="test initiation fake init arg",
    )
    text = replace_once(
        text,
        "        self._add_after_read = add_after_read\n"
        "        self._unavailable = unavailable\n",
        "        self._add_after_read = add_after_read\n"
        "        self._unavailable = unavailable\n"
        "        self._read_failure = read_failure\n",
        label="test initiation fake init state",
    )
    text = replace_once(
        text,
        "    async def find_unresolved_continuity_candidates(\n"
        "        self, *, known_at: datetime\n"
        "    ) -> tuple[InvestmentDecisionId, ...]:\n"
        "        assert known_at.tzinfo is not None\n",
        "    async def find_unresolved_continuity_candidates(\n"
        "        self, *, known_at: datetime\n"
        "    ) -> tuple[InvestmentDecisionId, ...]:\n"
        "        if self._read_failure == \"candidates\":\n"
        "            raise DecisionCommandReadUnavailable(\"fake candidate read unavailable\")\n"
        "        assert known_at.tzinfo is not None\n",
        label="test initiation candidate failure",
    )
    text = replace_once(
        text,
        "    async def get_initiation_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> InitiationReceipt | None:\n"
        "        with self._lock:\n",
        "    async def get_initiation_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> InitiationReceipt | None:\n"
        "        if self._read_failure == \"receipt\":\n"
        "            raise DecisionCommandReadUnavailable(\"fake receipt read unavailable\")\n"
        "        with self._lock:\n",
        label="test initiation receipt failure",
    )
    addition = '''\n\n@pytest.mark.parametrize("read_failure", ("receipt", "candidates"))\ndef test_command_read_unavailability_translates_without_commit(read_failure: str) -> None:\n    store = FakeDecisionStore(read_failure=read_failure)\n    service = _service(store, uuid4(), uuid4(), uuid4())\n\n    with pytest.raises(PersistenceUnavailable) as exc_info:\n        asyncio.run(service.initiate(_command()))\n\n    assert isinstance(exc_info.value.__cause__, DecisionCommandReadUnavailable)\n    assert store.decisions == ()\n    assert store.receipts == ()\n\n\ndef test_unrelated_read_failure_is_not_swallowed() -> None:\n    class RawFailureStore(FakeDecisionStore):\n        async def get_initiation_receipt(\n            self, operation_id: OperationId\n        ) -> InitiationReceipt | None:\n            raise RuntimeError("unrelated read failure")\n\n    store = RawFailureStore()\n    service = _service(store, uuid4(), uuid4(), uuid4())\n\n    with pytest.raises(RuntimeError, match="unrelated read failure"):\n        asyncio.run(service.initiate(_command()))\n\n    assert store.decisions == ()\n    assert store.receipts == ()\n'''
    return text.rstrip() + addition + "\n"


def edit_test_ordinary(text: str) -> str:
    text = replace_once(
        text,
        "    DecisionCommandEnvelope,\n    DecisionCommandState,\n",
        "    DecisionCommandEnvelope,\n    DecisionCommandReadUnavailable,\n    DecisionCommandState,\n",
        label="test ordinary import",
    )
    text = replace_once(
        text,
        "        unavailable: bool = False,\n"
        "        conflict_on_commit: bool = False,\n",
        "        unavailable: bool = False,\n"
        "        conflict_on_commit: bool = False,\n"
        "        read_failure: str | None = None,\n",
        label="test ordinary fake init arg",
    )
    text = replace_once(
        text,
        "        self._unavailable = unavailable\n"
        "        self._conflict_on_commit = conflict_on_commit\n",
        "        self._unavailable = unavailable\n"
        "        self._conflict_on_commit = conflict_on_commit\n"
        "        self._read_failure = read_failure\n",
        label="test ordinary fake init state",
    )
    text = replace_once(
        text,
        "    async def get_mutation_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> DecisionMutationReceipt | None:\n"
        "        with self._lock:\n",
        "    async def get_mutation_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> DecisionMutationReceipt | None:\n"
        "        if self._read_failure == \"receipt\":\n"
        "            raise DecisionCommandReadUnavailable(\"fake receipt read unavailable\")\n"
        "        with self._lock:\n",
        label="test ordinary receipt failure",
    )
    text = replace_once(
        text,
        "    ) -> DecisionCommandState | None:\n"
        "        assert known_at.tzinfo is not None\n"
        "        with self._lock:\n",
        "    ) -> DecisionCommandState | None:\n"
        "        if self._read_failure == \"state\":\n"
        "            raise DecisionCommandReadUnavailable(\"fake state read unavailable\")\n"
        "        assert known_at.tzinfo is not None\n"
        "        with self._lock:\n",
        label="test ordinary state failure",
    )
    addition = '''\n\n@pytest.mark.parametrize("read_failure", ("receipt", "state"))\ndef test_command_read_unavailability_translates_without_mutation(\n    read_failure: str,\n) -> None:\n    decision = _decision()\n    store = FakeDecisionStore(decision, read_failure=read_failure)\n    command = ReviseDecisionSubjectCommand(\n        envelope=_envelope(decision),\n        decision_id=decision.decision_id,\n        subject=DecisionSubject("Changed subject"),\n        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,\n    )\n\n    with pytest.raises(PersistenceUnavailable) as exc_info:\n        asyncio.run(_service(store).revise_subject(command))\n\n    assert isinstance(exc_info.value.__cause__, DecisionCommandReadUnavailable)\n    assert store.decision == decision\n    assert store.receipts == ()\n'''
    return text.rstrip() + addition + "\n"


def edit_test_relationships(text: str) -> str:
    text = replace_once(
        text,
        "    DecisionCommandEnvelope,\n    DecisionRelationshipCommit,\n",
        "    DecisionCommandEnvelope,\n    DecisionCommandReadUnavailable,\n    DecisionRelationshipCommit,\n",
        label="test relationship import",
    )
    text = replace_once(
        text,
        "    async def find_unresolved_continuity_candidates(\n"
        "        self, *, known_at: datetime\n"
        "    ) -> tuple[InvestmentDecisionId, ...]:\n"
        "        assert known_at.tzinfo is not None\n",
        "    async def find_unresolved_continuity_candidates(\n"
        "        self, *, known_at: datetime\n"
        "    ) -> tuple[InvestmentDecisionId, ...]:\n"
        "        if self._store.candidate_read_unavailable:\n"
        "            raise DecisionCommandReadUnavailable(\"fake candidate read unavailable\")\n"
        "        assert known_at.tzinfo is not None\n",
        label="test relationship candidate failure",
    )
    text = replace_once(
        text,
        "        unavailable: bool = False,\n"
        "        barrier: threading.Barrier | None = None,\n",
        "        unavailable: bool = False,\n"
        "        barrier: threading.Barrier | None = None,\n"
        "        read_failure: str | None = None,\n"
        "        candidate_read_unavailable: bool = False,\n",
        label="test relationship fake init args",
    )
    text = replace_once(
        text,
        "        self.unavailable = unavailable\n"
        "        self.barrier = barrier\n",
        "        self.unavailable = unavailable\n"
        "        self.barrier = barrier\n"
        "        self.read_failure = read_failure\n"
        "        self.candidate_read_unavailable = candidate_read_unavailable\n",
        label="test relationship fake state",
    )
    text = replace_once(
        text,
        "    async def get_relationship_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> DecisionRelationshipReceipt | None:\n"
        "        with self.lock:\n",
        "    async def get_relationship_receipt(\n"
        "        self, operation_id: OperationId\n"
        "    ) -> DecisionRelationshipReceipt | None:\n"
        "        if self.read_failure == \"receipt\":\n"
        "            raise DecisionCommandReadUnavailable(\"fake receipt read unavailable\")\n"
        "        with self.lock:\n",
        label="test relationship receipt failure",
    )
    text = replace_once(
        text,
        "    async def load_relationship_state(\n"
        "        self, *, known_at: datetime\n"
        "    ) -> DecisionRelationshipState:\n"
        "        assert known_at.tzinfo is not None\n",
        "    async def load_relationship_state(\n"
        "        self, *, known_at: datetime\n"
        "    ) -> DecisionRelationshipState:\n"
        "        if self.read_failure == \"state\":\n"
        "            raise DecisionCommandReadUnavailable(\"fake state read unavailable\")\n"
        "        assert known_at.tzinfo is not None\n",
        label="test relationship state failure",
    )
    addition = '''\n\n@pytest.mark.parametrize("read_failure", ("receipt", "state"))\ndef test_relationship_state_reads_translate_unavailability_without_commit(\n    read_failure: str,\n) -> None:\n    source = _decision()\n    target = _decision()\n    store = FakeRelationshipStore((source, target), read_failure=read_failure)\n\n    with pytest.raises(PersistenceUnavailable) as exc_info:\n        _supersede(store, source, target)\n\n    assert isinstance(exc_info.value.__cause__, DecisionCommandReadUnavailable)\n    assert store.history == ()\n    assert store.receipts == {}\n\n\ndef test_renewal_candidate_read_translates_unavailability_without_commit() -> None:\n    predecessor = _decision(resolved=True)\n    store = FakeRelationshipStore(\n        (predecessor,),\n        candidate_read_unavailable=True,\n    )\n    command = RenewDecisionCommand(\n        envelope=_envelope((predecessor,)),\n        need_statement="Revisit portfolio exposure",\n        subject=DecisionSubject("Portfolio exposure"),\n        scope=DecisionScope.unresolved(),\n        predecessors=(\n            RenewalPredecessor(\n                predecessor.decision_id,\n                RenewedFromRelationshipBasis(("renewal",)),\n            ),\n        ),\n    )\n\n    with pytest.raises(PersistenceUnavailable) as exc_info:\n        asyncio.run(_service(store).renew(command))\n\n    assert isinstance(exc_info.value.__cause__, DecisionCommandReadUnavailable)\n    assert store.history == ()\n    assert store.receipts == {}\n'''
    return text.rstrip() + addition + "\n"


update("src/polaris/application/decisions/contracts.py", edit_contracts)
update("src/polaris/application/decisions/__init__.py", edit_init_export)
update("src/polaris/application/decisions/initiation.py", edit_initiation)
update("src/polaris/application/decisions/ordinary_work.py", edit_ordinary)
update("src/polaris/application/decisions/relationships.py", edit_relationships)
update("tests/application/decisions/test_initiation.py", edit_test_initiation)
update("tests/application/decisions/test_ordinary_work.py", edit_test_ordinary)
update("tests/application/decisions/test_relationships.py", edit_test_relationships)
