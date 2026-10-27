from __future__ import annotations

from dataclasses import dataclass

import tree_sitter_typescript
from tree_sitter import Language, Node, Parser, Query, QueryCursor

_COMPONENT_QUERY = r"""
((jsx_opening_element
  name: (_) @tag
  attribute: (jsx_attribute
    (property_identifier) @attribute
    [(string) @value (jsx_expression (string) @value)])) @element
 (#eq? @attribute "componentName"))

((jsx_self_closing_element
  name: (_) @tag
  attribute: (jsx_attribute
    (property_identifier) @attribute
    [(string) @value (jsx_expression (string) @value)])) @element
 (#eq? @attribute "componentName"))
"""

_LANGUAGE = Language(tree_sitter_typescript.language_tsx())
_QUERY = Query(_LANGUAGE, _COMPONENT_QUERY)


@dataclass(frozen=True)
class JSXComponent:
    name: str
    tag: str
    path: tuple[str, ...]


def parse_jsx(jsx: str) -> dict[str, JSXComponent]:
    """Capture every named JSX element and calculate its named ancestor path."""
    source = jsx.encode()
    tree = Parser(_LANGUAGE).parse(source)
    matches = [
        captures
        for _, captures in QueryCursor(_QUERY).matches(tree.root_node)
        if captures
    ]

    names_by_node: dict[tuple[int, int, str], str] = {}
    captured: list[tuple[Node, str, str]] = []
    for captures in matches:
        element = captures["element"][0]
        name = _text(captures["value"][0], source)[1:-1]
        tag = _text(captures["tag"][0], source)
        captured.append((element, name, tag))
        names_by_node[_key(element)] = name
        if element.type == "jsx_opening_element" and element.parent is not None:
            names_by_node[_key(element.parent)] = name

    return {
        name: JSXComponent(
            name=name,
            tag=tag,
            path=(*_ancestor_names(element, names_by_node), name),
        )
        for element, name, tag in captured
    }


def _ancestor_names(
    element: Node,
    names_by_node: dict[tuple[int, int, str], str],
) -> tuple[str, ...]:
    node = element.parent
    if element.type == "jsx_opening_element" and node is not None:
        node = node.parent
    names: list[str] = []
    while node is not None:
        name = names_by_node.get(_key(node))
        if name is not None:
            names.append(name)
        node = node.parent
    names.reverse()
    return tuple(names)


def _key(node: Node) -> tuple[int, int, str]:
    return node.start_byte, node.end_byte, node.type


def _text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode()
