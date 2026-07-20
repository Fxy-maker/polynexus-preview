"""Qt-independent layer-tree data for the chart editor object surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class LayerTreeNode:
    node_id: str
    role: str
    label: str
    object_id: str = ""
    group_id: str = ""
    locked: bool = False
    visible: bool = True
    children: tuple["LayerTreeNode", ...] = ()


def _default_object_label(payload: dict) -> str:
    kind = str(payload.get("type", "object") or "object").replace("_", " ").title()
    name = str(payload.get("name", "") or "").strip()
    return kind if not name or name.casefold() == kind.casefold() else f"{kind}: {name}"


def _matches(label: str, query: str) -> bool:
    return not query or query.casefold() in label.casefold()


def build_layer_tree(
    objects: Iterable[dict],
    *,
    query: str = "",
    label_for: Callable[[dict], str] | None = None,
) -> tuple[LayerTreeNode, ...]:
    """Build stable group/object nodes while retaining object ids.

    Group membership is represented by the existing ``group_id`` field. The
    first appearance of a group determines its position, and filtering keeps
    a matching group ancestor visible with all of its children.
    """

    label_builder = label_for or _default_object_label
    normalized_query = str(query or "").strip().casefold()
    grouped: dict[str, list[LayerTreeNode]] = {}
    group_order: list[str] = []
    roots: list[LayerTreeNode] = []
    for payload in objects:
        if not isinstance(payload, dict):
            continue
        object_id = str(payload.get("id", "") or "").strip()
        if not object_id:
            continue
        label = str(label_builder(payload) or object_id)
        child = LayerTreeNode(
            node_id=object_id,
            role="object",
            label=label,
            object_id=object_id,
            group_id=str(payload.get("group_id", "") or "").strip(),
            locked=bool(payload.get("locked", False)),
            visible=payload.get("visible", True) is not False,
        )
        group_id = child.group_id
        if not group_id:
            if _matches(f"{object_id} {label} {payload.get('type', '')}", normalized_query):
                roots.append(child)
            continue
        if group_id not in grouped:
            grouped[group_id] = []
            group_order.append(group_id)
        grouped[group_id].append(child)

    group_nodes: list[LayerTreeNode] = []
    for group_id in group_order:
        children = grouped[group_id]
        group_label = f"Group: {group_id}"
        if _matches(group_label, normalized_query):
            visible_children = tuple(children)
        else:
            visible_children = tuple(
                child
                for child in children
                if _matches(f"{child.object_id} {child.label}", normalized_query)
            )
        if not visible_children:
            continue
        group_nodes.append(
            LayerTreeNode(
                node_id=f"group:{group_id}",
                role="group",
                label=group_label,
                group_id=group_id,
                children=visible_children,
            )
        )

    return tuple(group_nodes + roots)


__all__ = ["LayerTreeNode", "build_layer_tree"]
