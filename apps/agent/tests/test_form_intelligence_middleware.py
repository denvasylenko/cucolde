from langgraph.runtime import ExecutionInfo, Runtime

from adaptive_form_agent.form_intelligence import middleware
from adaptive_form_agent.form_intelligence import tools


def test_ingestion_indexes_shared_state_and_clears_large_input():
    tools._ENGINES.clear()
    payload = {
        "jsx": '<Field componentName="name" />',
        "idfConfig": {"props": {"name": {"label": "Name", "visible": True}}},
        "formId": "test",
    }
    state = {
        "messages": [],
        "formIntelligenceInput": payload,
    }
    runtime = Runtime(
        execution_info=ExecutionInfo(
            checkpoint_id="checkpoint",
            checkpoint_ns="",
            task_id="task",
            thread_id="thread-123",
        )
    )

    update = middleware.ingest_form_intelligence_source.before_agent(state, runtime)

    assert update == {"formIntelligenceInput": None}
    indexed = tools.get_engine("thread-123")
    assert indexed is not None
    assert indexed.inspect_component("name")["found"] is True


def test_ingestion_ignores_runs_without_shared_input():
    update = middleware.ingest_form_intelligence_source.before_agent(
        {"messages": []}, Runtime()
    )
    assert update is None
