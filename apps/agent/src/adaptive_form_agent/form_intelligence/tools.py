from __future__ import annotations

from typing import Any

from langchain.tools import ToolRuntime, tool

from .engine import FormIntelligenceEngine


def current_engine(runtime: ToolRuntime) -> FormIntelligenceEngine:
    """Build the engine from the checkpointed frontend snapshot.

    JSX parsing is cached, so rebuilding per call only re-attaches the config.
    """
    source = runtime.state.get("formIntelligenceInput")
    if not source:
        raise ValueError("The frontend has not supplied JSX and IDFConfig.")
    return FormIntelligenceEngine(source["jsx"], source["idfConfig"])


@tool
def search_components(
    query: str, runtime: ToolRuntime, limit: int = 8
) -> dict[str, Any]:
    """Return complete components ranked by name, props, tag, and path."""
    return current_engine(runtime).search_components(query, limit)


@tool
def get_component(
    component_name: str, runtime: ToolRuntime
) -> dict[str, Any] | None:
    """Return one complete component by its exact componentName."""
    return current_engine(runtime).get_component(component_name)


@tool
def find_actions(
    runtime: ToolRuntime,
    component_names: list[str] | None = None,
    event: str | None = None,
) -> dict[str, Any]:
    """Find which actions (for example onPartialSubmit buttons) cover components.

    Returns each matching action's trigger, event, collect/validate scope, and
    the scope components that are still missing a required value or carry
    explicit errors. Use get_component for details of any listed component.
    """
    return current_engine(runtime).find_actions(component_names, event)


FORM_INTELLIGENCE_TOOLS = [search_components, get_component, find_actions]
