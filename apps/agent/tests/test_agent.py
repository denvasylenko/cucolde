from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from adaptive_form_agent.agents import build_graph
from adaptive_form_agent.api import create_app
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


def test_supervisor_prompt_enforces_read_only_trajectory():
    required_steps = [
        "raw JSX and IDFConfig are never available",
        "Ask form_intelligence",
        "Do not call frontend tools",
        "Never submit, save",
    ]
    for step in required_steps:
        assert step in SUPERVISOR_PROMPT
