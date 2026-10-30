from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HandoffModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class DomainReport(HandoffModel):
    status: Literal["completed", "partial", "blocked", "failed"]
    summary: str
    concepts: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    consequences: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    requested_form_facts: list[str] = Field(
        default_factory=list, alias="requestedFormFacts"
    )


class ActionKey(HandoffModel):
    component_name: str = Field(alias="componentName")
    event: str


class FormIntelligenceReport(HandoffModel):
    """Names and concise facts; full component records stay in the specialist."""

    status: Literal["completed", "partial", "blocked"]
    findings: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    actions: list[ActionKey] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)


class RejectedPatch(HandoffModel):
    component_name: str = Field(alias="componentName")
    reason: str


class FillerReport(HandoffModel):
    status: Literal["applied", "partially_applied", "rejected", "blocked"]
    applied: list[str] = Field(default_factory=list)
    rejected: list[RejectedPatch] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    configuration_refreshed: bool = Field(
        default=False, alias="configurationRefreshed"
    )
    notes: list[str] = Field(default_factory=list)
