from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from adaptive_form_agent import agents
from adaptive_form_agent.agents import build_graph
from adaptive_form_agent.api import create_app
from adaptive_form_agent.handoffs import DomainReport, FillerReport, FormIntelligenceReport
from adaptive_form_agent.prompts import (
    FILLING_PROMPT,
    FORM_INTELLIGENCE_PROMPT,
    SUPERVISOR_PROMPT,
)

from helpers import FILLER_DONE, form_source, scripted, tool_call


def test_health_endpoint_without_model_credentials():
    client = TestClient(create_app(include_agent=False))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "contractVersion": "1.0",
        "agentEnabled": False,
    }


def test_deep_agent_graph_builds_with_specialists():
    model = scripted()
    graph = build_graph(model=model, subagent_model=model)
    assert graph.name == "adaptive_form_supervisor"
    assert graph.checkpointer is not True


def test_supervisor_has_no_form_tools_and_specialists_are_isolated(monkeypatch):
    captured = {}

    def capture_deep_agent(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(agents, "create_deep_agent", capture_deep_agent)
    build_graph(model="model", subagent_model="subagent-model")

    specialists = {s["name"]: s for s in captured["subagents"]}
    assert list(specialists) == ["domain", "form_intelligence", "filling"]
    assert "tools" not in captured
    assert "middleware" not in captured
    assert [t.name for t in specialists["domain"]["tools"]] == []
    assert [t.name for t in specialists["form_intelligence"]["tools"]] == [
        "search_components",
        "get_component",
        "find_actions",
    ]
    assert [t.name for t in specialists["filling"]["tools"]] == [
        "get_component",
        "get_dropdown_options",
        "search_input_options",
        "set_form_state",
    ]
    assert specialists["domain"]["response_format"] is DomainReport
    assert specialists["form_intelligence"]["response_format"] is FormIntelligenceReport
    assert specialists["filling"]["response_format"] is FillerReport


def test_prompts_route_work_and_forbid_guessing():
    for phrase in [
        "You have no form tools",
        "delegate straight to filling",
        "first ask form_intelligence for its componentName",
        "If several actions or buttons could apply, ask which one",
        "Never ask the user for a revision number",
        "only when the filling report says so",
    ]:
        assert phrase in " ".join(SUPERVISOR_PROMPT.split())
    assert "read-only" in FORM_INTELLIGENCE_PROMPT
    assert "does not mean the form is ready to submit" in " ".join(
        FORM_INTELLIGENCE_PROMPT.split()
    )
    assert "only agent that can change the form" in FILLING_PROMPT
    assert "Do not search or explore" in FILLING_PROMPT


def run_filler(filler_messages, source=None, thread="t"):
    """Run a supervisor that delegates once to the filling specialist."""
    supervisor = scripted(
        tool_call("task", {"description": "set it", "subagent_type": "filling"}, "t1"),
        AIMessage(content="done"),
    )
    filler = scripted(*filler_messages)
    graph = build_graph(model=supervisor, subagent_model=filler)
    config = {"configurable": {"thread_id": thread}}
    first = graph.invoke(
        {
            "messages": [HumanMessage("set subsidiary to yes")],
            "formIntelligenceInput": source or form_source(),
        },
        config,
    )
    return graph, config, filler, first


def test_filler_runs_in_the_browser_through_an_interrupt_and_refreshes_state():
    graph, config, _, first = run_filler(
        [
            tool_call(
                "set_form_state",
                {"patches": [{"componentName": "hasSubsidiary", "value": "yes"}]},
                "f1",
            ),
            tool_call("FillerReport", FILLER_DONE, "f2"),
        ]
    )

    payload = first["__interrupt__"][0].value
    assert payload["type"] == "form-operation"
    assert payload["operation"] == "setFormState"
    assert payload["patches"] == [{"componentName": "hasSubsidiary", "value": "yes"}]
    assert "expectedRevision" not in payload

    fresh = form_source(subsidiary_visible=True)
    final = graph.invoke(
        Command(
            resume={
                "outcome": {"status": "applied", "configRevision": 1},
                "intelligenceSource": fresh,
            }
        ),
        config,
    )

    assert final["formIntelligenceInput"] == fresh
    report = FillerReport.model_validate_json(final["messages"][-2].content)
    assert report.status == "applied"
    assert report.configuration_refreshed is True


def test_preflight_rejects_unsafe_patches_without_contacting_the_browser():
    _, _, filler, result = run_filler(
        [
            tool_call(
                "set_form_state",
                {
                    "patches": [
                        {"componentName": "subsidiaryName", "value": "Hidden Ltd"},
                        {"componentName": "ghost", "value": 1},
                        {"componentName": "subsidiaryCountry", "value": "GB"},
                    ]
                },
                "f1",
            ),
            tool_call(
                "FillerReport",
                {**FILLER_DONE, "status": "rejected", "applied": []},
                "f2",
            ),
        ]
    )

    assert "__interrupt__" not in result
    tool_result = filler.prompts[1][-1].content
    assert "Component is hidden." in tool_result
    assert "Unknown component." in tool_result


def test_choice_values_must_come_from_an_option_lookup():
    source = form_source(subsidiary_visible=True)
    graph, config, filler, first = run_filler(
        [
            tool_call(
                "set_form_state",
                {"patches": [{"componentName": "subsidiaryCountry", "value": "GB"}]},
                "f1",
            ),
            tool_call(
                "get_dropdown_options", {"component_name": "subsidiaryCountry"}, "f2"
            ),
            tool_call(
                "set_form_state",
                {"patches": [{"componentName": "subsidiaryCountry", "value": "GB"}]},
                "f3",
            ),
            tool_call("FillerReport", FILLER_DONE, "f4"),
        ],
        source=source,
    )

    lookup = first["__interrupt__"][0].value
    assert lookup["operation"] == "getDropdownOptions"
    assert "not returned by an option lookup" in filler.prompts[1][-1].content

    second = graph.invoke(
        Command(
            resume={
                "componentName": "subsidiaryCountry",
                "configRevision": 1,
                "options": [{"id": "GB", "label": "United Kingdom", "disabled": False}],
                "hasMore": False,
            }
        ),
        config,
    )
    assert second["__interrupt__"][0].value["patches"] == [
        {"componentName": "subsidiaryCountry", "value": "GB"}
    ]


def test_form_intelligence_reads_the_shared_snapshot_and_returns_names_only():
    supervisor = scripted(
        tool_call(
            "task",
            {"description": "which button covers parentCompany?", "subagent_type": "form_intelligence"},
            "t1",
        ),
        AIMessage(content="done"),
    )
    intelligence = scripted(
        tool_call("find_actions", {"component_names": ["parentCompany"]}, "i1"),
        tool_call(
            "FormIntelligenceReport",
            {
                "status": "completed",
                "findings": ["saveSubsidiary covers parentCompany."],
                "components": ["parentCompany"],
                "actions": [{"componentName": "saveSubsidiary", "event": "onPartialSubmit"}],
            },
            "i2",
        ),
    )
    graph = build_graph(model=supervisor, subagent_model=intelligence)

    result = graph.invoke(
        {
            "messages": [HumanMessage("which button saves the parent company?")],
            "formIntelligenceInput": form_source(subsidiary_visible=True),
        },
        {"configurable": {"thread_id": "fi"}},
    )

    tool_result = intelligence.prompts[1][-1].content
    assert "saveSubsidiary" in tool_result
    assert "subsidiaryName" in tool_result
    report = FormIntelligenceReport.model_validate_json(result["messages"][-2].content)
    assert report.components == ["parentCompany"]
    assert "props" not in result["messages"][-2].content
