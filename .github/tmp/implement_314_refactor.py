from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ["CANDIDATE_ROOT"])


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def update(path: str, transform) -> None:
    file_path = ROOT / path
    text = file_path.read_text()
    updated = transform(text)
    if updated == text:
        raise SystemExit(f"no refactor change produced for {path}")
    file_path.write_text(updated)


def edit_initiation(text: str) -> str:
    text = replace_once(
        text,
        "        try:\n"
        "            prior = await self._store.get_initiation_receipt(\n"
        "                command.envelope.operation_id\n"
        "            )\n"
        "        except DecisionCommandReadUnavailable as error:\n"
        "            raise PersistenceUnavailable(str(error)) from error\n",
        "        prior = await _read_initiation_receipt(\n"
        "            self._store, command.envelope.operation_id\n"
        "        )\n",
        label="initiation receipt helper call",
    )
    text = replace_once(
        text,
        "        try:\n"
        "            candidate_ids = frozenset(\n"
        "                await self._reader.find_unresolved_continuity_candidates(\n"
        "                    known_at=recorded_at\n"
        "                )\n"
        "            )\n"
        "        except DecisionCommandReadUnavailable as error:\n"
        "            raise PersistenceUnavailable(str(error)) from error\n",
        "        candidate_ids = await _read_continuity_candidates(\n"
        "            self._reader, recorded_at\n"
        "        )\n",
        label="initiation candidates helper call",
    )
    helpers = '''\n\nasync def _read_initiation_receipt(\n    store: DecisionCommandStore,\n    operation_id: OperationId,\n) -> InitiationReceipt | None:\n    try:\n        return await store.get_initiation_receipt(operation_id)\n    except DecisionCommandReadUnavailable as error:\n        raise PersistenceUnavailable(str(error)) from error\n\n\nasync def _read_continuity_candidates(\n    reader: DecisionMemoryReader,\n    known_at: datetime,\n) -> frozenset[InvestmentDecisionId]:\n    try:\n        return frozenset(\n            await reader.find_unresolved_continuity_candidates(known_at=known_at)\n        )\n    except DecisionCommandReadUnavailable as error:\n        raise PersistenceUnavailable(str(error)) from error\n'''
    return replace_once(
        text,
        "\n\ndef _recording_time(value: datetime) -> datetime:\n",
        helpers + "\n\ndef _recording_time(value: datetime) -> datetime:\n",
        label="initiation read helpers",
    )


def edit_ordinary(text: str) -> str:
    text = replace_once(
        text,
        "    try:\n"
        "        prior = await store.get_mutation_receipt(operation_id)\n"
        "    except DecisionCommandReadUnavailable as error:\n"
        "        raise PersistenceUnavailable(str(error)) from error\n",
        "    prior = await _read_mutation_receipt(store, operation_id)\n",
        label="mutation receipt helper call",
    )
    text = replace_once(
        text,
        "    try:\n"
        "        state = await store.load_decision_for_command(\n"
        "            command.decision_id,\n"
        "            known_at=recorded_at,\n"
        "        )\n"
        "    except DecisionCommandReadUnavailable as error:\n"
        "        raise PersistenceUnavailable(str(error)) from error\n",
        "    state = await _read_decision_state(\n"
        "        store, command.decision_id, recorded_at\n"
        "    )\n",
        label="mutation state helper call",
    )
    helpers = '''\n\nasync def _read_mutation_receipt(\n    store: DecisionMutationStore,\n    operation_id: OperationId,\n) -> DecisionMutationReceipt | None:\n    try:\n        return await store.get_mutation_receipt(operation_id)\n    except DecisionCommandReadUnavailable as error:\n        raise PersistenceUnavailable(str(error)) from error\n\n\nasync def _read_decision_state(\n    store: DecisionMutationStore,\n    decision_id: InvestmentDecisionId,\n    known_at: datetime,\n) -> DecisionCommandState | None:\n    try:\n        return await store.load_decision_for_command(decision_id, known_at=known_at)\n    except DecisionCommandReadUnavailable as error:\n        raise PersistenceUnavailable(str(error)) from error\n'''
    return replace_once(
        text,
        "\n\nasync def _execute_mutation(\n",
        helpers + "\n\nasync def _execute_mutation(\n",
        label="mutation read helpers",
    )


update("src/polaris/application/decisions/initiation.py", edit_initiation)
update("src/polaris/application/decisions/ordinary_work.py", edit_ordinary)
