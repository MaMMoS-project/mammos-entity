"""Private tree-view helpers for EntityCollection notebook display."""

from __future__ import annotations

import html
import importlib.resources
import itertools
import pprint
import reprlib
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Protocol

import mammos_units as u
import numpy as np

if TYPE_CHECKING:
    import collections.abc


_SUMMARY_EDGE_ITEMS = 3
_EXPANDED_THRESHOLD = 100
_MAX_INLINE_CHARS = 80
_DEFAULT_WIDGET_PAGE_SIZE = 50
_STATIC_MAX_DEPTH = 4
_STATIC_MAX_CHILDREN_PER_COLLECTION = 20
_STATIC_MAX_TOTAL_NODES = 250
_STATIC_ELLIPSIS_CHILD = "..."
_STATIC_PREVIEW_NOTE = "Static preview truncated."
_TREE_META_SEPARATOR = "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
_COMPACT_DETAILS_CSS_CLASSES = "mammos-entity-inline mammos-compact-value lazy-leaf-details"
_TEXT_INDENT = " " * 4


class _EntityCollectionLike(Protocol):
    """Internal protocol for EntityCollection and subclasses."""

    description: str
    _entities: dict[str, object]

    def __iter__(self) -> collections.abc.Iterator[tuple[str, object]]: ...

    def __len__(self) -> int: ...


@dataclass(frozen=True, slots=True)
class _CollapsibleTextSpec:
    """Text fragments needed to render a collapsible value preview."""

    preview_text: str
    expanded_text: str
    summary_unit_text: str = ""
    meta_text: str = ""
    expanded_suffix_text: str = ""


@dataclass(frozen=True, slots=True)
class _StaticRenderResult:
    """A rendered static subtree together with the number of rendered nodes."""

    html: str
    nodes_used: int
    complete: bool
    hit_global_limit: bool


@dataclass(frozen=True, slots=True)
class _StaticTextRenderResult:
    """A rendered static text subtree together with the number of rendered nodes."""

    text: str
    nodes_used: int
    complete: bool
    hit_global_limit: bool


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


def _compact_repr_whitespace(text: str) -> str:
    """Collapse separator whitespace while preserving spaces inside quoted reprs."""
    compact: list[str] = []
    quote = ""
    escaped = False
    for char in text:
        if quote:
            compact.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue

        if char in {"'", '"'}:
            quote = char
            compact.append(char)
        elif char.isspace():
            if compact and compact[-1] != " ":
                compact.append(" ")
        else:
            compact.append(char)
    return "".join(compact).strip()


def _format_array_repr_summary(value: np.typing.ArrayLike) -> str:
    """Format a flattened preview for array values."""
    flattened = np.ravel(value)
    if flattened.size <= 2 * _SUMMARY_EDGE_ITEMS:
        parts = [flattened]
    else:
        parts = [flattened[:_SUMMARY_EDGE_ITEMS], flattened[-_SUMMARY_EDGE_ITEMS:]]

    formatted_parts = []
    for part in parts:
        text = np.array2string(part, max_line_width=10_000)
        if text.startswith("[") and text.endswith("]"):
            text = text[1:-1]
        formatted_parts.append(_compact_repr_whitespace(text))

    if len(formatted_parts) == 1:
        return formatted_parts[0]
    head, tail = formatted_parts
    return f"{head} ... {tail}"


def _array_repr_expanded_edgeitems(value: np.typing.ArrayLike) -> int:
    """Choose NumPy edgeitems for a bounded expanded array repr."""
    array = np.asarray(value)
    if array.ndim <= 1:
        return _EXPANDED_THRESHOLD // 2
    return max(1, int((_EXPANDED_THRESHOLD ** (1 / array.ndim)) / 2))


def _format_array_repr_expanded(value: np.typing.ArrayLike) -> str:
    """Format a bounded expanded representation for array values."""
    array = np.asarray(value)
    with np.printoptions(threshold=_EXPANDED_THRESHOLD, edgeitems=_array_repr_expanded_edgeitems(array)):
        return repr(array)


class _ReprEllipsis:
    """Sentinel rendering as ``...`` inside pprint-based container reprs."""

    def __repr__(self) -> str:
        return "..."


_REPR_ELLIPSIS = _ReprEllipsis()


