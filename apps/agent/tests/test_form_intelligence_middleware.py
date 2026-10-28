from langgraph.runtime import Runtime

from adaptive_form_agent.form_intelligence import middleware
from adaptive_form_agent.form_intelligence.engine import FormIntelligenceEngine
from adaptive_form_agent.form_intelligence.tools import ENGINE_CONTEXT_KEY


def test_ingestion_builds_a_run_scoped_engine():
    payload = {
        "jsx": '<Field componentName="name" />',
        "idfConfig": {
            "props": {"name": {"label": "Name", "visible": True}},
            "state": {},
            "actions": [],
            "events": {"onChange": {}},
        },
        "formId": "test",
    }
    state = {
        "messages": [],
        "formIntelligenceInput": payload,
    }
    context = {}
    runtime = Runtime(context=context)

    update = middleware.build_form_intelligence_engine.before_agent(state, runtime)

    assert update is None
    engine = context[ENGINE_CONTEXT_KEY]
    assert isinstance(engine, FormIntelligenceEngine)
    assert engine.search_components("name")["matches"][0]["name"] == "name"

    middleware.clear_form_intelligence_engine.after_agent(state, runtime)
    assert context == {}


def test_ingestion_ignores_runs_without_shared_input():
    context = {}
    update = middleware.build_form_intelligence_engine.before_agent(
        {"messages": []}, Runtime(context=context)
    )
    assert update is None
    assert context == {}
