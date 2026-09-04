# Strategy Synthesis MarketEventsService Correctness Plan

## Summary / Issues Found

Current StrategySynthesisAgent is not correct as-is. The main bugs are:

- MarketEventsRequest cannot be imported because symbol_constituents uses a mutable set default in a frozen dataclass.
- StrategySynthesisAgent calls MarketEventsService with operation "events.analysis.execute", but the service only accepts "market_events.state".
- StrategySynthesisAgent reads market_events_result.data.analysis, but MarketEventsResult exposes state, not analysis.
- Dynamic top_50_constituents should be sanitized before passing to the service because it comes from serialized runtime node output.
- Event service failure currently raises and can break strategy synthesis; the existing _neutral_market_events() helper suggests the intended behavior is graceful neutral fallback.
- The workflow definition should explicitly declare the node outputs that synthesis directly reads.

## Implementation Changes

1. Fix the MarketEvents request contract.
    - Update MarketEventsRequest.symbol_constituents to use an immutable/default-safe contract, preferably:
        - frozenset[str]
        - field(default_factory=...)

    - Keep MarketEventsService.run() converting request constituents to set[str] before provider calls.
    - Preserve the canonical operation: "market_events.state".

2. Fix StrategySynthesisAgent service invocation.
    - Replace operation "events.analysis.execute" with "market_events.state".
    - Replace market_events_result.data.analysis with market_events_result.data.state or market_events_result.data.to_dict().
    - Add a small private helper to extract/sanitize constituents from:
        - technical_agent.outputs.features.market_context.top_50_constituents

    - Sanitization rules:
        - accept list/tuple/set/frozenset of strings
        - strip whitespace
        - uppercase symbols
        - drop empty/non-string values
        - fallback to TOP_EARNINGS_SYMBOLS if empty/missing

3. Make market events non-fatal for strategy synthesis.
    - Wrap service execution/result handling in a private helper such as _get_market_events(...).
    - On service validation failure, provider exception, missing result data, or invalid result shape, use _neutral_market_events(symbol=..., error=...).
    - Preserve the error in features["market_events"]["event_error"].
    - Add a risk/signal such as market_event_context_unavailable only when neutral fallback was used.

4. Correct event lookahead semantics.
    - Do not reuse historical technical-analysis days as event lookahead.
    - Use context.state.shared_state.get("event_lookahead_days", 10) for MarketEventsRequest.lookahead_days.
    - Keep horizon from shared state with default "3month".

5. Update workflow and downstream wiring.
    - Update workflows/definitions/reports/morning_report.py so strategy_synthesis_agent explicitly depends on the node outputs it directly reads:
        - adaptive_weighting_engine
        - risk_aggregator_agent
        - portfolio_state_builder
        - technical_agent
        - retain existing strategy-node dependencies if those remain part of synthesis ordering

    - Confirm intelligence/strategy/di.py still injects:
        - MarketEventsService
        - ServiceRunner
        - IntelligenceTelemetry

## Downstream Files Likely Requiring Updates

- application/services/market_events/market_events_request.py
    - Required to fix import/runtime failure from mutable dataclass default.

- intelligence/strategy/synthesis/strategy_synthesis_agent.py
    - Required to fix operation name, result access, dynamic constituent sanitization, and neutral fallback.

- workflows/definitions/reports/morning_report.py
- tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py
    - Required because synthesis now depends on market events service behavior and dynamic constituents.

- tests/unit/application/services/test_canonical_service_entrypoints.py
    - Required to lock the canonical MarketEventsRequest and MarketEventsService contract.

- tests/integration/workflow/test_morning_report_real_nodes.py
    - Required to verify the real workflow still runs and synthesis receives market event + breadth context.

- Optional cleanup if touched by validation:
    - market events provider protocol/implementations may be updated from mutable default set parameters to None defaults with internal fallback, but only if scoped validation or typing requires it.

## Test Plan