def _format_repr_summary(
    items: list[object], opener: str, closer: str, format_item: collections.abc.Callable[[object], str] | None = None
) -> str:
    """Generic head/tail preview for a container with ``opener``/``closer`` delimiters."""
    repr_fn = reprlib.repr if format_item is None else format_item

    if len(items) <= 2 * _SUMMARY_EDGE_ITEMS:
        elements = [repr_fn(item) for item in items]
    else:
        elements = [
            *(repr_fn(item) for item in items[:_SUMMARY_EDGE_ITEMS]),
            "...",
            *(repr_fn(item) for item in items[-_SUMMARY_EDGE_ITEMS:]),
        ]
    return f"{opener}{', '.join(elements)}{closer}"


def _format_quantity_repr_expanded(value: u.Quantity) -> str:
    """Format a bounded expanded representation for array-valued quantities."""
    with np.printoptions(threshold=_EXPANDED_THRESHOLD, edgeitems=_array_repr_expanded_edgeitems(value.value)):
        return repr(value)


def _format_sequence_repr_summary(value: list | tuple) -> str:
    """Format a compact head/tail preview for Python list and tuple values."""
    opener, closer = ("[", "]") if isinstance(value, list) else ("(", ")")
    return _format_repr_summary(list(value), opener, closer)


def _format_sequence_repr_expanded(value: list | tuple) -> str:
    """Format a wrapped, bounded expanded representation for list/tuple values."""
    edge_items = _EXPANDED_THRESHOLD // 2
    if len(value) <= _EXPANDED_THRESHOLD:
        truncated = list(value) if isinstance(value, list) else tuple(value)
    elif isinstance(value, list):
        truncated = [*value[:edge_items], _REPR_ELLIPSIS, *value[-edge_items:]]
    else:
        truncated = (*value[:edge_items], _REPR_ELLIPSIS, *value[-edge_items:])
    return pprint.pformat(truncated, width=88, compact=True, sort_dicts=False)


def _format_dict_repr_summary(value: dict[object, object]) -> str:
    """Format a compact head/tail preview for Python dict values."""

    def format_item(item: tuple[object, object]) -> str:
        key, item_value = item
        return f"{reprlib.repr(key)}: {reprlib.repr(item_value)}"

    return _format_repr_summary(list(value.items()), "{", "}", format_item)


def _format_dict_repr_expanded(value: dict[object, object]) -> str:
    """Format a wrapped, bounded expanded representation for Python dict values."""
    edge_items = _EXPANDED_THRESHOLD // 2
    items = list(value.items())
    if len(items) <= _EXPANDED_THRESHOLD:
        truncated_items = items
    else:
        truncated_items = [*items[:edge_items], (_REPR_ELLIPSIS, _REPR_ELLIPSIS), *items[-edge_items:]]
    return pprint.pformat(dict(truncated_items), width=88, compact=True, sort_dicts=False)


def _truncate_preview_text(text: str, max_inline_chars: int = _MAX_INLINE_CHARS) -> str:
    """Trim long preview text while reserving space for an ellipsis."""
    if len(text) <= max_inline_chars:
        return text
    preview_limit = max_inline_chars - len("...")
    return f"{text[:preview_limit].rstrip()}..."


def _compact_value_text_spec(
    value: u.Quantity | np.typing.ArrayLike | list | tuple | dict,
) -> _CollapsibleTextSpec | None:
    """Return the compact preview spec for supported long collection values."""
    shape = getattr(value, "shape", ())
    if isinstance(value, u.Quantity) and shape not in [(), None]:
        return _CollapsibleTextSpec(
            preview_text=_format_array_repr_summary(value.value),
            expanded_text=_format_quantity_repr_expanded(value),
            summary_unit_text=str(value.unit),
            meta_text=f"shape={shape}",
        )
    if isinstance(value, np.ndarray):
        return _CollapsibleTextSpec(
            preview_text=_format_array_repr_summary(value),
            expanded_text=_format_array_repr_expanded(value),
            meta_text=f"shape={value.shape}",
        )
    if isinstance(value, list | tuple):
        return _CollapsibleTextSpec(
            preview_text=_format_sequence_repr_summary(value),
            expanded_text=_format_sequence_repr_expanded(value),
            meta_text=f"len={len(value)}",
        )
    if isinstance(value, dict):
        return _CollapsibleTextSpec(
            preview_text=_format_dict_repr_summary(value),
            expanded_text=_format_dict_repr_expanded(value),
            meta_text=f"len={len(value)}",
        )
    return None


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
    open_attr = " open" if open_details else ""
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


def _is_collection_like(value: object) -> bool:
    """Return true for EntityCollection instances and subclasses."""
    entities = getattr(value, "_entities", None)
    return isinstance(entities, dict) and hasattr(value, "description")


