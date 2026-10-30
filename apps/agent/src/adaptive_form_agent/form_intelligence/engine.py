"""Flat, read-only component search over JSX and IDFConfig."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from rapidfuzz import fuzz, process

from .jsx_index import parse_jsx


@dataclass(frozen=True)
class Component:
    name: str
    tag: str
    path: tuple[str, ...]
    props: dict[str, Any]
    state: Any
    has_value: bool
    actions: tuple[dict[str, Any], ...]
    on_change: bool


def _has_value(value: Any) -> bool:
    return value not in (None, "", [], {})


def _is_missing_required(component: Component) -> bool:
    props = component.props
    return (
        props.get("required") is True
        and props.get("visible") is not False
        and props.get("disabled") is not True
        and not component.has_value
    )


class FormIntelligenceEngine:
    """Build one flat component dictionary and search complete records."""

    def __init__(
        self,
        jsx: str,
        config: Mapping[str, Any],
    ) -> None:
        self.jsx_index = parse_jsx(jsx)
        self.components: dict[str, Component] = {}
        self._actions: list[dict[str, Any]] = []
        self._documents: dict[str, str] = {}
        self.update_config(config)

    def update_config(self, config: Mapping[str, Any]) -> None:
        """Attach the canonical config snapshot to the static JSX index."""
        props = config["props"]
        state = config["state"]
        self._actions = [dict(action) for action in config["actions"]]
        actions_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for action in self._actions:
            actions_by_name[action["componentName"]].append(action)
        on_change = config["events"]["onChange"]

        self.components = {
            name: Component(
                name=name,
                tag=layout.tag,
                path=layout.path,
                props=dict(props[name]),
                state=(
                    None
                    if props[name].get("sensitive") is True
                    else state.get(name)
                ),
                has_value=_has_value(state.get(name)),
                actions=tuple(actions_by_name[name]),
                on_change=bool(on_change.get(name)),
            )
            for name, layout in self.jsx_index.items()
        }
        self._documents = {
            name: " ".join(
                (
                    component.name,
                    component.tag,
                    *component.path,
                    json.dumps(component.props, ensure_ascii=False),
                )
            )
            for name, component in self.components.items()
        }

    def search_components(self, query: str, limit: int = 8) -> dict[str, Any]:
        """Return complete component records ranked by RapidFuzz."""
        matches = process.extract(
            query,
            self._documents,
            scorer=fuzz.WRatio,
            limit=limit,
        )
        return {
            "query": query,
            "matches": [
                {**asdict(self.components[name]), "score": round(score / 100, 4)}
                for _, score, name in matches
            ],
        }

    def get_component(self, component_name: str) -> dict[str, Any] | None:
        """Return one complete component record by its exact componentName."""
        component = self.components.get(component_name)
        return asdict(component) if component is not None else None

    def find_actions(
        self,
        component_names: list[str] | None = None,
        event: str | None = None,
    ) -> dict[str, Any]:
        """Return compact action scopes, optionally filtered.

        An action matches `component_names` when its trigger, `collect`, or
        `validate` mentions any of them. `missing_required` counts components in
        the action scope that are explicitly required, not hidden or disabled,
        and have no value. `with_errors` lists scope components with explicit
        errors. These are facts only: scope membership does not prove validity
        and neither list means the form is ready to submit.
        """
        wanted = set(component_names or ())
        results = []
        for action in self._actions:
            scope = list(dict.fromkeys([*action["collect"], *action["validate"]]))
            if event is not None and action["event"] != event:
                continue
            if wanted and wanted.isdisjoint([action["componentName"], *scope]):
                continue
            trigger = self.components[action["componentName"]]
            members = [self.components[name] for name in scope]
            results.append(
                {
                    "trigger": {
                        "name": trigger.name,
                        "label": trigger.props.get("label"),
                        "path": trigger.path,
                    },
                    "event": action["event"],
                    "collect": action["collect"],
                    "validate": action["validate"],
                    "mutatesConfiguration": action["mutatesConfiguration"],
                    "missing_required": [
                        member.name for member in members if _is_missing_required(member)
                    ],
                    "with_errors": [
                        member.name for member in members if member.props.get("errors")
                    ],
                }
            )
        return {"actions": results}
