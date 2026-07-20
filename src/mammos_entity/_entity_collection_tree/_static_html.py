"""Static HTML renderer for EntityCollection tree display."""

from __future__ import annotations

import importlib.resources
from functools import cache

from ._common import (
    _STATIC_ELLIPSIS_CHILD,
    _STATIC_MAX_CHILDREN_PER_COLLECTION,
    _STATIC_MAX_DEPTH,
    _STATIC_MAX_TOTAL_NODES,
    _STATIC_PREVIEW_NOTE,
    _EntityCollectionLike,
    _is_collection_like,
    _StaticRenderResult,
)
from ._html_helpers import (
    _render_branch_summary,
    _render_collection_description,
    _render_collection_note,
    _render_leaf_value_html,
    _render_root_collection_summary,
    _render_row,
    _render_static_preview_note,
)


def _render_static_branch(
    key: str, collection: _EntityCollectionLike, *, depth: int, remaining_nodes: int
) -> _StaticRenderResult:
    """Render one nested collection branch for static HTML fallback."""
    summary_prefix = f"<details class='branch-item branch-node'>{_render_branch_summary(key, collection)}"
    suffix = "</details>"

    if depth >= _STATIC_MAX_DEPTH:
        child_parts = []
        nodes_used = 1
        if collection.description:
            child_parts.append(_render_collection_description(collection.description))
            nodes_used += 1
        child_parts.append(_render_collection_note(_STATIC_ELLIPSIS_CHILD))
        nodes_used += 1
        branch_html = f"{summary_prefix}<div class='collection-children'>{''.join(child_parts)}</div>{suffix}"
        if nodes_used > remaining_nodes:
            return _StaticRenderResult(html="", nodes_used=0, complete=False, hit_global_limit=True)
        return _StaticRenderResult(html=branch_html, nodes_used=nodes_used, complete=False, hit_global_limit=False)

    if remaining_nodes <= 1:
        return _StaticRenderResult(html="", nodes_used=0, complete=False, hit_global_limit=True)

    child_result = _render_static_children(collection, depth=depth + 1, remaining_nodes=remaining_nodes - 1)
    branch_html = f"{summary_prefix}{child_result.html}{suffix}"
    nodes_used = 1 + child_result.nodes_used
    if nodes_used > remaining_nodes:
        return _StaticRenderResult(html="", nodes_used=0, complete=False, hit_global_limit=True)
    return _StaticRenderResult(
        html=branch_html,
        nodes_used=nodes_used,
        complete=child_result.complete,
        hit_global_limit=child_result.hit_global_limit,
    )


def _render_static_children(
    collection: _EntityCollectionLike, *, depth: int, remaining_nodes: int
) -> _StaticRenderResult:
    """Render the children block for one collection in static mode."""
    parts: list[str] = []
    nodes_used = 0
    nodes_left = remaining_nodes
    complete = True
    hit_global_limit = False
    hit_local_limit = False

    if collection.description:
        if nodes_left <= 0:
            return _StaticRenderResult(html="", nodes_used=0, complete=False, hit_global_limit=True)
        parts.append(_render_collection_description(collection.description))
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
            item_result = _render_static_branch(key, value, depth=depth, remaining_nodes=child_budget)
        else:
            item_result = _StaticRenderResult(
                html=_render_row(key, _render_leaf_value_html(value), row_class="leaf-row"),
                nodes_used=1,
                complete=True,
                hit_global_limit=False,
            )
        if not item_result.html:
            complete = False
            hit_global_limit = hit_global_limit or item_result.hit_global_limit
            break

        parts.append(item_result.html)
        nodes_used += item_result.nodes_used
        nodes_left -= item_result.nodes_used
        if not item_result.complete:
            complete = False
            hit_global_limit = hit_global_limit or item_result.hit_global_limit

    if (hit_global_limit or hit_local_limit) and nodes_left > 0:
        parts.append(_render_collection_note(_STATIC_ELLIPSIS_CHILD))
        nodes_used += 1

    children_html = f"<div class='collection-children'>{''.join(parts)}</div>" if parts else ""
    return _StaticRenderResult(
        html=children_html,
        nodes_used=nodes_used,
        complete=complete,
        hit_global_limit=hit_global_limit,
    )


@cache
def _tree_css() -> str:
    """Load the dedicated EntityCollection tree CSS once."""
    css = importlib.resources.files("mammos_entity._entity_collection_tree").joinpath("_styles.css")
    return f"<style>{css.read_text(encoding='utf-8')}</style>"


def render_entity_collection_html(collection: _EntityCollectionLike) -> str:
    """Render the bounded static HTML fallback for EntityCollection."""
    summary_html = _render_root_collection_summary(collection)
    outer_prefix = f"<details class='mammos-entity-collection root-node' open><summary>{summary_html}</summary>"
    child_result = _render_static_children(collection, depth=0, remaining_nodes=_STATIC_MAX_TOTAL_NODES - 1)
    preview_note_html = _render_static_preview_note(_STATIC_PREVIEW_NOTE) if not child_result.complete else ""
    return f"{_tree_css()}{outer_prefix}{child_result.html}{preview_note_html}</details>"
