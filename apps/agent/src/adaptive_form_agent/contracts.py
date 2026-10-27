from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Choice(ContractModel):
    id: str
    label: str
    description: str | None = None
    disabled: bool = False


class FieldDescriptor(ContractModel):
    component_name: str = Field(alias="componentName", min_length=1)
    kind: Literal[
        "text",
        "textarea",
        "radio",
        "checkbox",
        "date",
        "dropdown",
        "search",
        "group",
        "unknown",
    ]
    label: str
    help_text: str | None = Field(default=None, alias="helpText")
    value: Any = None
    required: bool = False
    disabled: bool = False
    visible: bool = True
    sensitive: bool = False
    errors: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list, alias="dependsOn")
    choice_mode: Literal["none", "static", "dropdown", "search", "unknown"] = Field(
        default="none", alias="choiceMode"
    )
    static_options: list[Choice] | None = Field(default=None, alias="staticOptions")


class LayoutNode(ContractModel):
    component_name: str = Field(alias="componentName")
    kind: str
    label: str | None = None
    children: list[LayoutNode] = Field(default_factory=list)


class ActionDescriptor(ContractModel):
    component_name: str = Field(alias="componentName")
    event: Literal["onChange", "onPartialSubmit", "onSaveDraft", "onSubmit"]
    validate_fields: list[str] = Field(default_factory=list, alias="validate")
    collect: list[str] = Field(default_factory=list)
    mutates_configuration: bool = Field(default=False, alias="mutatesConfiguration")


class FormContext(ContractModel):
    contract_version: Literal["1.0"] = Field(alias="contractVersion")
    form_id: str = Field(alias="formId")
    config_revision: int = Field(alias="configRevision", ge=0)
    fields: list[FieldDescriptor]
    layout: list[LayoutNode]
    actions: list[ActionDescriptor] = Field(default_factory=list)
    navigation: dict[str, str] = Field(default_factory=dict)


class FieldPatch(ContractModel):
    component_name: str = Field(alias="componentName", min_length=1)
    value: Any
    reason: str | None = None


class SetFormStateRequest(ContractModel):
    patches: list[FieldPatch] = Field(min_length=1)
    expected_revision: int = Field(alias="expectedRevision", ge=0)
    side_effect_intent: Literal["allow-config-refresh", "suppress"] = Field(
        default="allow-config-refresh", alias="sideEffectIntent"
    )


class ValidationIssue(ContractModel):
    component_name: str = Field(alias="componentName")
    message: str
    code: str | None = None


class RefreshOutcome(ContractModel):
    status: Literal["applied", "partially_applied", "rejected", "stale"]
    applied: list[str] = Field(default_factory=list)
    rejected: list[str] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(
        default_factory=list, alias="validationIssues"
    )
    on_change_triggered: bool = Field(default=False, alias="onChangeTriggered")
    previous_revision: int = Field(alias="previousRevision", ge=0)
    config_revision: int = Field(alias="configRevision", ge=0)
    changed_components: list[str] = Field(default_factory=list, alias="changedComponents")
    visible_components: list[str] = Field(default_factory=list, alias="visibleComponents")


class OptionQuery(ContractModel):
    component_name: str = Field(alias="componentName", min_length=1)
    expected_revision: int = Field(alias="expectedRevision", ge=0)
    term: str | None = None
    page: int = Field(default=1, ge=1)


class OptionResult(ContractModel):
    component_name: str = Field(alias="componentName")
    config_revision: int = Field(alias="configRevision", ge=0)
    options: list[Choice]
    has_more: bool = Field(default=False, alias="hasMore")


class Guidance(ContractModel):
    summary: str
    consequences: list[str] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list, alias="unresolvedItems")
    suggested_navigation: str | None = Field(default=None, alias="suggestedNavigation")
