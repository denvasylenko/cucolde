from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

JSX = """
<DynamicForm componentName="subsidiaryForm">
  <Section componentName="companyDetails">
    <TextInput componentName="companyName" />
    <RadioGroup componentName="hasSubsidiary" />
    <Button componentName="saveCompany" />
    <Accordion componentName="subsidiaryDetails">
      <TextInput componentName="subsidiaryName" />
      <Dropdown componentName="subsidiaryCountry" />
      <SearchInput componentName="parentCompany" />
      <Button componentName="saveSubsidiary" />
    </Accordion>
  </Section>
</DynamicForm>
"""


def form_source(
    *, subsidiary_visible: bool = False, subsidiary_name: str | None = None
) -> dict[str, Any]:
    """A small multi-section form with two partial-submit actions."""

    def field(label: str, **props: Any) -> dict[str, Any]:
        return {"label": label, "visible": True, "disabled": False, **props}

    hidden = {"visible": subsidiary_visible}
    state: dict[str, Any] = {"companyName": "Acme Holdings", "hasSubsidiary": "no"}
    if subsidiary_name is not None:
        state["subsidiaryName"] = subsidiary_name
    return {
        "formId": "test",
        "jsx": JSX,
        "idfConfig": {
            "props": {
                "subsidiaryForm": {"kind": "form"},
                "companyDetails": {"kind": "section"},
                "subsidiaryDetails": {"kind": "accordion"},
                "companyName": field("Company name", required=True, sensitive=True),
                "hasSubsidiary": field("Has subsidiary?", required=True),
                "subsidiaryName": field("Subsidiary name", required=True, **hidden),
                "subsidiaryCountry": field(
                    "Country", required=True, choiceMode="dropdown", **hidden
                ),
                "parentCompany": field(
                    "Parent company", required=False, choiceMode="search", **hidden
                ),
                "saveCompany": field("Save company details"),
                "saveSubsidiary": field("Save subsidiary details"),
            },
            "state": state,
            "actions": [
                {
                    "componentName": "hasSubsidiary",
                    "event": "onChange",
                    "collect": ["hasSubsidiary"],
                    "validate": ["hasSubsidiary"],
                    "mutatesConfiguration": True,
                },
                {
                    "componentName": "saveCompany",
                    "event": "onPartialSubmit",
                    "collect": ["companyName", "hasSubsidiary"],
                    "validate": ["companyName", "hasSubsidiary"],
                    "mutatesConfiguration": False,
                },
                {
                    "componentName": "saveSubsidiary",
                    "event": "onPartialSubmit",
                    "collect": ["subsidiaryName", "subsidiaryCountry", "parentCompany"],
                    "validate": ["subsidiaryName", "subsidiaryCountry"],
                    "mutatesConfiguration": False,
                },
            ],
            "events": {"onChange": {"hasSubsidiary": True}},
        },
    }


def tool_call(name: str, args: dict[str, Any], call_id: str) -> AIMessage:
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": call_id}]
    )


class ScriptedModel(BaseChatModel):
    """Replays scripted messages and records every prompt it receives."""

    script: Any
    prompts: list[Any] = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.prompts.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=next(self.script))])


def scripted(*messages: AIMessage) -> ScriptedModel:
    return ScriptedModel(script=iter(messages), prompts=[])


FILLER_DONE = {
    "status": "applied",
    "applied": ["hasSubsidiary"],
    "rejected": [],
    "unresolved": [],
    "configurationRefreshed": True,
    "notes": [],
}
