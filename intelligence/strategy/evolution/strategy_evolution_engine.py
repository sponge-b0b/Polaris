from collections import defaultdict
from typing import Any

from core.runtime.execution.execution_graph import ExecutionGraph


class StrategyEvolutionEngine:
    """
    Graph-aware Strategy Evolution Engine.

    Upgraded role:
    - causal strategy tracking (not just time series)
    - risk-aware evolution
    - graph-driven attribution ingestion
    """

    def __init__(self) -> None:

        self.history: dict[str, list[dict[str, Any]]] = defaultdict(list)

    # ============================================================
    # INGEST RUN (GRAPH-BASED)
    # ============================================================

    def ingest_run(
        self,
        graph: ExecutionGraph,
        attribution: dict[str, Any],
        outcome: dict[str, Any] | None = None,
    ) -> None:

        strategy_map = attribution.get(
            "strategy_attribution",
            {},
        )

        risk_map = attribution.get(
            "risk_attribution",
            {},
        )

        node_influence = attribution.get(
            "node_influence",
            {},
        )

        for strategy, weight in strategy_map.items():
            # ====================================================
            # STRATEGY-SPECIFIC RISK EXPOSURE
            # ====================================================

            risk_exposure = self._compute_strategy_risk_exposure(
                strategy,
                risk_map,
                node_influence,
            )

            self.history[strategy].append(
                {
                    "run_id": graph.run_id,
                    "workflow": graph.workflow_name,
                    # core signals
                    "strategy_weight": weight,
                    "risk_exposure": risk_exposure,
                    # outcome linkage
                    "outcome": outcome or {},
                    # structural metadata
                    "node_count": len(graph.nodes),
                    "edge_count": len(graph.edges),
                }
            )

    # ============================================================
    # STRATEGY PERFORMANCE
    # ============================================================

    def compute_performance(
        self,
        strategy: str,
    ) -> dict[str, Any]:

        records = self.history.get(strategy, [])

        if not records:
            return {
                "strategy": strategy,
                "status": "no_data",
            }

        total = len(records)

        avg_weight = sum(r["strategy_weight"] for r in records) / total

        avg_risk = sum(r["risk_exposure"] for r in records) / total

        return {
            "strategy": strategy,
            "total_runs": total,
            "avg_strategy_weight": avg_weight,
            "avg_risk_exposure": avg_risk,
        }

    # ============================================================
    # DRIFT DETECTION (ENHANCED)
    # ============================================================

    def detect_drift(
        self,
        strategy: str,
        window: int = 10,
    ) -> dict[str, Any]:

        records = self.history.get(strategy, [])

        if len(records) < window:
            return {
                "strategy": strategy,
                "drift": False,
                "reason": "insufficient_data",
            }

        recent = records[-window:]
        baseline = records[:-window] or recent

        recent_avg = sum(r["strategy_weight"] for r in recent) / len(recent)

        baseline_avg = sum(r["strategy_weight"] for r in baseline) / len(baseline)

        recent_risk = sum(r["risk_exposure"] for r in recent) / len(recent)

        baseline_risk = sum(r["risk_exposure"] for r in baseline) / len(baseline)

        drift_score = abs(recent_avg - baseline_avg)
        risk_shift = abs(recent_risk - baseline_risk)

        return {
            "strategy": strategy,
            "drift": drift_score > 0.15,
            "drift_score": drift_score,
            "risk_shift": risk_shift,
        }

    # ============================================================
    # SYSTEM SNAPSHOT
    # ============================================================

    def system_snapshot(self) -> dict[str, Any]:

        return {
            strategy: self.compute_performance(strategy)
            for strategy in self.history.keys()
        }

    # ============================================================
    # INTERNAL: RISK EXPOSURE FROM GRAPH ATTRIBUTION
    # ============================================================

    def _compute_strategy_risk_exposure(
        self,
        strategy: str,
        risk_map: dict[str, Any],
        node_influence: dict[str, Any],
    ) -> float:

        exposure = 0.0

        for node, risk_value in risk_map.items():
            if strategy in node:
                exposure += abs(risk_value)

        return exposure
