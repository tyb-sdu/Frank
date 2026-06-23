"""Build and compile the Frank LangGraph workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

from ..agent import ParsedIntent
from ..orchestrator.planner import WorkflowPlan
from . import nodes
from .state import FrankState

if TYPE_CHECKING:
    from ..agent import FrankAgent


def _require_langgraph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise ImportError(
            "LangGraph is required for graph-based orchestration. "
            "Install with: pip install 'frank[langgraph]'"
        ) from exc
    return START, END, StateGraph


def build_frank_graph(agent: "FrankAgent", checkpointer=None):
    """Compile the Frank agent as a LangGraph StateGraph."""
    START, END, StateGraph = _require_langgraph()

    graph = StateGraph(FrankState)

    def bind(fn: Callable) -> Callable:
        return lambda state: fn(agent, state)

    graph.add_node("classify", bind(nodes.classify_node))
    graph.add_node("chat", bind(nodes.chat_node))
    graph.add_node("explain", bind(nodes.explain_node))
    graph.add_node("parse_intent", bind(nodes.parse_intent_node))
    graph.add_node("generate_code", bind(nodes.generate_code_node))
    graph.add_node("execute", bind(nodes.execute_node))
    graph.add_node("interpret", bind(nodes.interpret_node))
    graph.add_node("diagnose", bind(nodes.diagnose_node))
    graph.add_node("plan_workflow", bind(nodes.plan_workflow_node))
    graph.add_node("confirm_complex", bind(nodes.confirm_complex_node))
    graph.add_node("orchestrate", bind(nodes.orchestrate_node))

    graph.add_edge(START, "classify")

    graph.add_conditional_edges(
        "classify",
        lambda state: state.get("route", "calculate"),
        {
            "chat": "chat",
            "explain": "explain",
            "complex": "plan_workflow",
            "calculate": "parse_intent",
            "code_only": "parse_intent",
        },
    )

    graph.add_edge("chat", END)
    graph.add_edge("explain", END)

    def after_plan(state: FrankState) -> str:
        plan_obj = state.get("_plan_obj")
        if plan_obj is not None:
            return "confirm" if plan_obj.is_complex else "orchestrate"
        plan_data = state.get("plan") or {}
        return "confirm" if plan_data.get("is_complex") else "orchestrate"

    graph.add_conditional_edges(
        "plan_workflow",
        after_plan,
        {"confirm": "confirm_complex", "orchestrate": "orchestrate"},
    )

    graph.add_conditional_edges(
        "confirm_complex",
        lambda state: "orchestrate" if state.get("confirmed") else "cancelled",
        {"orchestrate": "orchestrate", "cancelled": END},
    )

    graph.add_edge("orchestrate", END)

    graph.add_edge("parse_intent", "generate_code")

    def after_generate(state: FrankState) -> str:
        if state.get("route") == "code_only" or state.get("execute") is False:
            return "done"
        if state.get("script"):
            return "execute"
        return "done"

    graph.add_conditional_edges(
        "generate_code",
        after_generate,
        {"execute": "execute", "done": END},
    )

    graph.add_conditional_edges(
        "execute",
        lambda state: "interpret" if state.get("execution_success") else "diagnose",
        {"interpret": "interpret", "diagnose": "diagnose"},
    )

    graph.add_edge("interpret", END)
    graph.add_edge("diagnose", END)

    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


def _plan_from_state(final_state: dict[str, Any]) -> Optional[WorkflowPlan]:
    plan_obj = final_state.get("_plan_obj")
    if plan_obj is not None:
        return plan_obj
    plan_data = final_state.get("plan")
    if not plan_data:
        return None
    from ..orchestrator.planner import WorkflowTask

    tasks = [
        WorkflowTask(**task)
        for task in plan_data.get("tasks", [])
        if isinstance(task, dict)
    ]
    return WorkflowPlan(
        workflow_type=plan_data.get("workflow_type", "single"),
        title=plan_data.get("title", ""),
        description=plan_data.get("description", ""),
        tasks=tasks,
        method=plan_data.get("method", "B3LYP"),
        basis=plan_data.get("basis", "6-31g*"),
        confidence=float(plan_data.get("confidence", 0.0)),
        warnings=list(plan_data.get("warnings") or []),
    )


def graph_result_to_dict(final_state: dict[str, Any]) -> dict[str, Any]:
    """Normalize LangGraph final state to FrankAgent-compatible result dicts."""
    if final_state.get("__interrupt__"):
        interrupt_value = final_state["__interrupt__"][0].value
        plan_data = interrupt_value.get("plan") if isinstance(interrupt_value, dict) else {}
        return {
            "awaiting_confirmation": True,
            "plan": _plan_from_state({"plan": plan_data}),
            "interrupt": interrupt_value,
            "warnings": final_state.get("warnings", []),
        }

    route = final_state.get("route")

    if route == "chat" or final_state.get("is_chat"):
        intent = final_state.get("intent") or {}
        return {
            "intent": ParsedIntent(**intent) if intent else ParsedIntent(),
            "code": None,
            "script": final_state.get("script", ""),
            "is_chat": True,
            "chat_message": final_state.get("chat_message", ""),
            "warnings": final_state.get("warnings", []),
        }

    if route == "explain":
        return {
            "answer": final_state.get("explain_answer", ""),
            "success": final_state.get("success", True),
        }

    if route == "complex":
        plan = _plan_from_state(final_state)
        orch = final_state.get("_orchestrator_obj")
        return {
            "plan": plan,
            "result": orch,
            "summary": final_state.get("summary", ""),
            "success": final_state.get("success", False),
            "warnings": final_state.get("warnings", []),
        }

    intent_data = final_state.get("intent") or {}
    intent = ParsedIntent(
        **{k: v for k, v in intent_data.items() if k in ParsedIntent.__dataclass_fields__}
    )

    return {
        "intent": intent,
        "code": final_state.get("_code_obj"),
        "script": final_state.get("script", ""),
        "is_chat": False,
        "execution": final_state.get("_execution_obj") or final_state.get("execution"),
        "parsed": final_state.get("parsed", {}),
        "diagnostics": final_state.get("diagnostics", []),
        "interpretation": final_state.get("interpretation", ""),
        "retry_log": final_state.get("retry_log", []),
        "warnings": final_state.get("warnings", []),
        "plain_language": final_state.get("plain_language", ""),
        "error_diagnosis": final_state.get("error_diagnosis", ""),
    }
