from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from json import dumps
from types import SimpleNamespace
from typing import Any

import pytest

from application.persistence.backtesting import backtest_result_to_persistence_bundle
from application.services.backtesting import BacktestApplicationService
from application.services.backtesting import BacktestExpectedOutcome
from application.services.backtesting import BacktestRunRequest
from application.services.backtesting import BacktestScenario
from application.services.base import ServiceRequest


_FIXED_TIME = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


class DeterministicGoldenWorkflowFacade:
    def __init__(
        self, *, node_outputs: dict[str, dict[str, Any]] | None = None
    ) -> None:
        self.call_count = 0
        self._node_outputs = node_outputs

    async def run_workflow(
        self,
        workflow_name: str,
        execution_id: str | None = None,
        mode: str = "live",
        workflow_inputs: Mapping[str, Any] | None = None,
        simulation_time: datetime | None = None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        if simulation_time is None:
            raise AssertionError("simulation_time is required")
        if execution_id is None:
            raise AssertionError("execution_id is required")
        if workflow_inputs is None:
            raise AssertionError("workflow_inputs are required")
        assert workflow_inputs["symbol"] == "SPY"
        assert workflow_inputs["days"] == 120
        self.call_count += 1
        node_outputs = (
            deepcopy(self._node_outputs)
            if self._node_outputs is not None
            else _golden_node_outputs()
        )
        for output in node_outputs.values():
            output["execution_metadata"] = {
                "duration_seconds": self.call_count,
            }
        return SimpleNamespace(
            success=True,
            execution_id=execution_id,
            execution_result=SimpleNamespace(
                final_context=SimpleNamespace(
                    node_outputs=node_outputs,
                )
            ),
        )


@pytest.mark.asyncio
async def test_golden_backtest_verifies_full_decision_chain_and_is_repeatable() -> None:
    scenario = _golden_scenario()
    service = BacktestApplicationService(
        workflow_facade=DeterministicGoldenWorkflowFacade(),
        clock=lambda: _FIXED_TIME,
        run_id_factory=lambda: "backtest-golden",
    )
    request = ServiceRequest(
        payload=BacktestRunRequest(
            scenario=scenario,
            persist_results=False,
            checkpoint_workflow_runs=False,
        )
    )

    first = await service.run(request)
    second = await service.run(request)

    assert first.result is not None
    assert second.result is not None
    assert first.result.success is True
    assert first.result.status == "succeeded"
    assert len(first.result.verifications) == len(scenario.expected_outcomes)
    assert all(verification.passed for verification in first.result.verifications)
    assert first.result.steps[0].workflow_run_id == "backtest-golden-step-000000"
    technical_output = first.result.steps[0].node_outputs["technical_agent"]
    assert isinstance(technical_output, dict)
    assert "execution_metadata" not in technical_output
    assert first.result.to_dict() == second.result.to_dict()
    assert _canonical_strategy_decision(first.result) == _canonical_strategy_decision(
        second.result
    )
    assert backtest_result_to_persistence_bundle(
        first.result
    ) == backtest_result_to_persistence_bundle(second.result)
    verified_count = len(scenario.expected_outcomes)
    assert (
        f"Verified Expectations: {verified_count} / {verified_count}"
        in first.result.artifacts["console"]
    )
    assert "## Deterministic Verification" in first.result.artifacts["markdown"]
    assert '"passed": true' in first.result.artifacts["json"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_name", "expected_selected", "expected_status", "expected_score", "reason"),
    (
        ("bullish", "bull", "selected", "0.45", None),
        ("bearish", "bear", "selected", "-0.45", None),
        ("sideways", "sideways", "selected", "0.00", None),
        ("conflict", None, "degraded", "0.00", "tied_candidates"),
        ("missing_data", None, "degraded", "0.00", "missing_hypothesis"),
        ("invalidation", "bear", "selected", "-0.40", None),
    ),
)
async def test_strategy_hypothesis_scenarios_are_deterministically_verified(
    case_name: str,
    expected_selected: str | None,
    expected_status: str,
    expected_score: str,
    reason: str | None,
) -> None:
    scenario = _golden_scenario(
        expected_outcomes=_strategy_case_expected_outcomes(
            expected_selected=expected_selected,
            expected_status=expected_status,
            expected_score=expected_score,
            reason=reason,
            expect_invalidated_bull=case_name == "invalidation",
        )
    )
    service = BacktestApplicationService(
        workflow_facade=DeterministicGoldenWorkflowFacade(
            node_outputs=_golden_node_outputs(
                strategy_output=_strategy_output_for_case(case_name)
            )
        ),
        clock=lambda: _FIXED_TIME,
        run_id_factory=lambda: f"backtest-{case_name}",
    )
    request = ServiceRequest(
        payload=BacktestRunRequest(
            scenario=scenario,
            persist_results=False,
            checkpoint_workflow_runs=False,
        )
    )

    first = await service.run(request)
    second = await service.run(request)

    assert first.result is not None
    assert second.result is not None
    assert first.result.success is True
    assert all(verification.passed for verification in first.result.verifications)
    assert _canonical_strategy_decision(first.result) == _canonical_strategy_decision(
        second.result
    )


@pytest.mark.asyncio
async def test_failed_expected_outcome_fails_run_with_attributable_evidence() -> None:
    scenario = _golden_scenario(
        expected_outcomes=(
            BacktestExpectedOutcome(
                target="risk.composite_risk",
                expectation_type="max",
                expected="0.20",
            ),
        )
    )
    service = BacktestApplicationService(
        workflow_facade=DeterministicGoldenWorkflowFacade(),
        clock=lambda: _FIXED_TIME,
        run_id_factory=lambda: "backtest-failed-verification",
    )

    response = await service.run(
        ServiceRequest(
            payload=BacktestRunRequest(
                scenario=scenario,
                persist_results=False,
                checkpoint_workflow_runs=False,
            )
        )
    )

    assert response.result is not None
    assert response.result.success is False
    assert response.result.status == "failed"
    assert response.result.verifications[0].passed is False
    assert response.result.verifications[0].actual == Decimal("0.25")
    assert response.result.metadata["verification_failure_count"] == 1


@pytest.mark.asyncio
async def test_injected_backtest_clock_must_be_timezone_aware() -> None:
    service = BacktestApplicationService(
        clock=lambda: datetime(2026, 1, 1),
        run_id_factory=lambda: "backtest-naive-clock",
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        await service.run(
            ServiceRequest(
                payload=BacktestRunRequest(
                    scenario=_golden_scenario(expected_outcomes=()),
                )
            )
        )


def _golden_scenario(
    *,
    expected_outcomes: tuple[BacktestExpectedOutcome, ...] | None = None,
) -> BacktestScenario:
    return BacktestScenario(
        scenario_id="full-chain-golden",
        name="Full decision chain golden scenario",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("1000"),
        parameters={"days": 120},
        expected_outcomes=expected_outcomes
        if expected_outcomes is not None
        else (
            BacktestExpectedOutcome(
                target="technical.snapshot.rsi_14",
                expectation_type="equals",
                expected="62.5",
            ),
            BacktestExpectedOutcome(
                target="breadth.breadth_percent",
                expectation_type="approx",
                expected="0.20",
                tolerance=Decimal("0.000001"),
            ),
            BacktestExpectedOutcome(
                target="technical.regime.directional_technical_score",
                expectation_type="min",
                expected="0.60",
            ),
            BacktestExpectedOutcome(
                target="portfolio.equity",
                expectation_type="equals",
                expected="1000",
            ),
            BacktestExpectedOutcome(
                target="portfolio_state.total_equity",
                expectation_type="equals",
                expected="1000",
            ),
            BacktestExpectedOutcome(
                target="risk.composite_risk",
                expectation_type="between",
                expected=("0.24", "0.26"),
            ),
            BacktestExpectedOutcome(
                target="strategy.directional_score",
                expectation_type="equals",
                expected="0.45",
            ),
            BacktestExpectedOutcome(
                target="strategy.strategy_synthesis_decision.selected_perspective",
                expectation_type="equals",
                expected="bull",
            ),
            BacktestExpectedOutcome(
                target="strategy.strategy_synthesis_decision.selection_status",
                expectation_type="equals",
                expected="selected",
            ),
            BacktestExpectedOutcome(
                target="strategy.strategy_synthesis_decision.evaluations.0.perspective",
                expectation_type="equals",
                expected="bull",
            ),
            BacktestExpectedOutcome(
                target="strategy.strategy_synthesis_decision.evaluations.0.posterior_weight",
                expectation_type="equals",
                expected="0.62",
            ),
            BacktestExpectedOutcome(
                target="strategy.hypothesis_candidate_scores.bear",
                expectation_type="equals",
                expected="0.22",
            ),
            BacktestExpectedOutcome(
                target="strategy.hypothesis_posterior_weights.bull",
                expectation_type="equals",
                expected="0.62",
            ),
            BacktestExpectedOutcome(
                target="strategy.selected_hypothesis.perspective",
                expectation_type="equals",
                expected="bull",
            ),
            BacktestExpectedOutcome(
                target="strategy.selected_hypothesis.supporting_evidence.0.supports",
                expectation_type="contains",
                expected="bull",
            ),
            BacktestExpectedOutcome(
                target="strategy.selected_hypothesis.contradicting_evidence.0.contradicts",
                expectation_type="contains",
                expected="bull",
            ),
            BacktestExpectedOutcome(
                target="strategy.selected_hypothesis.key_assumptions.0.description",
                expectation_type="contains",
                expected="bull",
            ),
            BacktestExpectedOutcome(
                target="strategy.selected_hypothesis.invalidation_conditions.0.invalidated",
                expectation_type="equals",
                expected=False,
            ),
            BacktestExpectedOutcome(
                target="strategy.selected_hypothesis.invalidation_conditions.0.threshold",
                expectation_type="equals",
                expected="0.35",
            ),
            BacktestExpectedOutcome(
                target="trade.position_sizing_hint",
                expectation_type="equals",
                expected="0.20",
            ),
            BacktestExpectedOutcome(
                target="execution_risk.adjusted_position_size",
                expectation_type="max",
                expected="0.20",
            ),
        ),
    )


def _strategy_case_expected_outcomes(
    *,
    expected_selected: str | None,
    expected_status: str,
    expected_score: str,
    reason: str | None,
    expect_invalidated_bull: bool,
) -> tuple[BacktestExpectedOutcome, ...]:
    outcomes = [
        BacktestExpectedOutcome(
            target="strategy.strategy_synthesis_decision.selection_status",
            expectation_type="equals",
            expected=expected_status,
        ),
        BacktestExpectedOutcome(
            target="strategy.strategy_synthesis_decision.directional_score",
            expectation_type="equals",
            expected=expected_score,
        ),
        BacktestExpectedOutcome(
            target="strategy.directional_score",
            expectation_type="equals",
            expected=expected_score,
        ),
        BacktestExpectedOutcome(
            target="strategy.selected_perspective",
            expectation_type="equals",
            expected=expected_selected,
        ),
        BacktestExpectedOutcome(
            target="strategy.hypothesis_posterior_weights.bull",
            expectation_type="equals",
            expected="0.62" if expected_selected == "bull" else "0.20",
        ),
    ]

    if expected_selected is None:
        outcomes.extend(
            (
                BacktestExpectedOutcome(
                    target="strategy.selected_hypothesis",
                    expectation_type="equals",
                    expected=None,
                ),
                BacktestExpectedOutcome(
                    target="strategy.strategy_synthesis_decision.degraded_reasons",
                    expectation_type="contains",
                    expected=reason,
                ),
            )
        )
    else:
        outcomes.extend(
            (
                BacktestExpectedOutcome(
                    target="strategy.selected_hypothesis.perspective",
                    expectation_type="equals",
                    expected=expected_selected,
                ),
                BacktestExpectedOutcome(
                    target="strategy.selected_hypothesis.supporting_evidence.0.supports",
                    expectation_type="contains",
                    expected=expected_selected,
                ),
                BacktestExpectedOutcome(
                    target="strategy.selected_hypothesis.key_assumptions.0.description",
                    expectation_type="contains",
                    expected=expected_selected,
                ),
                BacktestExpectedOutcome(
                    target="strategy.selected_hypothesis.invalidation_conditions.0.invalidated",
                    expectation_type="equals",
                    expected=False,
                ),
            )
        )

    if expect_invalidated_bull:
        outcomes.append(
            BacktestExpectedOutcome(
                target="strategy.strategy_synthesis_decision.evaluations.0.invalidated",
                expectation_type="equals",
                expected=True,
            )
        )

    return tuple(outcomes)


def _golden_node_outputs(
    *, strategy_output: dict[str, Any] | None = None
) -> dict[str, dict[str, Any]]:
    return {
        "technical_agent": {
            "outputs": {
                "features": {
                    "symbol": "SPY",
                    "snapshot": {"close": "100", "rsi_14": "62.5"},
                    "breadth_state": {"breadth_percent": "0.20"},
                    "regime": {"directional_technical_score": "0.60"},
                }
            }
        },
        "portfolio_state_builder": {
            "outputs": {
                "features": {
                    "total_equity": "1000",
                    "cash": "1000",
                    "gross_exposure": "0",
                }
            }
        },
        "risk_aggregator_agent": {
            "outputs": {
                "features": {
                    "composite_risk": Decimal("0.25"),
                    "risk_pressure": Decimal("0.20"),
                }
            }
        },
        "strategy_synthesis_agent": strategy_output
        or _strategy_output_for_case("bullish"),
        "trade_packager": {
            "outputs": {
                "features": {
                    "trade_intent": {
                        "symbol": "SPY",
                        "direction": "long",
                        "position_sizing_hint": Decimal("0.20"),
                    }
                }
            }
        },
        "execution_risk_guard": {
            "outputs": {
                "features": {
                    "execution_guard": {
                        "mode": "normal",
                        "adjusted_position_size": Decimal("0.20"),
                    }
                }
            }
        },
    }


def _strategy_output_for_case(case_name: str) -> dict[str, Any]:
    case_config = _strategy_case_config(case_name)
    selected_perspective = case_config["selected_perspective"]
    status = str(case_config["selection_status"])
    degraded_reasons = tuple(case_config["degraded_reasons"])
    candidate_scores = dict(case_config["candidate_scores"])
    posterior_weights = dict(case_config["posterior_weights"])
    invalidated_perspectives = tuple(case_config["invalidated_perspectives"])
    evaluations = _strategy_evaluations(
        selected_perspective=selected_perspective,
        status=status,
        candidate_scores=candidate_scores,
        posterior_weights=posterior_weights,
        invalidated_perspectives=invalidated_perspectives,
    )
    selected_hypothesis = (
        None
        if selected_perspective is None
        else _strategy_hypothesis(str(selected_perspective))
    )
    decision = {
        "selected_perspective": selected_perspective,
        "selection_status": status,
        "directional_score": case_config["directional_score"],
        "confidence": case_config["confidence"],
        "regime": case_config["regime"],
        "uncertainty": case_config["uncertainty"],
        "evaluations": evaluations,
        "degraded_reasons": list(degraded_reasons),
        "thesis": case_config["thesis"],
        "signals": [f"{case_name} deterministic signal"],
        "risks": [f"{case_name} deterministic risk"],
        "recommendations": [f"{case_name} deterministic recommendation"],
    }
    return {
        "outputs": {
            "directional_score": case_config["directional_score"],
            "confidence": case_config["confidence"],
            "regime": case_config["regime"],
            "features": {
                "strategy_synthesis_decision": decision,
                "strategy_hypothesis_evaluations": evaluations,
                "hypothesis_candidate_scores": candidate_scores,
                "hypothesis_posterior_weights": posterior_weights,
                "selected_hypothesis": selected_hypothesis,
                "selected_perspective": selected_perspective,
                "selection_status": status,
                "degraded_reasons": list(degraded_reasons),
                "thesis": case_config["thesis"],
            },
        }
    }


def _strategy_case_config(case_name: str) -> dict[str, Any]:
    configs: dict[str, dict[str, Any]] = {
        "bullish": {
            "selected_perspective": "bull",
            "selection_status": "selected",
            "directional_score": "0.45",
            "confidence": "0.80",
            "regime": "bullish",
            "uncertainty": "0.20",
            "candidate_scores": {"bull": "0.74", "bear": "0.22", "sideways": "0.32"},
            "posterior_weights": {"bull": "0.62", "bear": "0.18", "sideways": "0.20"},
            "degraded_reasons": (),
            "invalidated_perspectives": (),
            "thesis": "Bullish hypothesis selected from deterministic trend evidence.",
        },
        "bearish": {
            "selected_perspective": "bear",
            "selection_status": "selected",
            "directional_score": "-0.45",
            "confidence": "0.78",
            "regime": "bearish",
            "uncertainty": "0.22",
            "candidate_scores": {"bull": "0.20", "bear": "0.72", "sideways": "0.30"},
            "posterior_weights": {"bull": "0.20", "bear": "0.60", "sideways": "0.20"},
            "degraded_reasons": (),
            "invalidated_perspectives": (),
            "thesis": "Bearish hypothesis selected from deterministic downside evidence.",
        },
        "sideways": {
            "selected_perspective": "sideways",
            "selection_status": "selected",
            "directional_score": "0.00",
            "confidence": "0.70",
            "regime": "sideways",
            "uncertainty": "0.30",
            "candidate_scores": {"bull": "0.28", "bear": "0.25", "sideways": "0.69"},
            "posterior_weights": {"bull": "0.20", "bear": "0.20", "sideways": "0.60"},
            "degraded_reasons": (),
            "invalidated_perspectives": (),
            "thesis": "Sideways hypothesis selected from deterministic range evidence.",
        },
        "conflict": {
            "selected_perspective": None,
            "selection_status": "degraded",
            "directional_score": "0.00",
            "confidence": "0.40",
            "regime": "conflicted",
            "uncertainty": "0.60",
            "candidate_scores": {"bull": "0.50", "bear": "0.50", "sideways": "0.20"},
            "posterior_weights": {"bull": "0.20", "bear": "0.20", "sideways": "0.20"},
            "degraded_reasons": ("tied_candidates",),
            "invalidated_perspectives": (),
            "thesis": "No strategy selected because deterministic evidence is tied.",
        },
        "missing_data": {
            "selected_perspective": None,
            "selection_status": "degraded",
            "directional_score": "0.00",
            "confidence": "0.35",
            "regime": "insufficient_data",
            "uncertainty": "0.65",
            "candidate_scores": {"bull": "0.00", "bear": "0.00", "sideways": "0.00"},
            "posterior_weights": {"bull": "0.20", "bear": "0.20", "sideways": "0.20"},
            "degraded_reasons": ("missing_hypothesis",),
            "invalidated_perspectives": (),
            "thesis": "No strategy selected because deterministic evidence is missing.",
        },
        "invalidation": {
            "selected_perspective": "bear",
            "selection_status": "selected",
            "directional_score": "-0.40",
            "confidence": "0.76",
            "regime": "bearish",
            "uncertainty": "0.24",
            "candidate_scores": {"bull": "0.80", "bear": "0.66", "sideways": "0.30"},
            "posterior_weights": {"bull": "0.20", "bear": "0.58", "sideways": "0.22"},
            "degraded_reasons": (),
            "invalidated_perspectives": ("bull",),
            "thesis": "Bearish hypothesis selected after bullish hypothesis invalidation.",
        },
    }
    return configs[case_name]


def _strategy_evaluations(
    *,
    selected_perspective: object,
    status: str,
    candidate_scores: Mapping[str, object],
    posterior_weights: Mapping[str, object],
    invalidated_perspectives: tuple[object, ...],
) -> list[dict[str, Any]]:
    evaluations: list[dict[str, Any]] = []
    for rank, perspective in enumerate(("bull", "bear", "sideways"), start=1):
        invalidated = perspective in invalidated_perspectives
        selected = perspective == selected_perspective
        evaluation_status = "selected" if selected else "rejected"
        if invalidated:
            evaluation_status = "invalidated"
        elif status == "degraded":
            evaluation_status = "degraded"
        evaluations.append(
            {
                "perspective": perspective,
                "rank": rank,
                "candidate_score": candidate_scores[perspective],
                "posterior_weight": posterior_weights[perspective],
                "perspective_weight": posterior_weights[perspective],
                "likelihood_score": candidate_scores[perspective],
                "evidence_score": candidate_scores[perspective],
                "risk_adjustment": "0.05",
                "confidence": "0.80" if selected else "0.50",
                "hypothesis_strength": candidate_scores[perspective],
                "selection_status": evaluation_status,
                "invalidated": invalidated,
                "rationale": f"{perspective} deterministic evaluation",
            }
        )
    return evaluations


def _strategy_hypothesis(perspective: str) -> dict[str, Any]:
    return {
        "perspective": perspective,
        "thesis": f"Deterministic {perspective} hypothesis thesis.",
        "directional_bias": "0.45" if perspective == "bull" else "-0.45",
        "hypothesis_strength": "0.80",
        "confidence": "0.80",
        "supporting_evidence": [
            {
                "evidence_id": f"ev-{perspective}-trend",
                "source": "deterministic_fixture",
                "name": f"{perspective} trend evidence",
                "observed_value": "0.72",
                "strength": "0.80",
                "reliability": "0.90",
                "supports": [perspective],
                "contradicts": [],
                "explanation": f"Supports the deterministic {perspective} hypothesis.",
            }
        ],
        "contradicting_evidence": [
            {
                "evidence_id": f"ev-{perspective}-risk",
                "source": "deterministic_fixture",
                "name": f"{perspective} risk evidence",
                "observed_value": "0.25",
                "strength": "0.25",
                "reliability": "0.70",
                "supports": [],
                "contradicts": [perspective],
                "explanation": f"Partially contradicts the deterministic {perspective} hypothesis.",
            }
        ],
        "key_assumptions": [
            {
                "assumption_id": f"assumption-{perspective}-trend",
                "perspective": perspective,
                "description": f"The deterministic {perspective} evidence remains valid.",
                "confidence": "0.75",
                "evidence_ids": [f"ev-{perspective}-trend"],
            }
        ],
        "invalidation_conditions": [
            {
                "condition_id": f"invalidate-{perspective}-trend",
                "perspective": perspective,
                "description": f"Invalidate {perspective} if evidence strength falls below threshold.",
                "observed_value": "0.72",
                "operator": "lt",
                "threshold": "0.35",
                "evidence_id": f"ev-{perspective}-trend",
                "invalidated": False,
            }
        ],
        "risks": [f"{perspective} deterministic risk"],
        "recommendations": [f"{perspective} deterministic recommendation"],
        "data_quality_flags": [],
        "evidence_fingerprint": f"{perspective}-fixture-fingerprint",
        "invalidated": False,
    }


def _canonical_strategy_decision(result: Any) -> str:
    strategy_output = result.steps[0].node_outputs["strategy_synthesis_agent"]
    outputs = strategy_output["outputs"]
    features = outputs["features"]
    return dumps(
        features["strategy_synthesis_decision"],
        sort_keys=True,
        separators=(",", ":"),
    )
