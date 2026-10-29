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
