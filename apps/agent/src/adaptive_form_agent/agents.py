from copilotkit import LangGraphAGUIAgent
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver

from .form_intelligence.filling_tools import FILLING_TOOLS
from .form_intelligence.state import FormAgentState
from .form_intelligence.tools import FORM_INTELLIGENCE_TOOLS, get_component
from .handoffs import DomainReport, FillerReport, FormIntelligenceReport
from .prompts import (
    DOMAIN_PROMPT,
    FILLING_PROMPT,
    FORM_INTELLIGENCE_PROMPT,
    SUPERVISOR_PROMPT,
)
from .settings import settings


def build_graph(model=None, subagent_model=None):
    """Build the Deep Agent graph without invoking a model."""
    subagents = [
        {
            "name": "domain",
            "description": (
                "Interprets domain terminology, rules, prerequisites, and consequences."
            ),
            "model": subagent_model or settings.domain_model,
            "system_prompt": DOMAIN_PROMPT,
            "response_format": DomainReport,
            "tools": [],
        },
        {
            "name": "form_intelligence",
            "description": (
                "Read-only form exploration: finds components, which actions or "
                "buttons cover them, and what remains missing or has errors."
            ),
            "model": subagent_model or settings.intelligence_model,
            "system_prompt": FORM_INTELLIGENCE_PROMPT,
            "response_format": FormIntelligenceReport,
            "tools": FORM_INTELLIGENCE_TOOLS,
        },
        {
            "name": "filling",
            "description": (
                "Changes the form: sets authorized values and looks up dropdown "
                "or search options. Needs exact componentNames and values."
            ),
            "model": subagent_model or settings.filling_model,
            "system_prompt": FILLING_PROMPT,
            "response_format": FillerReport,
            "tools": [get_component, *FILLING_TOOLS],
        },
    ]

    return create_deep_agent(
        name="adaptive_form_supervisor",
        model=model or settings.supervisor_model,
        system_prompt=SUPERVISOR_PROMPT,
        subagents=subagents,
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
