from __future__ import annotations

from typing import Any, NotRequired

from deepagents.graph import DeepAgentState


class FormAgentState(DeepAgentState):
    """Checkpointed state shared by the supervisor and its sub-agents."""

    formIntelligenceInput: NotRequired[dict[str, Any] | None]
    seenOptions: NotRequired[dict[str, list[str]]]
