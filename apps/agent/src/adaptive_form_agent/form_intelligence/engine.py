"""Flat, read-only component search over JSX and IDFConfig."""

from __future__ import annotations

import hashlib
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
    actions: tuple[dict[str, Any], ...]
    on_change: bool


class FormIntelligenceEngine:
    """Build one flat component dictionary and search complete records."""

    def __init__(
        self,
        jsx: str,
        config: Mapping[str, Any],
    ) -> None:
        self.jsx_fingerprint = hashlib.sha256(jsx.encode()).hexdigest()
        self.jsx_index = parse_jsx(jsx)
        self.components: dict[str, Component] = {}
        self._documents: dict[str, str] = {}
        self.update_config(config)

    def update_config(self, config: Mapping[str, Any]) -> None:
        """Attach the canonical config snapshot to the static JSX index."""
        props = config["props"]
        state = config["state"]
        actions_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for action in config["actions"]:
            actions_by_name[action["componentName"]].append(dict(action))
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
