from __future__ import annotations

from dataclasses import replace
from time import perf_counter
from typing import Protocol
from typing import cast

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph

from application.rag.generation import RagAnswerGenerator
from application.rag.graphs.rag_graph_models import EmptyRagConversationMemoryProvider
from application.rag.graphs.rag_graph_models import PresenceRagContextEvaluator
from application.rag.graphs.rag_graph_models import RagAnswerReflector
from application.rag.graphs.rag_graph_models import RagContextEvaluator
from application.rag.graphs.rag_graph_models import RagConversationMemoryProvider
from application.rag.graphs.rag_graph_models import RagWebFallbackRetriever
from application.rag.graphs.rag_graph_policy import RagGraphPolicy
from application.rag.contracts.rag_quality_models import RagCorrectiveAction
from application.rag.graphs.rag_graph_models import RagCorrectiveQueryRewriter
from application.rag.graphs.rag_graph_state import RagGraphState
from application.rag.graphs.rag_graph_state import initial_rag_graph_state
from application.rag.routing.query_routing_models import RagAdaptiveTriage
from application.rag.routing.query_routing_models import RagHydeExpansion
from application.rag.routing.query_routing_models import RagQueryContext
from application.rag.routing.query_routing_models import RagQueryModelExecution
from application.rag.routing.query_routing_models import RagRetrievalRoute
from application.rag.routing.query_routing_models import RagRouteSelection
from application.rag.routing.query_routing_models import RagStandaloneQueryRewrite
from application.rag.routing.query_routing_service import RagQueryRoutingService
from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_request import RagRequest
from application.rag.security.rag_security import RagSecurityGuard
from application.rag.security.rag_security import safe_grounding_failure_answer
from application.rag.contracts.rag_result import RagResult
from application.rag.observability import RagAiObservabilityProjectorPort
from application.rag.observability import RagAiObservabilityRecorder
from application.rag.observability import record_answer_quality_observation
from application.rag.observability import record_crag_observation
from application.rag.observability import record_generation_observation
from application.rag.observability import record_hyde_observation
from application.rag.observability import record_routing_observation
from application.rag.observability import record_security_observation
from application.rag.observability import record_self_rag_observation
from application.rag.retrieval.rag_retriever import RagRetrievalResult
from application.rag.retrieval.rag_retriever import RagRetriever


class RagQueryRoutingPort(Protocol):
    async def rewrite(
        self,
        context: RagQueryContext,
    ) -> tuple[RagStandaloneQueryRewrite, RagQueryModelExecution | None]: ...

    async def triage(
        self,
        *,
        context: RagQueryContext,
        query: str,
    ) -> tuple[RagAdaptiveTriage, RagQueryModelExecution]: ...

    async def select_route(
        self,
        *,
        context: RagQueryContext,
        query: str,
        triage: RagAdaptiveTriage,
    ) -> tuple[RagRouteSelection, RagQueryModelExecution]: ...

    async def generate_hyde(
        self,
        *,
        context: RagQueryContext,
        query: str,
    ) -> tuple[RagHydeExpansion, RagQueryModelExecution]: ...


class RagRetrieverPort(Protocol):
    async def retrieve(self, request: RagRequest) -> RagRetrievalResult: ...


class RagAnswerGeneratorPort(Protocol):
    async def generate(
        self,
        *,
        request: RagRequest,
        contexts: tuple[RagRetrievedContext, ...],
    ) -> RagResult: ...


class RagStateGraphProtocol(Protocol):
    async def ainvoke(self, input: RagGraphState) -> RagGraphState: ...


