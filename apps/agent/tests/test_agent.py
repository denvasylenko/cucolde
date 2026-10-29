from fastapi.testclient import TestClient
from copilotkit import CopilotKitMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from adaptive_form_agent import agents
from adaptive_form_agent.agents import build_graph
from adaptive_form_agent.api import create_app
from adaptive_form_agent.handoffs import DomainReport
from adaptive_form_agent.prompts import SUPERVISOR_PROMPT


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
    fake_model = FakeMessagesListChatModel(
        responses=[AIMessage(content="No operation required.")]
    )
    graph = build_graph(model=fake_model, subagent_model=fake_model)
    assert graph.name == "adaptive_form_supervisor"
    assert graph.checkpointer is not True


def test_supervisor_owns_form_tools_and_domain_is_isolated(monkeypatch):
    captured = {}

    def capture_deep_agent(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(agents, "create_deep_agent", capture_deep_agent)
    build_graph(model="model", subagent_model="subagent-model")

    specialists = {
        specialist["name"]: specialist for specialist in captured["subagents"]
    }
    assert list(specialists) == ["domain"]
    assert [tool.name for tool in captured["tools"]] == [
        "search_components",
        "get_component",
    ]
    assert any(
        isinstance(middleware, CopilotKitMiddleware)
        for middleware in captured["middleware"]
    )
    assert not any(
        isinstance(middleware, CopilotKitMiddleware)
        for middleware in specialists["domain"].get("middleware", [])
    )
    assert specialists["domain"]["response_format"] is DomainReport
    assert [tool.name for tool in specialists["domain"]["tools"]] == []


def test_supervisor_prompt_is_guidance_first_and_mutation_safe():
    required_steps = [
        "not a form crawler or an automatic pre-filler",
        "Answer directly",
        "Ask one focused clarification",
        "Delegate to domain only",
        "Do not enumerate the form",
        "explicitly asks to",
        "Never infer missing dependencies",
        "Do not mutate a disabled component",
        "use only returned IDs",
        "Configuration revisions are supplied internally",
        "Never submit or save",
    ]
    for step in required_steps:
        assert step in SUPERVISOR_PROMPT
