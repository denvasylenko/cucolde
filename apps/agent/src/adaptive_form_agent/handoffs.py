from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .contracts import FieldPatch, Guidance


class HandoffModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class DomainReport(HandoffModel):
    concepts: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    consequences: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class FormIntelligenceReport(HandoffModel):
    target_components: list[str] = Field(default_factory=list, alias="targetComponents")
    controlling_components: list[str] = Field(
        default_factory=list, alias="controllingComponents"
    )
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    navigation: list[str] = Field(default_factory=list)
    on_change_caveats: list[str] = Field(
        default_factory=list, alias="onChangeCaveats"
    )
    unresolved_components: list[str] = Field(
        default_factory=list, alias="unresolvedComponents"
    )


class ToolRequest(HandoffModel):
    tool: Literal["setFormState", "getDropdownOptions", "searchInputOptions"]
    arguments: dict[str, Any]
    purpose: str


class FillingDecision(HandoffModel):
    phase: Literal[
        "controlling_patch",
        "option_discovery",
        "remaining_patch",
        "complete",
        "blocked",
    ]
    patches: list[FieldPatch] = Field(default_factory=list)
    tool_requests: list[ToolRequest] = Field(default_factory=list, alias="toolRequests")
    unresolved_items: list[str] = Field(default_factory=list, alias="unresolvedItems")
    rationale: str


class SupervisorResponse(HandoffModel):
    guidance: Guidance
    next_action: Literal[
        "delegate_domain",
        "delegate_intelligence",
        "delegate_filling",
        "call_frontend_tool",
        "answer_user",
    ] = Field(alias="nextAction")
    notes: list[str] = Field(default_factory=list)
