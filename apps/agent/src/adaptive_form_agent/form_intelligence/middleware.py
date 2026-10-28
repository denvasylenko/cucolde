from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NotRequired

from deepagents.graph import DeepAgentState
from langchain.agents.middleware import after_agent, before_agent
from langgraph.runtime import Runtime

from .engine import FormIntelligenceEngine
from .tools import ENGINE_CONTEXT_KEY

class FormAgentState(DeepAgentState):
    formIntelligenceInput: NotRequired[dict[str, Any] | None]


@before_agent(state_schema=FormAgentState)
def build_form_intelligence_engine(
    state: FormAgentState, runtime: Runtime
) -> dict[str, Any] | None:
    """Build a fresh engine in the run-scoped context."""

    source = state.get("formIntelligenceInput")
    if not isinstance(source, Mapping):
        return None
    jsx = source.get("jsx")
    idf_config = source.get("idfConfig")
    if isinstance(jsx, str) and isinstance(idf_config, Mapping):
        if not isinstance(runtime.context, dict):
            raise ValueError("Form Intelligence requires a dictionary runtime context.")
        runtime.context[ENGINE_CONTEXT_KEY] = FormIntelligenceEngine(jsx, idf_config)
    return None


@after_agent
def clear_form_intelligence_engine(
    _state: FormAgentState, runtime: Runtime
) -> None:
    """Discard the engine after the Form Intelligence sub-agent finishes."""
    if isinstance(runtime.context, dict):
        runtime.context.pop(ENGINE_CONTEXT_KEY, None)
