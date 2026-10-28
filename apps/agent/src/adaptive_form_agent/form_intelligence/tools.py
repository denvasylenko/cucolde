from __future__ import annotations

from typing import Any

from langchain.tools import ToolRuntime, tool

from .engine import FormIntelligenceEngine

ENGINE_CONTEXT_KEY = "form_intelligence_engine"


def _current(runtime: ToolRuntime) -> FormIntelligenceEngine:
    context = runtime.context
    engine = context.get(ENGINE_CONTEXT_KEY) if isinstance(context, dict) else None
    if not isinstance(engine, FormIntelligenceEngine):
        raise ValueError("The frontend has not supplied JSX and IDFConfig.")
    return engine


@tool
def search_components(
    query: str, runtime: ToolRuntime, limit: int = 8
) -> dict[str, Any]:
    """Return complete components ranked by name, props, tag, and path."""
    return _current(runtime).search_components(query, limit)


@tool
def get_component(
    component_name: str, runtime: ToolRuntime
) -> dict[str, Any] | None:
    """Return one complete component by its exact componentName."""
    return _current(runtime).get_component(component_name)


FORM_INTELLIGENCE_TOOLS = [search_components, get_component]
