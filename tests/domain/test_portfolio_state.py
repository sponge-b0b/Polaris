from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from polaris.domain.portfolio import (
    FinancialInstrumentId,
    PortfolioId,
    PortfolioSource,
    PortfolioState,
    PortfolioStateId,
    RecordedPortfolioState,
)


def _state() -> PortfolioState:
    return PortfolioState(
        state_id=PortfolioStateId(uuid4()),
        portfolio_id=PortfolioId(uuid4()),
        as_of=datetime(2026, 10, 18, tzinfo=UTC),
        source=PortfolioSource(
            "custodian", "position-report-42", datetime(2026, 10, 18, tzinfo=UTC)
        ),
        currency="USD",
        capital_basis=Decimal("100000.00001"),
        cash=Decimal("20000.00001"),
        instrument_id=FinancialInstrumentId(uuid4()),
        position_quantity=Decimal("100.125"),
        position_value=Decimal("80000"),
        exposure_value=Decimal("80500"),
        allocation_fraction=Decimal("0.8"),
        interpretation_basis="Portfolio boundary and custodian valuation at as-of",
    )


def test_decision_grade_state_preserves_distinct_source_and_interpretation() -> None:
    state = _state()
    assert state.source.system == "custodian"
    assert state.source.record_reference == "position-report-42"
    assert state.position_value != state.exposure_value
    assert state.cash == Decimal("20000.00001")
    assert state.capital_basis == Decimal("100000.00001")
    assert state.instrument_id.value.version == 4
    with pytest.raises(FrozenInstanceError):
        state.cash = Decimal("0")  # type: ignore[misc]


def test_state_preserves_instrument_identity_without_symbol_as_authority() -> None:
    state = _state()
    assert state.instrument_id.value.version == 4
    assert "instrument_symbol" not in state.__dataclass_fields__


def test_state_rejects_manufactured_precision() -> None:
    state = _state()
    with pytest.raises(ValueError, match="finite"):
        replace(state, cash=Decimal("NaN"))
    with pytest.raises(ValueError, match="positive"):
        replace(state, capital_basis=Decimal("0"))


def test_recorded_state_preserves_trusted_knowledge_boundary() -> None:
    state = _state()
    later = datetime(2026, 10, 19, tzinfo=UTC)
    fact = RecordedPortfolioState(state, later)
    assert fact.state.state_id == state.state_id
    assert fact.known_at == later
    with pytest.raises(ValueError, match="source observation"):
        RecordedPortfolioState(state, datetime(2026, 10, 17, tzinfo=UTC))
