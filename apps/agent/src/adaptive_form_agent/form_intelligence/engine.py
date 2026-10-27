"""Read-only intelligence for static React JSX and DynamicForm IDFConfig."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from rapidfuzz import fuzz, process
from tree_sitter import Language, Parser


@dataclass
class Component:
    node_id: str
    tag: str
    component_name: str | None
    parent_id: str | None
    children: list[str] = field(default_factory=list)
    attrs: dict[str, str] = field(default_factory=dict)
    dynamic_attrs: list[str] = field(default_factory=list)
    line: int = 0
    column: int = 0


class FormIntelligenceEngine:
    """One immutable JSX index with a replaceable configuration snapshot."""

    def __init__(
        self,
        jsx: str,
        config: Mapping[str, Any],
        *,
        language: str = "tsx",
        embed: Callable[[list[str]], Any] | None = None,
    ) -> None:
        self.jsx = jsx
        self.jsx_fingerprint = hashlib.sha256(jsx.encode()).hexdigest()
        self._source = jsx.encode()
        self.embed = embed
        self.components: dict[str, Component] = {}
        self.by_name: dict[str, list[str]] = defaultdict(list)
        self.config: dict[str, Any] = {}
        self._documents: dict[str, str] = {}
        self._embeddings: Any = None
        self._parse(language)
        self.update_config(config)

    def update_config(self, config: Mapping[str, Any]) -> None:
        """Replace dynamic data without reparsing JSX."""
        self.config = dict(config)
        self._documents = {
            node_id: self._search_text(component)
            for node_id, component in self.components.items()
        }
        self._embeddings = (
            self.embed(list(self._documents.values())) if self.embed else None
        )

    def search_components(self, query: str, limit: int = 8) -> dict[str, Any]:
        """Find components and sections using RapidFuzz and optional embeddings."""
        query = query.strip()
        if not query:
            return {"query": query, "matches": [], "warnings": ["Query is empty."]}

        fuzzy_matches = process.extract(
            query,
            self._documents,
            scorer=fuzz.WRatio,
            limit=max(1, min(limit, 20)),
        )
        scores = {node_id: score / 100 for _, score, node_id in fuzzy_matches}

        if self.embed and self._embeddings is not None:
            import numpy as np

            matrix = np.asarray(self._embeddings, dtype=float)
            query_vector = np.asarray(self.embed([query])[0], dtype=float)
            matrix_norm = np.linalg.norm(matrix, axis=1)
            query_norm = np.linalg.norm(query_vector)
            semantic = (
                matrix @ query_vector
                / np.where(matrix_norm * query_norm == 0, 1, matrix_norm * query_norm)
            )
            for node_id, semantic_score in zip(
                self._documents, semantic, strict=True
            ):
                scores[node_id] = 0.6 * scores.get(node_id, 0) + 0.4 * max(
                    float(semantic_score), 0
                )

        ranked = sorted(scores, key=scores.get, reverse=True)[:limit]
        return {
            "query": query,
            "matches": [
                {
                    "componentName": self.components[node_id].component_name,
                    "tag": self.components[node_id].tag,
                    "label": self._label(self.components[node_id]),
                    "visibility": self._visibility(self.components[node_id]),
                    "score": round(scores[node_id], 4),
                }
                for node_id in ranked
            ],
            "warnings": [],
        }

    def inspect_component(self, component_name: str) -> dict[str, Any]:
        """Return compact metadata and the explicit configuration snapshot."""
        node_ids = self.by_name.get(component_name, [])
        if not node_ids:
            return {
                "found": False,
                "componentName": component_name,
                "warnings": ["Component was not found in JSX."],
            }

        component = self.components[node_ids[0]]
        props = self._section_value("props", component_name)
        props_section = self.config.get("props")
        config_path = (
            f"props.{component_name}"
            if isinstance(props_section, Mapping)
            and component_name in props_section
            else None
        )
        state, has_state = self._state(component_name)
        sensitive = isinstance(props, Mapping) and props.get("sensitive") is True
        warnings = [
            f"Dynamic JSX attribute was not evaluated: {item}"
            for item in component.dynamic_attrs
        ]
        if len(node_ids) > 1:
            warnings.append("Multiple JSX components use this componentName.")
        if sensitive and has_state:
            state = None
            has_state = False
            warnings.append("Sensitive current state was redacted.")

        return {
            "found": True,
            "component": {
                **asdict(component),
                "parent": self._named_parent(component),
                "label": self._label(component),
                "configPath": config_path,
                "props": dict(props) if isinstance(props, Mapping) else {},
                "currentState": state,
                "hasState": has_state,
                "visibility": self._visibility(component),
                "onChangeConfigured": self._has_on_change(component_name),
            },
            "warnings": warnings,
        }

    def get_navigation_path(self, component_name: str) -> dict[str, Any]:
        """Return named JSX ancestors from the form root to the component."""
        node_ids = self.by_name.get(component_name, [])
        if not node_ids:
            return {
                "found": False,
                "componentName": component_name,
                "path": [],
                "warnings": ["Component was not found in JSX."],
            }

        path: list[dict[str, Any]] = []
        node_id: str | None = node_ids[0]
        while node_id:
            component = self.components[node_id]
            if component.component_name:
                path.append(
                    {
                        "componentName": component.component_name,
                        "tag": component.tag,
                        "label": self._label(component),
                    }
                )
            node_id = component.parent_id
        path.reverse()
        return {
            "found": True,
            "componentName": component_name,
            "path": path,
            "warnings": (
                ["Multiple JSX components use this componentName."]
                if len(node_ids) > 1
                else []
            ),
        }

    def _parse(self, language: str) -> None:
        if language == "tsx":
            import tree_sitter_typescript

            grammar = Language(tree_sitter_typescript.language_tsx())
        elif language == "jsx":
            import tree_sitter_javascript

            grammar = Language(tree_sitter_javascript.language())
        else:
            raise ValueError("language must be 'jsx' or 'tsx'")

        tree = Parser(grammar).parse(self._source)

        def raw(node: Any) -> str:
            return self._source[node.start_byte : node.end_byte].decode()

        def attributes(opening: Any) -> tuple[dict[str, str], list[str]]:
            static: dict[str, str] = {}
            dynamic: list[str] = []
            for attribute in opening.named_children:
                if attribute.type != "jsx_attribute":
                    continue
                children = attribute.named_children
                if not children:
                    continue
                name_node = children[0]
                name = raw(name_node)
                if len(children) == 1:
                    static[name] = "true"
                    continue
                value_node = children[1]
                value = raw(value_node)
                if value_node.type == "string":
                    static[name] = value[1:-1]
                    continue
                literal = re.fullmatch(r"\{\s*(['\"])(.*?)\1\s*\}", value, re.S)
                if literal:
                    static[name] = literal.group(2)
                else:
                    dynamic.append(f"{name}={value}")
            return static, dynamic

        def visit(node: Any, parent_id: str | None) -> None:
            current_parent = parent_id
            opening = None
            if node.type == "jsx_element":
                opening = next(
                    (
                        child
                        for child in node.named_children
                        if child.type == "jsx_opening_element"
                    ),
                    None,
                )
            elif node.type == "jsx_self_closing_element":
                opening = node

            if opening is not None:
                name_node = opening.child_by_field_name("name")
                if name_node is None:
                    name_node = next(
                        (
                            child
                            for child in opening.named_children
                            if child.type
                            in {"identifier", "member_expression", "nested_identifier"}
                        ),
                        None,
                    )
                tag = raw(name_node) if name_node is not None else "UNKNOWN"
                attrs, dynamic = attributes(opening)
                component_name = attrs.get("componentName") or attrs.get("name")
                node_id = f"jsx:{node.start_byte}"
                component = Component(
                    node_id=node_id,
                    tag=tag,
                    component_name=component_name,
                    parent_id=parent_id,
                    attrs=attrs,
                    dynamic_attrs=dynamic,
                    line=node.start_point.row + 1,
                    column=node.start_point.column + 1,
                )
                self.components[node_id] = component
                if component_name:
                    self.by_name[component_name].append(node_id)
                if parent_id:
                    self.components[parent_id].children.append(node_id)
                current_parent = node_id

            for child in node.named_children:
                if child is not opening:
                    visit(child, current_parent)

        visit(tree.root_node, None)
        if not self.components:
            raise ValueError("No JSX components found; verify input and language.")

    def _section_value(self, section: str, component_name: str) -> Any:
        values = self.config.get(section, {})
        return values.get(component_name) if isinstance(values, Mapping) else None

    def _state(self, component_name: str) -> tuple[Any, bool]:
        state = self.config.get("state", {})
        if isinstance(state, Mapping) and component_name in state:
            return state[component_name], True
        return None, False

    def _label(self, component: Component) -> str | None:
        props = self._section_value("props", component.component_name or "")
        for source in (props, component.attrs):
            if isinstance(source, Mapping):
                for key in ("label", "title", "placeholder", "aria-label"):
                    value = source.get(key)
                    if isinstance(value, (str, int, float)):
                        return str(value)
        return None

    def _visibility(self, component: Component) -> str:
        props = self._section_value("props", component.component_name or "")
        visible = props.get("visible") if isinstance(props, Mapping) else None
        if isinstance(visible, bool):
            return "visible" if visible else "hidden"
        return "unknown"

    def _has_on_change(self, component_name: str) -> bool | None:
        actions = self.config.get("actions")
        events = self.config.get("events")
        configured = actions is not None or events is not None
        if isinstance(actions, list):
            for action in actions:
                if (
                    isinstance(action, Mapping)
                    and action.get("componentName") == component_name
                    and action.get("event") == "onChange"
                ):
                    return True
        if isinstance(actions, Mapping):
            action = actions.get(component_name)
            if isinstance(action, Mapping) and (
                action.get("event") == "onChange" or "onChange" in action
            ):
                return True
        if isinstance(events, Mapping):
            component_events = events.get(component_name)
            if isinstance(component_events, Mapping) and "onChange" in component_events:
                return component_events["onChange"] not in (None, False)
            on_change = events.get("onChange")
            if isinstance(on_change, Mapping) and component_name in on_change:
                return on_change[component_name] not in (None, False)
        return False if configured else None

    def _named_parent(self, component: Component) -> str | None:
        parent_id = component.parent_id
        while parent_id:
            parent = self.components[parent_id]
            if parent.component_name:
                return parent.component_name
            parent_id = parent.parent_id
        return None

    def _search_text(self, component: Component) -> str:
        ancestors: list[str] = []
        parent_id = component.parent_id
        while parent_id:
            parent = self.components[parent_id]
            ancestors.extend([parent.component_name or "", self._label(parent) or ""])
            parent_id = parent.parent_id
        return " ".join(
            value
            for value in [
                component.component_name or "",
                component.tag,
                self._label(component) or "",
                *ancestors,
            ]
            if value
        )
