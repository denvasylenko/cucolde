from typing import Awaitable, Callable
from copilotkit import LangGraphAGUIAgent
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import (
    ModelRequest,
    ModelResponse,
    wrap_model_call,
)

from .handoffs import DomainReport, FillingDecision, FormIntelligenceReport
from .form_intelligence.middleware import (
    FormAgentState,
    ingest_form_intelligence_source,
)
from .form_intelligence.tools import FORM_INTELLIGENCE_TOOLS
from .prompts import (
    DOMAIN_PROMPT,
    FILLING_PROMPT,
    FORM_INTELLIGENCE_PROMPT,
    SUPERVISOR_PROMPT,
)
from .settings import settings

@wrap_model_call
async def model_call(
    request: ModelRequest,
    handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
) -> ModelResponse:
    return await handler(request)

def build_graph(model=None, subagent_model=None):
    """Build the Deep Agent graph without invoking a model."""
    supervisor_model = model or settings.supervisor_model
    domain_model = subagent_model or settings.domain_model
    intelligence_model = subagent_model or settings.intelligence_model
    filling_model = subagent_model or settings.filling_model

    subagents = [
        {
            "name": "domain",
            "description": (
                "Interprets domain terminology, rules, prerequisites, and consequences."
            ),
            "model": domain_model,
            "system_prompt": DOMAIN_PROMPT,
            "response_format": DomainReport,
            "tools": [],
            "middleware": [model_call],
        },
        {
            "name": "form_intelligence",
            "description": (
                "Maps concepts to component names and finds navigation, dependencies, "
                "visibility, and onChange caveats in the current form configuration."
            ),
            "model": intelligence_model,
            "system_prompt": FORM_INTELLIGENCE_PROMPT,
            "response_format": FormIntelligenceReport,
            "tools": FORM_INTELLIGENCE_TOOLS,
            "middleware": [model_call],
        },
        {
            "name": "filling",
            "description": (
                "Produces staged typed patches or option-discovery requests; never "
                "executes browser tools directly."
            ),
            "model": filling_model,
            "system_prompt": FILLING_PROMPT,
            "response_format": FillingDecision,
            "tools": [],
        },
    ]

    return create_deep_agent(
        name="adaptive_form_supervisor",
        model=supervisor_model,
        system_prompt=SUPERVISOR_PROMPT,
        subagents=subagents,
        middleware=[
            ingest_form_intelligence_source
        ],
        state_schema=FormAgentState,
        checkpointer=InMemorySaver(),
    )


def build_agui_agent() -> LangGraphAGUIAgent:
    return LangGraphAGUIAgent(
        name="adaptive_form_guide",
        description=(
            "Provides read-only guidance over versioned DynamicForm configurations."
        ),
        graph=build_graph(),
    )