class RagServiceGraph:
    """Unified internal LangGraph orchestration for the platform RAG pipeline."""

    def __init__(
        self,
        *,
        query_routing_service: RagQueryRoutingService | RagQueryRoutingPort,
        retriever: RagRetriever | RagRetrieverPort,
        answer_generator: RagAnswerGenerator | RagAnswerGeneratorPort,
        memory_provider: RagConversationMemoryProvider | None = None,
        context_evaluator: RagContextEvaluator | None = None,
        corrective_query_rewriter: RagCorrectiveQueryRewriter | None = None,
        answer_reflector: RagAnswerReflector | None = None,
        web_fallback_retriever: RagWebFallbackRetriever | None = None,
        security_guard: RagSecurityGuard | None = None,
        max_loops: int = 1,
        ai_observability_projector: RagAiObservabilityProjectorPort | None = None,
    ) -> None:
        if max_loops <= 0:
            raise ValueError("max_loops must be positive.")
        self._query_routing_service = query_routing_service
        self._retriever = retriever
        self._answer_generator = answer_generator
        self._memory_provider = memory_provider or EmptyRagConversationMemoryProvider()
        self._context_evaluator = context_evaluator or PresenceRagContextEvaluator()
        self._corrective_query_rewriter = corrective_query_rewriter
        self._answer_reflector = answer_reflector
        self._web_fallback_retriever = web_fallback_retriever
        self._security_guard = security_guard or RagSecurityGuard()
        self._policy = RagGraphPolicy()
        self._max_loops = max_loops
        self._ai_observability = RagAiObservabilityRecorder(ai_observability_projector)
        self._compiled_graph: RagStateGraphProtocol | None = None

    async def run(self, request: RagRequest) -> RagResult:
        input_inspection = await self._security_guard.inspect_input(request)
        await record_security_observation(
            self._ai_observability,
            request=request,
            stage_name="input_security_guard",
            detected=input_inspection.detected,
            signal_count=len(input_inspection.signals),
        )
        if input_inspection.detected:
            result = replace(
                RagResult.no_results(
                    request=request,
                    answer_text=(
                        "The request was blocked because it contained instruction-"
                        "override content."
                    ),
                ),
                injection_detected=True,
                corrective_actions=(RagCorrectiveAction.FAIL_CLOSED,),
                metadata={
                    "security_stage": "input_guard",
                    "security_signals": list(input_inspection.signals),
                },
            )
            await record_answer_quality_observation(
                self._ai_observability,
                request=request,
                result=result,
            )
            return result
        try:
            final_state = await self.graph.ainvoke(
                initial_rag_graph_state(request, max_loops=self._max_loops)
            )
        except Exception as exc:
            result = RagResult.failed(request=request, error=str(exc))
            await record_answer_quality_observation(
                self._ai_observability,
                request=request,
                result=result,
            )
            return result
        result = final_state.get("result")
        if result is None:
            result = RagResult.failed(
                request=request,
                error="RAG graph completed without a result.",
            )
        await record_answer_quality_observation(
            self._ai_observability,
            request=request,
            result=result,
        )
        return result

    @property
    def graph(self) -> RagStateGraphProtocol:
        if self._compiled_graph is None:
            self._compiled_graph = self._compile_graph()
        return self._compiled_graph

    def _compile_graph(self) -> RagStateGraphProtocol:
        graph = StateGraph(RagGraphState)
        graph.add_node("memory_context", self._memory_context)
        graph.add_node("adaptive_classifier", self._adaptive_classifier)
        graph.add_node("route_selection", self._route_selection)
        graph.add_node("hyde", self._hyde)
        graph.add_node("branched_retrieval", self._branched_retrieval)
        graph.add_node("context_fusion_reranking", self._context_fusion_reranking)
        graph.add_node("crag_evaluator", self._crag_evaluator)
        graph.add_node("query_rewrite", self._query_rewrite)
        graph.add_node("grounding_failure", self._grounding_failure)
        graph.add_node("web_fallback", self._web_fallback)
        graph.add_node("secure_generation", self._secure_generation)
        graph.add_node("self_rag_reflection", self._self_rag_reflection)
        graph.add_node("post_processing_safety", self._post_processing_safety)

        graph.add_edge(START, "memory_context")
        graph.add_edge("memory_context", "adaptive_classifier")
        graph.add_edge("adaptive_classifier", "route_selection")
        graph.add_conditional_edges(
            "route_selection",
            self._route_after_selection,
            {
                "direct": "secure_generation",
                "retrieval": "branched_retrieval",
                "deep_research": "hyde",
            },
        )
        graph.add_edge("hyde", "branched_retrieval")
        graph.add_edge("branched_retrieval", "context_fusion_reranking")
        graph.add_edge("context_fusion_reranking", "crag_evaluator")
        graph.add_conditional_edges(
            "crag_evaluator",
            self._route_after_crag,
            {
                "generate": "secure_generation",
                "rewrite": "query_rewrite",
                "web_fallback": "web_fallback",
                "fail_closed": "grounding_failure",
            },
        )
        graph.add_edge("query_rewrite", "branched_retrieval")
        graph.add_conditional_edges(
            "web_fallback",
            self._route_after_web_fallback,
            {
                "generate": "secure_generation",
                "fail_closed": "grounding_failure",
            },
        )
        graph.add_edge("grounding_failure", "post_processing_safety")
        graph.add_edge("secure_generation", "self_rag_reflection")
        graph.add_edge("self_rag_reflection", "post_processing_safety")
        graph.add_edge("post_processing_safety", END)
        return cast(RagStateGraphProtocol, graph.compile())

    async def _memory_context(self, state: RagGraphState) -> RagGraphState:
        request = _required_request(state)
        memory = await self._memory_provider.load(request)
        context = RagQueryContext(
            request_id=request.request_id,
            query=request.normalized_query,
            memory=memory,
        )
        rewrite, execution = await self._query_routing_service.rewrite(context)
        await record_routing_observation(
            self._ai_observability,
            request=request,
            stage_name="memory_context",
            execution=execution,
            output_shape=f"rewritten={rewrite.rewritten}",
        )
        executions = () if execution is None else (execution,)
        return RagGraphState(
            status="running",
            query_context=context,
            rewrite=rewrite,
            model_executions=executions,
            stage_history=_append_stage(state, "memory_context"),
        )

    async def _adaptive_classifier(self, state: RagGraphState) -> RagGraphState:
        context = _required_query_context(state)
        rewrite = state["rewrite"]
        triage, execution = await self._query_routing_service.triage(
            context=context,
            query=rewrite.standalone_query,
        )
        await record_routing_observation(
            self._ai_observability,
            request=_required_request(state),
            stage_name="adaptive_classifier",
            execution=execution,
            output_shape=f"complexity={triage.complexity.value}",
            metadata={"complexity": triage.complexity.value},
        )
        return RagGraphState(
            triage=triage,
            model_executions=(*state.get("model_executions", ()), execution),
            stage_history=_append_stage(state, "adaptive_classifier"),
        )

    async def _route_selection(self, state: RagGraphState) -> RagGraphState:
        context = _required_query_context(state)
        rewrite = state["rewrite"]
        triage = state["triage"]
        selection, execution = await self._query_routing_service.select_route(
            context=context,
            query=rewrite.standalone_query,
            triage=triage,
        )
        await record_routing_observation(
            self._ai_observability,
            request=_required_request(state),
            stage_name="route_selection",
            execution=execution,
            output_shape=f"route={selection.route.value}",
            metadata={"selected_route": selection.route.value},
        )
        active_request = _request_for_query(
            _required_request(state),
            query=rewrite.standalone_query,
            selection=selection.route.value,
            executions=(*state.get("model_executions", ()), execution),
        )
        return RagGraphState(
            route_selection=selection,
            active_request=active_request,
            model_executions=(*state.get("model_executions", ()), execution),
            stage_history=_append_stage(state, "route_selection"),
        )

    async def _hyde(self, state: RagGraphState) -> RagGraphState:
        context = _required_query_context(state)
        rewrite = state["rewrite"]
        hyde, execution = await self._query_routing_service.generate_hyde(
            context=context,
            query=rewrite.standalone_query,
        )
        await record_hyde_observation(
            self._ai_observability,
            request=_required_request(state),
            execution=execution,
            hypothetical_document_length=len(hyde.hypothetical_document),
        )
        executions = (*state.get("model_executions", ()), execution)
        active_request = _request_for_query(
            _required_request(state),
            query=f"{rewrite.standalone_query}\n\n{hyde.hypothetical_document}",
            selection=RagRetrievalRoute.DEEP_RESEARCH.value,
            executions=executions,
        )
        return RagGraphState(
            hyde=hyde,
            active_request=active_request,
            model_executions=executions,
            stage_history=_append_stage(state, "hyde"),
        )

    async def _branched_retrieval(self, state: RagGraphState) -> RagGraphState:
        result = await self._retriever.retrieve(_required_active_request(state))
        return RagGraphState(
            retrieval_result=result,
            stage_history=_append_stage(state, "branched_retrieval"),
        )

    async def _context_fusion_reranking(self, state: RagGraphState) -> RagGraphState:
        request = _required_active_request(state)
        sanitation = await self._security_guard.sanitize_contexts(
            request=request,
            contexts=state["retrieval_result"].contexts,
        )
        await record_security_observation(
            self._ai_observability,
            request=request,
            stage_name="context_security_guard",
            detected=bool(
                sanitation.injection_count
                or sanitation.executable_markup_count
                or sanitation.dropped_count
            ),
            signal_count=(
                sanitation.injection_count
                + sanitation.executable_markup_count
                + sanitation.dropped_count
            ),
        )
        return RagGraphState(
            fused_context=sanitation.contexts,
            reranked_context=sanitation.contexts,
            stage_history=_append_stage(state, "context_fusion_reranking"),
        )

    async def _crag_evaluator(self, state: RagGraphState) -> RagGraphState:
        contexts = state.get("reranked_context", ())
        evaluation = await self._context_evaluator.evaluate(
            request=_required_active_request(state),
            contexts=contexts,
            loop_count=state.get("loop_count", 0),
        )
        retained_context = contexts
        if evaluation.action is RagCorrectiveAction.DISCARD_WEAK_CONTEXT:
            retained_ids = set(evaluation.retained_context_ids)
            retained_context = tuple(
                context for context in contexts if context.context_id in retained_ids
            )
        await record_crag_observation(
            self._ai_observability,
            request=_required_active_request(state),
            evaluation=evaluation,
            input_context_count=len(contexts),
            retained_context_count=len(retained_context),
        )
        return RagGraphState(
            context_evaluation=evaluation,
            reranked_context=retained_context,
            corrective_actions=(
                *state.get("corrective_actions", ()),
                evaluation.action,
            ),
            stage_history=_append_stage(state, "crag_evaluator"),
        )

    async def _query_rewrite(self, state: RagGraphState) -> RagGraphState:
        rewriter = self._corrective_query_rewriter
        if rewriter is None:
            raise RuntimeError("CRAG requested a query rewrite without a rewriter.")
        loop_count = state.get("loop_count", 0) + 1
        current = _required_active_request(state)
        rewritten_query = await rewriter.rewrite(
            request=current,
            query=current.normalized_query,
            loop_count=loop_count,
        )
        await record_routing_observation(
            self._ai_observability,
            request=current,
            stage_name="query_rewrite",
            execution=None,
            output_shape=f"rewritten_query_characters={len(rewritten_query)}",
            metadata={"loop_count": loop_count},
        )
        return RagGraphState(
            active_request=replace(current, query=rewritten_query),
            loop_count=loop_count,
            stage_history=_append_stage(state, "query_rewrite"),
        )

    async def _grounding_failure(self, state: RagGraphState) -> RagGraphState:
        request = _required_active_request(state)
        await self._security_guard.emit_grounding_failure(
            request=request,
            reason="crag_fail_closed",
        )
        result = RagResult.no_results(
            request=request,
            answer_text=safe_grounding_failure_answer(),
        )
        return RagGraphState(
            result=result,
            draft_answer=None,
            stage_history=_append_stage(state, "grounding_failure"),
        )

    async def _web_fallback(self, state: RagGraphState) -> RagGraphState:
        retriever = self._web_fallback_retriever
        if retriever is None:
            return RagGraphState(
                reranked_context=(),
                stage_history=_append_stage(state, "web_fallback"),
            )
        request = _required_active_request(state)
        contexts = await retriever.retrieve(request)
        sanitation = await self._security_guard.sanitize_contexts(
            request=request,
            contexts=contexts,
        )
        return RagGraphState(
            fused_context=sanitation.contexts,
            reranked_context=sanitation.contexts,
            stage_history=_append_stage(state, "web_fallback"),
        )

    async def _secure_generation(self, state: RagGraphState) -> RagGraphState:
        request = _required_active_request(state)
        contexts = state.get("reranked_context", ())
        generation_started_at = perf_counter()
        result = await self._answer_generator.generate(
            request=request,
            contexts=contexts,
        )
        generation_duration_seconds = perf_counter() - generation_started_at
        corrective_actions = state.get("corrective_actions", ())
        if result.status == "answered":
            output_inspection = await self._security_guard.inspect_output(
                request=request,
                answer_text=result.answer_text,
            )
            if output_inspection.detected:
                result = replace(
                    result,
                    answer_text=safe_grounding_failure_answer(),
                    status="no_results",
                    confidence_score=None,
                    injection_detected=True,
                    error=None,
                    metadata={
                        **dict(result.metadata),
                        "security_stage": "output_guard",
                        "security_signals": list(output_inspection.signals),
                    },
                )
                corrective_actions = (
                    *corrective_actions,
                    RagCorrectiveAction.FAIL_CLOSED,
                )
            await record_security_observation(
                self._ai_observability,
                request=request,
                stage_name="output_security_guard",
                detected=output_inspection.detected,
                signal_count=len(output_inspection.signals),
            )
        await record_generation_observation(
            self._ai_observability,
            request=request,
            result=result,
            input_context_count=len(contexts),
            duration_seconds=generation_duration_seconds,
        )
        return RagGraphState(
            result=result,
            draft_answer=result.answer_text,
            corrective_actions=corrective_actions,
            stage_history=_append_stage(state, "secure_generation"),
        )

    async def _self_rag_reflection(self, state: RagGraphState) -> RagGraphState:
        result = state["result"]
        reflector = self._answer_reflector
        if reflector is None or result.status != "answered":
            await record_self_rag_observation(
                self._ai_observability,
                request=_required_active_request(state),
                reflection=None,
                skipped=True,
            )
            return RagGraphState(
                stage_history=_append_stage(state, "self_rag_reflection"),
            )
        reflection = await reflector.reflect(
            request=_required_active_request(state),
            contexts=state.get("reranked_context", ()),
            answer_text=result.answer_text,
        )
        corrective_actions = state.get("corrective_actions", ())
        if not reflection.answer_supported or reflection.injection_detected:
            corrective_actions = (
                *corrective_actions,
                RagCorrectiveAction.FAIL_CLOSED,
            )
        await record_self_rag_observation(
            self._ai_observability,
            request=_required_active_request(state),
            reflection=reflection,
            skipped=False,
        )
        return RagGraphState(
            self_reflection=reflection,
            corrective_actions=corrective_actions,
            stage_history=_append_stage(state, "self_rag_reflection"),
        )

    async def _post_processing_safety(self, state: RagGraphState) -> RagGraphState:
        decision = self._policy.finalize_result(
            result=state["result"],
            request=_required_request(state),
            route=state["route_selection"].route.value,
            reflection=state.get("self_reflection"),
            contexts=state.get("reranked_context", ()),
            corrective_actions=state.get("corrective_actions", ()),
            model_executions=state.get("model_executions", ()),
            loop_count=state.get("loop_count", 0),
            stage_history=state.get("stage_history", ()),
        )
        return RagGraphState(
            result=decision.result,
            status=decision.status,
            final_answer=decision.result.answer_text,
            stage_history=_append_stage(state, "post_processing_safety"),
        )

    def _route_after_selection(self, state: RagGraphState) -> str:
        return self._policy.route_after_selection(state["route_selection"].route).value

    def _route_after_crag(self, state: RagGraphState) -> str:
        request = _required_active_request(state)
        return self._policy.route_after_crag(
            evaluation=state["context_evaluation"],
            has_context=bool(state.get("reranked_context", ())),
            loop_count=state.get("loop_count", 0),
            max_loops=state.get("max_loops", self._max_loops),
            rewrite_available=self._corrective_query_rewriter is not None,
            allow_web=request.allow_web,
            web_fallback_available=self._web_fallback_retriever is not None,
        ).value

    def _route_after_web_fallback(self, state: RagGraphState) -> str:
        return self._policy.route_after_web_fallback(
            has_context=bool(state.get("reranked_context", ()))
        ).value


def _required_request(state: RagGraphState) -> RagRequest:
    request = state.get("request")
    if request is None:
        raise RuntimeError("RAG graph state missing request.")
    return request


def _required_active_request(state: RagGraphState) -> RagRequest:
    request = state.get("active_request")
    if request is None:
        raise RuntimeError("RAG graph state missing active request.")
    return request


def _required_query_context(state: RagGraphState) -> RagQueryContext:
    context = state.get("query_context")
    if context is None:
        raise RuntimeError("RAG graph state missing query context.")
    return context


def _append_stage(state: RagGraphState, stage: str) -> tuple[str, ...]:
    return (*state.get("stage_history", ()), stage)


def _request_for_query(
    request: RagRequest,
    *,
    query: str,
    selection: str,
    executions: tuple[RagQueryModelExecution, ...],
) -> RagRequest:
    return replace(
        request,
        query=query,
        metadata={
            **dict(request.metadata),
            "adaptive_route": selection,
            "model_executions": [execution.to_dict() for execution in executions],
        },
    )
