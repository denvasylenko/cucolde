from __future__ import annotations

from typing import Any

from langchain.tools import ToolRuntime, tool

from .engine import FormIntelligenceEngine

_ENGINES: dict[str, FormIntelligenceEngine] = {}


def session_key(config: dict[str, Any]) -> str:
    for values in (config.get("configurable", {}), config.get("metadata", {})):
        for name in ("thread_id", "threadId", "run_id"):
            if values.get(name):
                return str(values[name])
    return "default"


def set_engine(key: str, engine: FormIntelligenceEngine) -> None:
    _ENGINES[key] = engine


def get_engine(key: str) -> FormIntelligenceEngine | None:
    return _ENGINES.get(key)


def _current(runtime: ToolRuntime) -> FormIntelligenceEngine:
    engine = get_engine(session_key(runtime.config))
    if engine is None:
        raise ValueError("The frontend has not supplied JSX and IDFConfig.")
    return engine


@tool
def search_components(
    query: str, runtime: ToolRuntime, limit: int = 8
) -> dict[str, Any]:
    """Find components or sections by name, label, type, and ancestors."""
    return _current(runtime).search_components(query, limit)


@tool
def inspect_component(
    component_name: str, runtime: ToolRuntime
) -> dict[str, Any]:
    """Inspect one exact component and its current explicit configuration."""
    return _current(runtime).inspect_component(component_name)


@tool
def get_navigation_path(
    component_name: str, runtime: ToolRuntime
) -> dict[str, Any]:
    """Return named JSX ancestors for an exact component."""
    return _current(runtime).get_navigation_path(component_name)


FORM_INTELLIGENCE_TOOLS = [
    search_components,
    inspect_component,
    get_navigation_path,
]