- Add/adjust unit tests for MarketEventsRequest.
    - Import succeeds.
    - Default constituents are immutable/default-safe.
    - Custom dynamic constituents are accepted.

- Add/adjust StrategySynthesisAgent unit tests.
    - Uses operation "market_events.state".
    - Reads MarketEventsResult.state.
    - Passes sanitized top-50 constituents from technical market_context.
    - Falls back to TOP_EARNINGS_SYMBOLS when constituents are missing.
    - Uses neutral market events when the service fails, without failing synthesis.

- Update existing breadth synthesis tests.
    - Ensure breadth behavior remains unchanged when market events are neutral.
    - Fix fixture node key if needed so it provides portfolio_state_builder, not portfolio_manager_agent.

- Update integration coverage.
    - Run morning report real-node workflow.
    - Assert strategy_synthesis_agent.outputs.features.market_events exists.
    - Assert synthesis still propagates breadth context.
    - If feasible, assert event fallback is absent in the normal simulated-provider path.

- Validation commands:
    - UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/integration/workflow/
    test_morning_report_real_nodes.py

    - UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/services/market_events/market_events_request.py intelligence/strategy/synthesis/strategy_synthesis_agent.py intelligence/strategy/di.py workflows/definitions/
    reports/morning_report.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/integration/workflow/
    test_morning_report_real_nodes.py

    - UV_CACHE_DIR=/tmp/uv-cache uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip ...same scoped files...
    - UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .

## Assumptions

- Strategy synthesis should not fail the morning report solely because market event data is unavailable.
- MarketEventsService remains the canonical application-service boundary; no direct provider calls from the agent.
- Dynamic constituents should be treated as untrusted serialized runtime data and normalized before entering the typed request.
- event_lookahead_days should be separate from historical technical-analysis days.

## Results

Changes made:

- application/services/market_events/market_events_request.py
    - Replaced the mutable dataclass set default with an immutable frozenset default factory.
    - Added DEFAULT_SYMBOL_CONSTITUENTS.

- intelligence/strategy/synthesis/strategy_synthesis_agent.py
    - Fixed MarketEventsService operation from the invalid events.analysis.execute to canonical market_events.state.
    - Fixed result handling to use MarketEventsResult.to_dict() instead of nonexistent .analysis.
    - Added sanitized extraction of top_50_constituents from technical_agent.outputs.features.market_context.
    - Added neutral market-events fallback behavior when the events service fails or returns no data.
    - Added event-context fallback signals/risks:
        - market_event_context_unavailable

    - Switched event lookahead to event_lookahead_days with default 10, instead of reusing broad historical days.
    - Added output features:
        - market_event_constituents
        - event_lookahead_days

- workflows/definitions/reports/morning_report.py
    - Made direct strategy_synthesis_agent dependencies explicit:
        - adaptive_weighting_engine
        - bull_agent
        - bear_agent
        - sideways_agent
        - risk_aggregator_agent
        - portfolio_state_builder
        - technical_agent

- Tests updated:
    - tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py
        - Fixed expected node output from portfolio_manager_agent to portfolio_state_builder.
        - Added coverage for dynamic market-context constituents.
        - Added coverage for neutral market-events fallback on service failure.

    - tests/unit/application/services/test_canonical_service_entrypoints.py
        - Added assertions for immutable MarketEventsRequest.symbol_constituents.
        - Added provider assertion that requested symbols reach the events provider.

    - tests/integration/workflow/test_morning_report_real_nodes.py
        - Added assertions that technical breadth top_50_constituents reaches strategy synthesis.
        - Added assertions for strategy synthesis market-event output.

Validation passed:

13 passed, 1 warning

Commands run successfully:

uv run python -m py_compile ...
uv run pytest -q tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/integration/workflow/test_morning_report_real_nodes.py
uv run ruff check ...
uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip ...
uv run graphify update .

Also ran a final grep check confirming the invalid operation/result access is gone:

events.analysis.execute
market_events_result.data.analysis
symbol_constituents mutable default

No matches.
