"""Shared helpers for EntityCollection tree renderers."""

from __future__ import annotations

import itertools
import pprint
import reprlib
from dataclasses import dataclass
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

    return formatted_parts[0] if len(formatted_parts) == 1 else f"{formatted_parts[0]} ... {formatted_parts[1]}"


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
    return f"{text[: max_inline_chars - len('...')].rstrip()}..."


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


def _is_collection_like(value: object) -> bool:
    """Return true for EntityCollection instances and subclasses."""
    entities = getattr(value, "_entities", None)
    return isinstance(entities, dict) and hasattr(value, "description")


def _is_entity_like(value: object) -> bool:
    """Return true for mammos Entity-like objects without importing their HTML reprs."""
    return all(hasattr(value, attribute) for attribute in ("ontology_label", "value", "description"))


def _collection_preview(collection: _EntityCollectionLike) -> str:
    """Build the muted count/keys preview for a collection summary."""
    count = len(collection._entities)
    item_label = "item" if count == 1 else "items"
    preview_keys = list(itertools.islice(collection._entities, 3))
    preview_text = ", ".join(preview_keys)
    if count > 3:
        preview_text = f"{preview_text}, ..." if preview_text else "..."
    return f"{count} {item_label}" if not preview_text else f"{count} {item_label} · {preview_text}"


def _repr_with_fallback(value: object) -> tuple[str, bool]:
    """Return ``repr(value)`` and whether the normal repr path failed."""
    try:
        return repr(value), False
    except Exception:
        return object.__repr__(value), True


def _text_indent(level: int) -> str:
    """Return the shared indentation prefix used by text/plain tree rendering."""
    return _TEXT_INDENT * level
