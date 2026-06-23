"""FrankGraphAgent — LangGraph-backed orchestration entry point."""

from __future__ import annotations

import uuid
from typing import Callable, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from ..agent import FrankAgent, ParsedIntent
from ..templates.base import GeneratedCode
from .builder import build_frank_graph, graph_result_to_dict


class FrankGraphAgent:
    """Drop-in LangGraph orchestrator wrapping the existing FrankAgent stack."""

    def __init__(self, work_dir: Optional[str] = None, timeout: int = 600):
        self._agent = FrankAgent(work_dir=work_dir, timeout=timeout)
        self._checkpointer = MemorySaver()
        self._graph = build_frank_graph(self._agent, checkpointer=self._checkpointer)
        self._progress_callback: Optional[Callable] = None

    @property
    def agent(self) -> FrankAgent:
        return self._agent

    @property
    def session(self):
        return self._agent.session

    @property
    def executor(self):
        return self._agent.executor

    def _config(self, thread_id: Optional[str] = None) -> dict:
        return {"configurable": {"thread_id": thread_id or uuid.uuid4().hex}}

    def invoke(
        self,
        text: str,
        *,
        execute: bool = True,
        interpret: bool = True,
        entry_route: Optional[str] = None,
        require_confirmation: bool = False,
        confirmed: bool = False,
        thread_id: Optional[str] = None,
    ) -> dict:
        final_state = self._graph.invoke(
            {
                "user_input": text,
                "execute": execute,
                "interpret": interpret,
                "entry_route": entry_route,
                "require_confirmation": require_confirmation,
                "confirmed": confirmed,
                "warnings": [],
            },
            config=self._config(thread_id),
        )
        return graph_result_to_dict(final_state)

    def resume(self, thread_id: str, *, confirmed: bool = True) -> dict:
        final_state = self._graph.invoke(
            Command(resume=confirmed),
            config=self._config(thread_id),
        )
        return graph_result_to_dict(final_state)

    def process_request(self, text: str) -> dict:
        return self.invoke(text, execute=False, interpret=False)

    def run(self, text: str, interpret: bool = True) -> dict:
        return self.invoke(text, execute=True, interpret=interpret)

    def run_autonomous(
        self,
        text: str,
        progress_callback: Optional[Callable] = None,
        *,
        require_confirmation: bool = True,
        confirmed: bool = False,
        thread_id: Optional[str] = None,
    ) -> dict:
        self._progress_callback = progress_callback
        self._agent._progress_callback = progress_callback
        tid = thread_id or uuid.uuid4().hex

        if confirmed and thread_id:
            return self.resume(thread_id, confirmed=True)

        result = self.invoke(
            text,
            execute=False,
            interpret=False,
            entry_route="complex",
            require_confirmation=require_confirmation,
            confirmed=confirmed if not require_confirmation else False,
            thread_id=tid,
        )
        if result.get("awaiting_confirmation"):
            result["thread_id"] = tid
        return result

    def plan_workflow(self, text: str):
        return self._agent.plan_workflow(text)

    def is_complex_query(self, text: str) -> bool:
        return self._agent.is_complex_query(text)

    def generate_code(self, intent: ParsedIntent) -> GeneratedCode:
        return self._agent.generate_code(intent)

    def adjust_intent(self, intent: ParsedIntent, overrides: dict) -> ParsedIntent:
        return self._agent.adjust_intent(intent, overrides)

    def _infer_defaults(self, intent: ParsedIntent) -> None:
        self._agent._infer_defaults(intent)

    def run_workflow(self, molecule: str, workflow_type: str = "opt_freq", **kwargs):
        return self._agent.run_workflow(molecule, workflow_type, **kwargs)

    def explain(self, question: str) -> str:
        return self._agent.explain(question)

    def parse_intent(self, text: str, use_session: bool = True) -> ParsedIntent:
        return self._agent.parse_intent(text, use_session=use_session)

    def get_help(self) -> str:
        return self._agent.get_help()
