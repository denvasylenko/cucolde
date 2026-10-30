"""Filling tools that ask the browser to execute form operations.

Each tool validates its request against the engine, then calls `interrupt()`.
CopilotKit's `useInterrupt` runs the adapter call in the browser and resumes the
graph with the outcome plus the refreshed `{jsx, idfConfig}` snapshot. The
configuration revision is never a tool argument; the browser injects its latest.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command, interrupt
from pydantic import BaseModel

from .engine import FormIntelligenceEngine
from .tools import current_engine

INTERRUPT_TYPE = "form-operation"


class FieldPatch(BaseModel):
    componentName: str
    value: Any
    reason: str | None = None


def _reply(runtime: ToolRuntime, content: Any, **update: Any) -> Command:
    return Command(
        update={
            **update,
            "messages": [
                ToolMessage(json.dumps(content), tool_call_id=runtime.tool_call_id)
            ],
        }
    )


def _target_rejection(engine: FormIntelligenceEngine, name: str) -> str | None:
    component = engine.components.get(name)
    if component is None:
        return "Unknown component."
    if component.props.get("visible") is False:
        return "Component is hidden."
    if component.props.get("disabled") is True:
        return "Component is disabled."
    return None


def _rejection(
    engine: FormIntelligenceEngine,
    runtime: ToolRuntime,
    patch: FieldPatch,
) -> str | None:
    reason = _target_rejection(engine, patch.componentName)
    if reason is not None:
        return reason
    props = engine.components[patch.componentName].props
    if props.get("choiceMode") in ("dropdown", "search"):
        seen = runtime.state.get("seenOptions", {}).get(patch.componentName, [])
        if patch.value not in seen:
            return "Value was not returned by an option lookup in this conversation."
    return None


def _lookup(
    runtime: ToolRuntime,
    operation: Literal["getDropdownOptions", "searchInputOptions"],
    component_name: str,
    page: int,
    term: str | None = None,
) -> Command:
    reason = _target_rejection(current_engine(runtime), component_name)
    if reason is not None:
        return _reply(runtime, {"status": "rejected", "reason": reason})

    result = interrupt(
        {
            "type": INTERRUPT_TYPE,
            "operation": operation,
            "componentName": component_name,
            "page": page,
            **({"term": term} if term else {}),
        }
    )
    if "error" in result:
        return _reply(runtime, {"status": "failed", **result})
    seen = dict(runtime.state.get("seenOptions", {}))
    seen[component_name] = sorted(
        {*seen.get(component_name, []), *(option["id"] for option in result["options"])}
    )
    return _reply(runtime, result, seenOptions=seen)


@tool
def get_dropdown_options(
    component_name: str, runtime: ToolRuntime, page: int = 1
) -> Command:
    """Get the valid options of a dropdown component from the frontend."""
    return _lookup(runtime, "getDropdownOptions", component_name, page)


@tool
def search_input_options(
    component_name: str, term: str, runtime: ToolRuntime, page: int = 1
) -> Command:
    """Search the valid options of a search-input component (2+ characters)."""
    return _lookup(runtime, "searchInputOptions", component_name, page, term)


@tool
def set_form_state(
    patches: list[FieldPatch],
    runtime: ToolRuntime,
    allow_config_refresh: bool = True,
) -> Command:
    """Apply field patches in the browser form and return the refresh outcome.

    Patches for unknown, hidden, or disabled components, and dropdown/search
    values not returned by an option lookup, are rejected without contacting the
    browser. Apply controlling fields in their own call.
    """
    engine = current_engine(runtime)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for patch in patches:
        reason = _rejection(engine, runtime, patch)
        if reason is None:
            accepted.append(patch.model_dump(exclude_none=True))
        else:
            rejected.append({"componentName": patch.componentName, "reason": reason})

    if not accepted:
        return _reply(runtime, {"status": "rejected", "preflightRejected": rejected})

    result = interrupt(
        {
            "type": INTERRUPT_TYPE,
            "operation": "setFormState",
            "patches": accepted,
            "sideEffectIntent": "allow-config-refresh" if allow_config_refresh else "suppress",
        }
    )
    if "error" in result:
        return _reply(runtime, {"status": "failed", **result})
    return _reply(
        runtime,
        {"outcome": result["outcome"], "preflightRejected": rejected},
        formIntelligenceInput=result["intelligenceSource"],
    )


FILLING_TOOLS = [
    get_dropdown_options,
    search_input_options,
    set_form_state,
]
