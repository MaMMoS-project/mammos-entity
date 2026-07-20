"""Shared HTML helpers for EntityCollection tree representations."""

from __future__ import annotations

import html
from dataclasses import dataclass

import mammos_units as u
import numpy as np

from ._common import (
    _MAX_INLINE_CHARS,
    _CollapsibleTextSpec,
    _collection_preview,
    _compact_value_text_spec,
    _format_array_repr_expanded,
    _format_array_repr_summary,
    _is_entity_like,
    _repr_with_fallback,
    _truncate_preview_text,
)

_TREE_META_SEPARATOR = "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
_COMPACT_DETAILS_CSS_CLASSES = "mammos-entity-inline mammos-compact-value lazy-leaf-details"


@dataclass(frozen=True, slots=True)
class _EntityRenderState:
    """Precomputed bits needed to render an entity-like value."""

    label_html: str
    entity_value: object
    value_text: str
    compact_value_text: str
    description_html: str
    unit_text: str
    has_shape: bool
    shape_meta_text: str
    show_details: bool


@dataclass(frozen=True, slots=True)
class _LeafRenderState:
    """Precomputed state for non-entity leaf rendering."""

    repr_value_text: str
    repr_failed: bool
    compact_spec: _CollapsibleTextSpec | None
    use_compact: bool


def _format_html_text(text: str, *, preserve_spaces: bool = False) -> str:
    """Escape plain text for safe inline HTML display."""
    escaped = html.escape(text).replace("\n", "<br>")
    if preserve_spaces:
        escaped = escaped.replace(" ", "&nbsp;")
    return escaped


def _render_meta_suffix(text: str) -> str:
    """Render optional metadata using the shared muted suffix style."""
    if not text:
        return ""
    return f"{_TREE_META_SEPARATOR}<span class='entity-meta'>{_format_html_text(text, preserve_spaces=True)}</span>"


def _render_summary_content(spec: _CollapsibleTextSpec) -> str:
    """Render the shared summary text used by collapsible value previews."""
    summary_unit_html = ""
    if spec.summary_unit_text:
        summary_unit_html = f"<span>{_format_html_text(f' {spec.summary_unit_text}', preserve_spaces=True)}</span>"
    return (
        "<span>"
        f"<span>{_format_html_text(spec.preview_text, preserve_spaces=True)}{summary_unit_html}</span>"
        f"{_render_meta_suffix(spec.meta_text)}"
        "</span>"
    )


def _render_leaf_details(
    spec: _CollapsibleTextSpec,
    *,
    css_classes: str,
    node_id: str | None = None,
    open_details: bool = False,
    include_body: bool = True,
) -> str:
    """Render a ``details`` block for a long value preview."""
    lazy_attrs = ""
    if node_id is not None:
        lazy_attrs = (
            f" data-lazy-id='{node_id}' data-lazy-patch='replace-self' "
            "data-lazy-cursor='0' data-lazy-loading='false' data-lazy-done='false'"
        )
    body_html = ""
    if include_body:
        body_html = (
            "<div class='entity-expanded-details'>"
            "<span class='entity-full-value'>"
            f"{html.escape(spec.expanded_text)}"
            f"{html.escape(spec.expanded_suffix_text)}"
            "</span>"
            "</div>"
        )
    open_attr = " open" if open_details else ""
    return (
        f"<details class='{css_classes}'{open_attr}{lazy_attrs}>"
        "<summary class='lazy-leaf-summary'>"
        "<span class='entity-toggle'>[+]</span>"
        "<span class='entity-toggle'>[−]</span>"
        f"{_render_summary_content(spec)}"
        "</summary>"
        f"{body_html}"
        "</details>"
    )


def _render_root_collection_summary(collection) -> str:
    """Render the root collection summary shown next to the disclosure marker."""
    preview_html = _format_html_text(_collection_preview(collection), preserve_spaces=True)
    return (
        f"<span class='collection-title'>{_format_html_text(collection.__class__.__name__)}</span>"
        f"<span class='summary-preview'>{preview_html}</span>"
    )


def _render_text_block(css_class: str, text: str, *, preserve_spaces: bool = False) -> str:
    """Render one simple text block with a dedicated CSS class."""
    return f"<div class='{css_class}'>{_format_html_text(text, preserve_spaces=preserve_spaces)}</div>"


def _render_collection_description(description: str) -> str:
    """Render the optional description item shown above collection members."""
    return _render_text_block("branch-item collection-description", description)


def _render_collection_note(note: str) -> str:
    """Render a muted collection note item."""
    return _render_text_block("branch-item collection-note", note, preserve_spaces=True)


def _render_static_preview_note(note: str) -> str:
    """Render the static preview warning below the tree body."""
    return _render_text_block("static-preview-note", note, preserve_spaces=True)