def _collection_preview(collection: _EntityCollectionLike) -> str:
    """Build the muted count/keys preview for a collection summary."""
    count = len(collection._entities)
    item_label = "item" if count == 1 else "items"
    preview_keys = list(itertools.islice(collection._entities, 3))
    preview_text = ", ".join(preview_keys)
    if count > 3:
        preview_text = f"{preview_text}, ..." if preview_text else "..."
    return f"{count} {item_label}" if not preview_text else f"{count} {item_label} · {preview_text}"


def _render_root_collection_summary(collection: _EntityCollectionLike) -> str:
    """Render the root collection summary shown next to the disclosure marker."""
    preview_html = _format_html_text(_collection_preview(collection), preserve_spaces=True)
    return (
        f"<span class='collection-title'>{_format_html_text(collection.__class__.__name__)}</span>"
        f"<span class='summary-preview'>{preview_html}</span>"
    )


def _repr_with_fallback(value: object) -> tuple[str, bool]:
    """Return ``repr(value)`` and whether the normal repr path failed."""
    try:
        return repr(value), False
    except Exception:
        return object.__repr__(value), True


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
    initial_children_html = html.escape(description_html, quote=True)
    lazy_attrs = (
        f"data-lazy-id='{node_id}' data-lazy-patch='append-children' "
        "data-lazy-cursor='0' data-lazy-loading='false' "
        "data-lazy-loaded='false' data-lazy-done='false' "
        f"data-initial-children-html='{initial_children_html}'"
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


def _is_entity_like(value: object) -> bool:
    """Return true for mammos Entity-like objects without importing their HTML reprs."""
    return all(hasattr(value, attribute) for attribute in ("ontology_label", "value", "description"))


def _entity_description_inline_html(description: object) -> str:
    """Render an inline entity description."""
    if not isinstance(description, str) or not description:
        return ""
    return f"<em class='entity-description'>{_format_html_text(description)}</em>"


def _entity_render_state(value: object) -> _EntityRenderState:
    """Collect the display state needed for rendering an entity-like value."""
    ontology_label = _format_html_text(str(value.ontology_label))
    label_html = f"<span class='entity-label'>{ontology_label}</span>"
    entity_value = value.value
    value_text = str(entity_value)
    compact_value_text = " ".join(value_text.split())
    description_html = _entity_description_inline_html(getattr(value, "description", ""))

    try:
        unit_text = str(value.unit)
    except Exception:
        unit_text = ""

    shape = getattr(entity_value, "shape", ())
    has_shape = shape not in [(), None]
    shape_meta_text = f"shape={shape}" if has_shape else ""
    show_details = len(f"{compact_value_text} {unit_text}".strip()) > _MAX_INLINE_CHARS
    return _EntityRenderState(
        label_html=label_html,
        entity_value=entity_value,
        value_text=value_text,
        compact_value_text=compact_value_text,
        description_html=description_html,
        unit_text=unit_text,
        has_shape=has_shape,
        shape_meta_text=shape_meta_text,
        show_details=show_details,
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
        preview_text=_truncate_preview_text(state.compact_value_text), expanded_text=state.value_text
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
    return _render_entity_detail_wrapper(
        state, _render_entity_details_html(state, node_id=entity_id, include_body=False)
    )


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
        unit_html = _format_html_text(f" {state.unit_text}", preserve_spaces=True) if state.unit_text else ""
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
            compact_source_text = compact_spec.expanded_text if repr_failed else repr_value_text
            use_compact = len(compact_source_text) > _MAX_INLINE_CHARS

    return _LeafRenderState(
        repr_value_text=repr_value_text, repr_failed=repr_failed, compact_spec=compact_spec, use_compact=use_compact
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
        if callable(fragment):
            return fragment()
        return _render_entity_value_html(value)

    state = _leaf_render_state(value)
    if state.compact_spec is not None:
        if state.use_compact:
            return _render_leaf_details(state.compact_spec, css_classes=_COMPACT_DETAILS_CSS_CLASSES)
        if state.repr_failed:
            return _format_html_text(state.compact_spec.expanded_text, preserve_spaces=True)

    return _format_html_text(state.repr_value_text, preserve_spaces=True)


def _text_indent(level: int) -> str:
    """Return the shared indentation prefix used by text/plain tree rendering."""
    return _TEXT_INDENT * level


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
        branch_text = f"{branch_prefix}{chr(10).join(body_lines)}{branch_suffix}"
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
            item_text = f"{indent}{key}={_repr_with_fallback(value)[0]},"
            item_result = _StaticTextRenderResult(
                text=item_text,
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


def _render_branch_summary(key: str, collection: _EntityCollectionLike) -> str:
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


def _render_widget_branch(key: str, collection: _EntityCollectionLike, node_id: str) -> str:
    """Render a lazy branch placeholder for widget mode."""
    return _render_widget_collection_node(
        _render_branch_summary(key, collection),
        node_id,
        collection.description,
        root=False,
    )


def _render_widget_root(collection: _EntityCollectionLike, node_id: str) -> str:
    """Render the root widget container without eagerly rendering any members."""
    return _render_widget_collection_node(
        f"<summary>{_render_root_collection_summary(collection)}</summary>",
        node_id,
        collection.description,
        root=True,
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
            description_html = _render_collection_description(collection.description)
            child_parts.append(description_html)
            nodes_used += 1
        child_parts.append(_render_collection_note(_STATIC_ELLIPSIS_CHILD))
        nodes_used += 1
        children_html = f"<div class='collection-children'>{''.join(child_parts)}</div>"
        branch_html = f"{summary_prefix}{children_html}{suffix}"
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
    truncation_note_html = _render_collection_note(_STATIC_ELLIPSIS_CHILD)

    if collection.description:
        description_html = _render_collection_description(collection.description)
        if nodes_left <= 0:
            return _StaticRenderResult(html="", nodes_used=0, complete=False, hit_global_limit=True)
        parts.append(description_html)
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
            row_html = _render_row(key, _render_leaf_value_html(value), row_class="leaf-row")
            if child_budget <= 0:
                item_result = _StaticRenderResult(html="", nodes_used=0, complete=False, hit_global_limit=True)
            else:
                item_result = _StaticRenderResult(html=row_html, nodes_used=1, complete=True, hit_global_limit=False)

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
        parts.append(truncation_note_html)
        nodes_used += 1

    children_html = f"<div class='collection-children'>{''.join(parts)}</div>" if parts else ""
    return _StaticRenderResult(
        html=children_html, nodes_used=nodes_used, complete=complete, hit_global_limit=hit_global_limit
    )


class EntityCollectionTreeSession:
    """Stateful lazy renderer used by the anywidget frontend."""

    def __init__(self, collection: _EntityCollectionLike, *, page_size: int = _DEFAULT_WIDGET_PAGE_SIZE):
        self._root_collection = collection
        self._page_size = page_size
        self._root_node_id = "lazy-node-0"

    @property
    def root_node_id(self) -> str:
        """Stable node id for the root collection."""
        return self._root_node_id

    def _collection_child_node_id(self, path: tuple[int, ...]) -> str:
        suffix = "".join(f"-collection-{index}" for index in path)
        return f"{self._root_node_id}{suffix}"

    def _replace_child_node_id(self, path: tuple[int, ...]) -> str:
        if not path:
            raise KeyError("Leaf paths must contain at least one index.")
        collection_suffix = "".join(f"-collection-{index}" for index in path[:-1])
        return f"{self._root_node_id}{collection_suffix}-leaf-{path[-1]}"

    def _decode_node_id(self, node_id: str) -> tuple[str, tuple[int, ...]]:
        if node_id == self._root_node_id:
            return "append-children", ()
        if not node_id.startswith(f"{self._root_node_id}-"):
            raise KeyError(f"Unknown lazy node id: {node_id}")

        tokens = node_id[len(self._root_node_id) + 1 :].split("-")
        if len(tokens) % 2 != 0:
            raise KeyError(f"Malformed lazy node id: {node_id}")

        path: list[int] = []
        patch = "append-children"
        for position in range(0, len(tokens), 2):
            kind = tokens[position]
            try:
                index = int(tokens[position + 1])
            except ValueError as exc:
                raise KeyError(f"Malformed lazy node id: {node_id}") from exc
            if kind == "collection":
                if patch != "append-children":
                    raise KeyError(f"Malformed lazy node id: {node_id}")
                path.append(index)
                continue
            if kind == "leaf" and position == len(tokens) - 2:
                patch = "replace-self"
                path.append(index)
                continue
            raise KeyError(f"Malformed lazy node id: {node_id}")

        return patch, tuple(path)

    def _collection_item_at(self, collection: _EntityCollectionLike, index: int) -> tuple[str, object]:
        try:
            return next(itertools.islice(collection._entities.items(), index, None))
        except StopIteration as exc:
            raise KeyError(f"Collection index {index} is out of range.") from exc

    def _resolve_collection(self, path: tuple[int, ...]) -> _EntityCollectionLike:
        collection = self._root_collection
        for index in path:
            _, value = self._collection_item_at(collection, index)
            if not _is_collection_like(value):
                raise KeyError(f"Path {path!r} does not resolve to a collection.")
            collection = value
        return collection

    def _resolve_value(self, path: tuple[int, ...]) -> object:
        if not path:
            raise KeyError("Leaf paths must contain at least one index.")
        collection = self._resolve_collection(path[:-1])
        _, value = self._collection_item_at(collection, path[-1])
        return value

    def render_root_html(self) -> str:
        """Render the root widget container."""
        return _render_widget_root(self._root_collection, self._root_node_id)

    def _render_widget_row(self, key: str, value: object, child_path: tuple[int, ...]) -> str:
        """Render one widget row or nested branch for a collection item."""
        if _is_collection_like(value):
            return _render_widget_branch(key, value, self._collection_child_node_id(child_path))
        if _is_entity_like(value) and _entity_requires_lazy_details(value):
            return _render_row(key, _render_lazy_entity_value_html(value, self._replace_child_node_id(child_path)))
        if _leaf_requires_lazy_details(value):
            leaf_state = _leaf_render_state(value)
            assert leaf_state.compact_spec is not None
            return _render_row(
                key,
                _render_leaf_details(
                    leaf_state.compact_spec,
                    css_classes=_COMPACT_DETAILS_CSS_CLASSES,
                    node_id=self._replace_child_node_id(child_path),
                    include_body=False,
                ),
                row_class="leaf-row",
            )
        return _render_row(key, _render_leaf_value_html(value), row_class="leaf-row")

    def render_lazy_node(self, node_id: str, *, cursor: int = 0, load_all: bool = False) -> dict[str, object]:
        """Render one lazy widget node page or replacement fragment."""
        patch, path = self._decode_node_id(node_id)
        if patch == "append-children":
            collection = self._resolve_collection(path)
            start = max(0, int(cursor))
            end = len(collection._entities) if load_all else start + self._page_size
            rows: list[str] = []
            for index, (key, value) in enumerate(
                itertools.islice(collection._entities.items(), start, end), start=start
            ):
                rows.append(self._render_widget_row(key, value, (*path, index)))

            total = len(collection._entities)
            next_cursor = min(end, total)
            return {
                "lazy_id": node_id,
                "patch": patch,
                "html": "".join(rows),
                "controls_html": _render_collection_controls(
                    node_id, next_cursor=next_cursor, total=total, page_size=self._page_size
                ),
                "next_cursor": next_cursor,
                "done": next_cursor >= total,
            }

        value = self._resolve_value(path)
        if _is_entity_like(value):
            html = _render_expanded_entity_value_html(value)
        else:
            html = _render_expanded_leaf_value_html(value)
        return {"lazy_id": node_id, "patch": patch, "html": html, "controls_html": "", "next_cursor": 0, "done": True}


@cache
def _tree_css() -> str:
    """Load the dedicated EntityCollection tree CSS once."""
    css = importlib.resources.files("mammos_entity").joinpath("_entity_collection_tree.css")
    return f"<style>{css.read_text(encoding='utf-8')}</style>"


def render_entity_collection_html(collection: _EntityCollectionLike) -> str:
    """Render the bounded static HTML fallback for EntityCollection."""
    summary_html = _render_root_collection_summary(collection)
    outer_prefix = f"<details class='mammos-entity-collection root-node' open><summary>{summary_html}</summary>"
    outer_suffix = "</details>"
    child_result = _render_static_children(collection, depth=0, remaining_nodes=_STATIC_MAX_TOTAL_NODES - 1)
    preview_note_html = ""
    if not child_result.complete:
        preview_note_html = _render_static_preview_note(_STATIC_PREVIEW_NOTE)
    return f"{_tree_css()}{outer_prefix}{child_result.html}{preview_note_html}{outer_suffix}"


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


def render_entity_collection_mimebundle(collection: _EntityCollectionLike, **kwargs: dict) -> tuple[dict, dict]:
    """Render a widget-first mimebundle with static HTML fallback."""
    html_fallback = render_entity_collection_html(collection)
    text_fallback = render_entity_collection_text(collection)
    fallback_data = {"text/html": html_fallback, "text/plain": text_fallback}
    try:
        from mammos_entity._entity_collection_tree_widget import EntityCollectionTreeWidget
    except Exception:
        return fallback_data, {}

    try:
        widget = EntityCollectionTreeWidget(collection)
        widget_bundle = widget._repr_mimebundle_(**kwargs)
    except Exception:
        return fallback_data, {}

    if widget_bundle is None:
        return fallback_data, {}

    widget_data, widget_metadata = widget_bundle
    data = dict(widget_data)
    metadata = dict(widget_metadata)
    data["text/html"] = html_fallback
    data["text/plain"] = text_fallback
    return data, metadata
