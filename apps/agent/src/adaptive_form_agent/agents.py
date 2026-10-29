from copilotkit import CopilotKitMiddleware, LangGraphAGUIAgent
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import ModelRequest

from .handoffs import DomainReport
from .form_intelligence.middleware import (
    FormAgentState,
    build_form_intelligence_engine,
    clear_form_intelligence_engine,
)
from .form_intelligence.tools import FORM_INTELLIGENCE_TOOLS
from .prompts import DOMAIN_PROMPT, SUPERVISOR_PROMPT
from .settings import settings


class FrontendToolsOnlyMiddleware(CopilotKitMiddleware):
    """Inject frontend tools without serializing runtime dependencies."""

    def _apply_app_context_note(self, request: ModelRequest) -> ModelRequest:
        return request


def build_graph(model=None, subagent_model=None):
    """Build the Deep Agent graph without invoking a model."""
    supervisor_model = model or settings.supervisor_model
    domain_model = subagent_model or settings.domain_model

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
        },
    ]

    return create_deep_agent(
        name="adaptive_form_supervisor",
        model=supervisor_model,
        system_prompt=SUPERVISOR_PROMPT,
        tools=FORM_INTELLIGENCE_TOOLS,
        subagents=subagents,
        middleware=[
            build_form_intelligence_engine,
            FrontendToolsOnlyMiddleware(),
            clear_form_intelligence_engine,
        ],
        state_schema=FormAgentState,
        checkpointer=InMemorySaver(),
    )


def build_agui_agent() -> LangGraphAGUIAgent:
    return LangGraphAGUIAgent(
        name="adaptive_form_guide",
        description=(
            "Guides users through versioned DynamicForm configurations and performs "
            "explicitly requested field updates."
        ),
        graph=build_graph(),
    )