def _render_widget_collection_node(summary_html: str, node_id: str, description: str, *, root: bool) -> str:
    """Render the shared lazy collection node markup used by root and nested branches."""
    description_html = _render_collection_description(description) if description else ""
    lazy_attrs = (
        f"data-lazy-id='{node_id}' data-lazy-patch='append-children' "
        "data-lazy-cursor='0' data-lazy-loading='false' "
        "data-lazy-loaded='false' data-lazy-done='false' "
        f"data-initial-children-html='{html.escape(description_html, quote=True)}'"
    )
    css_class = "mammos-entity-collection root-node" if root else "branch-item branch-node"
    open_attr = " open" if root else ""
    return (
        f"<details class='{css_class}'{open_attr} {lazy_attrs}>"
        f"{summary_html}"
        f"<div class='collection-children'>{description_html}</div>"
        "<div class='collection-footer'></div>"
        "</details>"
    )


def _render_widget_root(collection, node_id: str) -> str:
    """Render the root widget container without eagerly rendering any members."""
    return _render_widget_collection_node(
        f"<summary>{_render_root_collection_summary(collection)}</summary>",
        node_id,
        collection.description,
        root=True,
    )


def _render_collection_controls(node_id: str, *, next_cursor: int, total: int, page_size: int) -> str:
    """Render per-node paging controls for wide collections."""
    if next_cursor >= total:
        return ""
    remaining = total - next_cursor
    next_count = min(page_size, remaining)
    return (
        "<div class='collection-controls'>"
        f"<button type='button' class='collection-control' data-lazy-action='next' data-lazy-target-id='{node_id}'>"
        f"Load next {next_count}"
        "</button>"
        f"<button type='button' class='collection-control' data-lazy-action='all' data-lazy-target-id='{node_id}'>"
        f"Load remaining {remaining}"
        "</button>"
        "</div>"
    )


def _render_row(key: str, value_html: str, *, row_class: str = "") -> str:
    """Render a single key/value row."""
    classes = "branch-item entity-row"
    if row_class:
        classes = f"{classes} {row_class}"
    return (
        f"<div class='{classes}'>"
        f"<div class='entity-key'>{_format_html_text(key, preserve_spaces=True)}</div>"
        f"<div class='entity-value'>{value_html}</div>"
        "</div>"
    )


def _entity_description_inline_html(description: object) -> str:
    """Render an inline entity description."""
    if not isinstance(description, str) or not description:
        return ""
    return f"<em class='entity-description'>{_format_html_text(description)}</em>"


def _entity_render_state(value: object) -> _EntityRenderState:
    """Collect the display state needed for rendering an entity-like value."""
    entity_value = value.value
    compact_value_text = " ".join(str(entity_value).split())
    try:
        unit_text = str(value.unit)
    except Exception:
        unit_text = ""
    shape = getattr(entity_value, "shape", ())
    return _EntityRenderState(
        label_html=f"<span class='entity-label'>{_format_html_text(str(value.ontology_label))}</span>",
        entity_value=entity_value,
        value_text=str(entity_value),
        compact_value_text=compact_value_text,
        description_html=_entity_description_inline_html(getattr(value, "description", "")),
        unit_text=unit_text,
        has_shape=shape not in [(), None],
        shape_meta_text=f"shape={shape}" if shape not in [(), None] else "",
        show_details=len(f"{compact_value_text} {unit_text}".strip()) > _MAX_INLINE_CHARS,
    )


def _entity_uses_details(state: _EntityRenderState) -> bool:
    """Return true when an entity should use the expandable details rendering."""
    return state.show_details or "..." in state.value_text


def _entity_requires_lazy_details(value: object) -> bool:
    """Return true when widget mode should defer the full entity fragment."""
    return _entity_uses_details(_entity_render_state(value))


def _entity_collapsible_spec(state: _EntityRenderState) -> _CollapsibleTextSpec:
    """Build the collapsible preview spec used by long entity values."""
    if state.unit_text:
        return _CollapsibleTextSpec(
            preview_text=_format_array_repr_summary(state.entity_value),
            expanded_text=_format_array_repr_expanded(state.entity_value),
            summary_unit_text=state.unit_text,
        )
    return _CollapsibleTextSpec(
        preview_text=_truncate_preview_text(state.compact_value_text),
        expanded_text=state.value_text,
    )


def _render_entity_detail_wrapper(state: _EntityRenderState, details_html: str) -> str:
    """Render the shared entity wrapper used around expandable details."""
    return (
        "<div class='mammos-entity-inline'>"
        f"{state.label_html}{_render_meta_suffix(state.shape_meta_text)}"
        f"{'<br>' if state.description_html else ''}{state.description_html}"
        "<br>"
        f"{details_html}"
        "</div>"
    )


