"""Bounded plain-text renderer for EntityCollection tree display."""

from __future__ import annotations

import mammos_units as u
import numpy as np

from ._common import (
    _MAX_INLINE_CHARS,
    _STATIC_ELLIPSIS_CHILD,
    _STATIC_MAX_CHILDREN_PER_COLLECTION,
    _STATIC_MAX_DEPTH,
    _STATIC_MAX_TOTAL_NODES,
    _compact_value_text_spec,
    _EntityCollectionLike,
    _is_collection_like,
    _is_entity_like,
    _repr_with_fallback,
    _StaticTextRenderResult,
    _text_indent,
)


def _compact_leaf_text(value: object, preview_text: str, *, meta_text: str, summary_unit_text: str) -> str:
    """Render one bounded plain-text preview for a large supported leaf value."""
    if isinstance(value, u.Quantity):
        text = f"<Quantity [{preview_text}] {summary_unit_text}>"
    elif isinstance(value, np.ndarray):
        text = f"array([{preview_text}])"
    else:
        text = preview_text

    if meta_text:
        text = f"{text} ({meta_text})"
    return text


def _render_plain_text_leaf(value: object) -> str:
    """Render one bounded plain-text leaf value."""
    if _is_entity_like(value):
        value_text = _render_plain_text_leaf(value.value)
        args = [f"ontology_label={value.ontology_label!r}", f"value={value_text}"]
        unit_text = str(getattr(value, "unit", ""))
        if unit_text:
            args.append(f"unit={unit_text!r}")
        if value.description:
            args.append(f"description={value.description!r}")
        return f"{value.__class__.__name__}({', '.join(args)})"

    repr_value_text, repr_failed = _repr_with_fallback(value)
    compact_spec = None
    if isinstance(value, u.Quantity | np.ndarray | list | tuple | dict):
        compact_spec = _compact_value_text_spec(value)
    if compact_spec is None:
        return repr_value_text

    full_text = compact_spec.expanded_text if repr_failed else repr_value_text
    if len(full_text) <= _MAX_INLINE_CHARS:
        return repr_value_text

    return _compact_leaf_text(
        value,
        compact_spec.preview_text,
        meta_text=compact_spec.meta_text,
        summary_unit_text=compact_spec.summary_unit_text,
    )


def _render_static_text_branch(
    key: str,
    collection: _EntityCollectionLike,
    *,
    depth: int,
    remaining_nodes: int,
    indent_level: int,
) -> _StaticTextRenderResult:
    """Render one nested collection branch for the bounded text/plain fallback."""
    indent = _text_indent(indent_level)
    branch_prefix = f"{indent}{key}={collection.__class__.__name__}(\n"
    branch_suffix = f"\n{indent}),"

    if depth >= _STATIC_MAX_DEPTH:
        body_lines = []
        nodes_used = 1
        if collection.description:
            body_lines.append(f"{_text_indent(indent_level + 1)}description={collection.description!r},")
            nodes_used += 1
        body_lines.append(f"{_text_indent(indent_level + 1)}{_STATIC_ELLIPSIS_CHILD},")
        nodes_used += 1
        branch_body = "\n".join(body_lines)
        branch_text = f"{branch_prefix}{branch_body}{branch_suffix}"
        if nodes_used > remaining_nodes:
            return _StaticTextRenderResult(text="", nodes_used=0, complete=False, hit_global_limit=True)
        return _StaticTextRenderResult(text=branch_text, nodes_used=nodes_used, complete=False, hit_global_limit=False)

    if remaining_nodes <= 1:
        return _StaticTextRenderResult(text="", nodes_used=0, complete=False, hit_global_limit=True)

    child_result = _render_static_text_children(
        collection,
        depth=depth + 1,
        remaining_nodes=remaining_nodes - 1,
        indent_level=indent_level + 1,
    )
    branch_text = f"{branch_prefix}{child_result.text}{branch_suffix}"
    nodes_used = 1 + child_result.nodes_used
    if nodes_used > remaining_nodes:
        return _StaticTextRenderResult(text="", nodes_used=0, complete=False, hit_global_limit=True)
    return _StaticTextRenderResult(
        text=branch_text,
        nodes_used=nodes_used,
        complete=child_result.complete,
        hit_global_limit=child_result.hit_global_limit,
    )


def _render_static_text_children(
    collection: _EntityCollectionLike,
    *,
    depth: int,
    remaining_nodes: int,
    indent_level: int,
) -> _StaticTextRenderResult:
    """Render the children block for one collection in text/plain mode."""
    lines: list[str] = []
    nodes_used = 0
    nodes_left = remaining_nodes
    complete = True
    hit_global_limit = False
    hit_local_limit = False
    indent = _text_indent(indent_level)

    if collection.description:
        if nodes_left <= 0:
            return _StaticTextRenderResult(text="", nodes_used=0, complete=False, hit_global_limit=True)
        lines.append(f"{indent}description={collection.description!r},")
        nodes_used += 1
        nodes_left -= 1

    total_children = len(collection._entities)
    for child_index, (key, value) in enumerate(collection._entities.items()):
        has_more_siblings = child_index + 1 < total_children
        if child_index >= _STATIC_MAX_CHILDREN_PER_COLLECTION:
            complete = False
            hit_local_limit = True
            break
        if nodes_left <= 0:
            complete = False
            hit_global_limit = True
            break
        if nodes_left == 1:
            complete = False
            hit_global_limit = True
            break
        child_budget = nodes_left - 1 if has_more_siblings else nodes_left
        if child_budget <= 0:
            complete = False
            hit_global_limit = True
            break
        if _is_collection_like(value):
            item_result = _render_static_text_branch(
                key,
                value,
                depth=depth,
                remaining_nodes=child_budget,
                indent_level=indent_level,
            )
        else:
            item_result = _StaticTextRenderResult(
                text=f"{indent}{key}={_render_plain_text_leaf(value)},",
                nodes_used=1,
                complete=True,
                hit_global_limit=False,
            )

        if not item_result.text:
            complete = False
            hit_global_limit = hit_global_limit or item_result.hit_global_limit
            break

        lines.append(item_result.text)
        nodes_used += item_result.nodes_used
        nodes_left -= item_result.nodes_used
        if not item_result.complete:
            complete = False
            hit_global_limit = hit_global_limit or item_result.hit_global_limit

    if (hit_global_limit or hit_local_limit) and nodes_left > 0:
        lines.append(f"{indent}{_STATIC_ELLIPSIS_CHILD},")
        nodes_used += 1

    return _StaticTextRenderResult(
        text="\n".join(lines),
        nodes_used=nodes_used,
        complete=complete,
        hit_global_limit=hit_global_limit,
    )


def render_entity_collection_text(collection: _EntityCollectionLike) -> str:
    """Render the bounded text/plain fallback for EntityCollection."""
    child_result = _render_static_text_children(
        collection,
        depth=0,
        remaining_nodes=_STATIC_MAX_TOTAL_NODES - 1,
        indent_level=1,
    )
    if child_result.text:
        return f"{collection.__class__.__name__}(\n{child_result.text}\n)"
    return f"{collection.__class__.__name__}()"
