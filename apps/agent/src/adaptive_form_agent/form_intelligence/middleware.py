from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any, NotRequired

from deepagents.graph import DeepAgentState
from langchain.agents.middleware import before_agent
from langgraph.runtime import Runtime

from .engine import FormIntelligenceEngine
from .tools import get_engine, set_engine

class FormAgentState(DeepAgentState):
    formIntelligenceInput: NotRequired[dict[str, Any] | None]


@before_agent(state_schema=FormAgentState)
def ingest_form_intelligence_source(
    state: FormAgentState, runtime: Runtime
) -> dict[str, Any] | None:
    """Index CopilotKit shared state, then remove its large transient payload."""

    source = state.get("formIntelligenceInput")
    if not isinstance(source, Mapping):
        return None
    jsx = source.get("jsx")
    idf_config = source.get("idfConfig")
    if isinstance(jsx, str) and isinstance(idf_config, Mapping):
        key = _runtime_session_key(runtime, source)
        engine = get_engine(key)
        fingerprint = hashlib.sha256(jsx.encode()).hexdigest()
        if engine is None or engine.jsx_fingerprint != fingerprint:
            set_engine(key, FormIntelligenceEngine(jsx, idf_config))
        else:
            engine.update_config(idf_config)
    return {"formIntelligenceInput": None}


def _runtime_session_key(runtime: Runtime, source: Mapping[str, Any]) -> str:
    execution_info = runtime.execution_info
    if execution_info is not None:
        if execution_info.thread_id:
            return str(execution_info.thread_id)
        if execution_info.run_id:
            return str(execution_info.run_id)
    form_id = source.get("formId")
    return str(form_id) if form_id else "default"