def _render_entity_details_html(
    state: _EntityRenderState, *, node_id: str | None = None, open_details: bool = False, include_body: bool = True
) -> str:
    """Render the shared details block used for long entity values."""
    return _render_leaf_details(
        _entity_collapsible_spec(state),
        css_classes="lazy-leaf-details",
        node_id=node_id,
        open_details=open_details,
        include_body=include_body,
    )


def _render_lazy_entity_value_html(value: object, entity_id: str) -> str:
    """Render the collapsed widget preview for an entity with lazy details."""
    state = _entity_render_state(value)
    details_html = _render_entity_details_html(state, node_id=entity_id, include_body=False)
    return _render_entity_detail_wrapper(state, details_html)


def _render_expanded_entity_value_html(value: object) -> str:
    """Render an entity-like value in its expanded state for widget replacement."""
    return _render_entity_details_html(_entity_render_state(value), open_details=True)


def _render_entity_value_html(value: object) -> str:
    """Render mammos Entity-like objects without delegating to their own HTML repr."""
    state = _entity_render_state(value)
    if _entity_uses_details(state):
        return _render_entity_detail_wrapper(state, _render_entity_details_html(state))
    if state.unit_text:
        compact_shape_html = ""
        if state.has_shape and getattr(state.entity_value, "size", 0) > 3:
            compact_shape_html = _render_meta_suffix(state.shape_meta_text)
        value_html = _format_html_text(state.compact_value_text, preserve_spaces=True)
        unit_html = _format_html_text(f" {state.unit_text}", preserve_spaces=True)
        return (
            "<samp class='mammos-entity-inline'>"
            f"{state.label_html}"
            f"{_TREE_META_SEPARATOR}"
            f"<span>{value_html}{unit_html}</span>"
            f"{compact_shape_html}"
            f"{'<br>' if state.description_html else ''}{state.description_html}"
            "</samp>"
        )
    return (
        "<samp class='mammos-entity-inline'>"
        f"{state.label_html}"
        f"{_TREE_META_SEPARATOR}"
        f"<span>{_format_html_text(state.value_text)}</span>"
        f"{'<br>' if state.description_html else ''}{state.description_html}"
        "</samp>"
    )


def _leaf_render_state(value: object) -> _LeafRenderState:
    """Collect shared rendering state for a non-entity leaf value."""
    repr_value_text, repr_failed = _repr_with_fallback(value)
    compact_spec = None
    use_compact = False
    if isinstance(value, u.Quantity | np.ndarray | list | tuple | dict):
        compact_spec = _compact_value_text_spec(value)
        if compact_spec is not None:
            use_compact = len(compact_spec.expanded_text if repr_failed else repr_value_text) > _MAX_INLINE_CHARS
    return _LeafRenderState(
        repr_value_text=repr_value_text,
        repr_failed=repr_failed,
        compact_spec=compact_spec,
        use_compact=use_compact,
    )


def _leaf_requires_lazy_details(value: object) -> bool:
    """Return true when widget mode should defer a long special leaf value."""
    state = _leaf_render_state(value)
    return state.compact_spec is not None and state.use_compact


def _render_expanded_leaf_value_html(value: object) -> str:
    """Render the fully expanded HTML for a lazy non-entity leaf value."""
    state = _leaf_render_state(value)
    if state.compact_spec is None or not state.use_compact:
        raise TypeError(f"Value {value!r} does not use lazy compact rendering.")
    return _render_leaf_details(state.compact_spec, css_classes=_COMPACT_DETAILS_CSS_CLASSES, open_details=True)


def _render_leaf_value_html(value: object) -> str:
    """Render a non-collection leaf value."""
    if _is_entity_like(value):
        fragment = getattr(value, "_repr_html_fragment_", None)
        return fragment() if callable(fragment) else _render_entity_value_html(value)

    state = _leaf_render_state(value)
    if state.compact_spec is not None:
        if state.use_compact:
            return _render_leaf_details(state.compact_spec, css_classes=_COMPACT_DETAILS_CSS_CLASSES)
        if state.repr_failed:
            return _format_html_text(state.compact_spec.expanded_text, preserve_spaces=True)
    return _format_html_text(state.repr_value_text, preserve_spaces=True)


def _render_branch_summary(key: str, collection) -> str:
    """Render the shared summary markup for a nested collection branch."""
    return (
        "<summary>"
        f"<span>{_format_html_text(key, preserve_spaces=True)}</span>"
        "<span class='summary-preview'>"
        f"{_format_html_text(collection.__class__.__name__)}"
        f"&nbsp;·&nbsp;{_format_html_text(_collection_preview(collection), preserve_spaces=True)}"
        "</span>"
        "</summary>"
    )


def _render_widget_branch(key: str, collection, node_id: str) -> str:
    """Render a lazy branch placeholder for widget mode."""
    return _render_widget_collection_node(
        _render_branch_summary(key, collection),
        node_id,
        collection.description,
        root=False,
    )
