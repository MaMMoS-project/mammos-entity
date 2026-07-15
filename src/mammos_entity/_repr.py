"""Helpers and private mixins for notebook HTML representations."""

from __future__ import annotations

import html
import importlib.resources
import pprint
import reprlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

import mammos_units as u
import numpy as np

if TYPE_CHECKING:
    import mammos_units
    import numpy.typing

    import mammos_entity


_ENTITY_REPR_SUMMARY_EDGE_ITEMS = 3
_ENTITY_REPR_EXPANDED_THRESHOLD = 100
_ENTITY_REPR_MAX_INLINE_CHARS = 80


@dataclass(frozen=True, slots=True)
class _CollapsibleTextSpec:
    """Text fragments needed to render a collapsible value preview."""

    preview_text: str
    expanded_text: str
    summary_unit_text: str = ""
    meta_text: str = ""
    expanded_suffix_text: str = ""


def _format_html_text(text: str, *, preserve_spaces: bool = False) -> str:
    """Escape plain text for safe inline HTML display."""
    escaped = html.escape(text).replace("\n", "<br>")
    if preserve_spaces:
        escaped = escaped.replace(" ", "&nbsp;")
    return escaped


def _compact_repr_whitespace(text: str) -> str:
    """Collapse separator whitespace while preserving spaces inside quoted reprs."""
    compact = []
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


def _format_array_repr_summary(value: numpy.typing.ArrayLike) -> str:
    """Format a flattened preview for array values in HTML reprs."""
    flattened = np.ravel(value)
    if flattened.size <= 2 * _ENTITY_REPR_SUMMARY_EDGE_ITEMS:
        parts = [flattened]
    else:
        parts = [
            flattened[:_ENTITY_REPR_SUMMARY_EDGE_ITEMS],
            flattened[-_ENTITY_REPR_SUMMARY_EDGE_ITEMS:],
        ]

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


def _array_repr_expanded_edgeitems(value: numpy.typing.ArrayLike) -> int:
    """Choose NumPy edgeitems for a bounded expanded array repr."""
    array = np.asarray(value)
    if array.ndim <= 1:
        return _ENTITY_REPR_EXPANDED_THRESHOLD // 2
    return max(1, int((_ENTITY_REPR_EXPANDED_THRESHOLD ** (1 / array.ndim)) / 2))


def _format_array_repr_expanded(value: numpy.typing.ArrayLike) -> str:
    """Format a bounded expanded representation for array values in HTML reprs."""
    array = np.asarray(value)
    with np.printoptions(
        threshold=_ENTITY_REPR_EXPANDED_THRESHOLD,
        edgeitems=_array_repr_expanded_edgeitems(array),
    ):
        return repr(array)


_REPR_HTML_META_SEPARATOR = "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
_REPR_HTML_TOGGLE_ONKEYDOWN = "if(event.key==='Enter'||event.key===' '){event.preventDefault();this.click();}"


def _repr_html_meta_suffix(text: str) -> str:
    """Render optional metadata using the shared muted suffix style."""
    if not text:
        return ""
    return (
        f"{_REPR_HTML_META_SEPARATOR}<span class='entity-meta'>{_format_html_text(text, preserve_spaces=True)}</span>"
    )


def _repr_html_toggle_script(css_class: str, *, expanded: bool) -> str:
    """Build an inline script that toggles ``data-expanded`` on the nearest parent."""
    state = "true" if expanded else "false"
    return f"const root = this.closest('.{css_class}');if (!root) return;root.dataset.expanded = '{state}';"


def _repr_html_collapsible(
    spec: _CollapsibleTextSpec,
    *,
    expand_script: str,
    collapse_script: str,
) -> str:
    """Render the three collapsible sections for a long value preview."""
    summary_unit_html = ""
    if spec.summary_unit_text:
        summary_unit_html = f"<span>{_format_html_text(f' {spec.summary_unit_text}', preserve_spaces=True)}</span>"
    summary_content_html = (
        "<span class='entity-summary-content'>"
        f"<span>{_format_html_text(spec.preview_text, preserve_spaces=True)}{summary_unit_html}</span>"
        f"{_repr_html_meta_suffix(spec.meta_text)}"
        "</span>"
    )
    expanded_details_html = (
        "<span class='entity-expanded-details'>"
        "<span class='entity-full-value'>"
        f"{html.escape(spec.expanded_text)}"
        f"{html.escape(spec.expanded_suffix_text)}"
        "</span>"
        "</span>"
    )
    collapsed_html = (
        "<span class='entity-collapsed entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Expand value' "
        f'onclick="{expand_script}" onkeydown="{_REPR_HTML_TOGGLE_ONKEYDOWN}">[+]</span>'
        f"{summary_content_html}"
        "</span>"
    )
    expanded_summary_html = (
        "<span class='entity-expanded entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Collapse value' "
        f'onclick="{collapse_script}" onkeydown="{_REPR_HTML_TOGGLE_ONKEYDOWN}">[−]</span>'
        f"{summary_content_html}"
        "</span>"
    )
    return f"{collapsed_html}{expanded_summary_html}{expanded_details_html}"


class _ReprEllipsis:
    """Sentinel rendering as ``...`` inside pprint-based container reprs."""

    def __repr__(self) -> str:
        return "..."


_REPR_ELLIPSIS = _ReprEllipsis()


def _truncate_preview_text(text: str, max_inline_chars: int = _ENTITY_REPR_MAX_INLINE_CHARS) -> str:
    """Trim long preview text while reserving space for an ellipsis."""
    if len(text) <= max_inline_chars:
        return text
    preview_limit = max_inline_chars - len("...")
    return f"{text[:preview_limit].rstrip()}..."


def _format_repr_summary(
    items: list[object],
    opener: str,
    closer: str,
    format_item: Callable[[object], str] | None = None,
) -> str:
    """Generic head/tail preview for a container with ``opener``/``closer`` delimiters."""
    repr_fn = reprlib.repr if format_item is None else format_item

    if len(items) <= 2 * _ENTITY_REPR_SUMMARY_EDGE_ITEMS:
        elements = [repr_fn(item) for item in items]
    else:
        elements = [
            *(repr_fn(item) for item in items[:_ENTITY_REPR_SUMMARY_EDGE_ITEMS]),
            "...",
            *(repr_fn(item) for item in items[-_ENTITY_REPR_SUMMARY_EDGE_ITEMS:]),
        ]
    return f"{opener}{', '.join(elements)}{closer}"


def _format_quantity_repr_expanded(value: mammos_units.Quantity) -> str:
    """Format a bounded expanded representation for array-valued quantities."""
    with np.printoptions(
        threshold=_ENTITY_REPR_EXPANDED_THRESHOLD,
        edgeitems=_array_repr_expanded_edgeitems(value.value),
    ):
        return repr(value)


def _format_sequence_repr_summary(value: list | tuple) -> str:
    """Format a compact head/tail preview for Python list and tuple values."""
    opener, closer = ("[", "]") if isinstance(value, list) else ("(", ")")
    return _format_repr_summary(list(value), opener, closer)


def _format_sequence_repr_expanded(value: list | tuple) -> str:
    """Format a wrapped, bounded expanded representation for list/tuple values."""
    edge_items = _ENTITY_REPR_EXPANDED_THRESHOLD // 2
    if len(value) <= _ENTITY_REPR_EXPANDED_THRESHOLD:
        truncated = value
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

    return _format_repr_summary(
        list(value.items()),
        "{",
        "}",
        format_item,
    )


def _format_dict_repr_expanded(value: dict[object, object]) -> str:
    """Format a wrapped, bounded expanded representation for Python dict values."""
    edge_items = _ENTITY_REPR_EXPANDED_THRESHOLD // 2
    items = list(value.items())
    if len(items) <= _ENTITY_REPR_EXPANDED_THRESHOLD:
        truncated_items = items
    else:
        truncated_items = [
            *items[:edge_items],
            (_REPR_ELLIPSIS, _REPR_ELLIPSIS),
            *items[-edge_items:],
        ]
    return pprint.pformat(dict(truncated_items), width=88, compact=True, sort_dicts=False)


def _compact_value_text_spec(
    value: mammos_units.Quantity | numpy.typing.ArrayLike | list | tuple | dict[object, object],
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


class _EntityReprHtml:
    """Private mixin containing notebook HTML repr methods for Entity."""

    def _repr_html_fragment_(self) -> str:
        """Render the entity HTML without injecting shared CSS."""
        value_text = str(self.value)
        compact_value_text = " ".join(value_text.split())
        label_html = f"<span class='entity-label'>{_format_html_text(self.ontology_label)}</span>"
        unit_text = ""
        if not self.unit.is_equivalent(u.dimensionless_unscaled):
            unit_text = str(self.unit)

        description_html = ""
        if self.description:
            description_html = f"<em>{_format_html_text(self.description)}</em>"

        shape = getattr(self.value, "shape", ())
        has_shape = shape not in [(), None]
        shape_meta_text = f"shape={shape}" if has_shape else ""
        show_details = len(f"{compact_value_text} {unit_text}".strip()) > _ENTITY_REPR_MAX_INLINE_CHARS
        spec = None
        if has_shape:
            if show_details or "..." in value_text:
                spec = _CollapsibleTextSpec(
                    preview_text=_format_array_repr_summary(self.value),
                    expanded_text=_format_array_repr_expanded(self.value),
                    summary_unit_text=unit_text,
                )
        elif show_details:
            spec = _CollapsibleTextSpec(
                preview_text=_truncate_preview_text(compact_value_text),
                expanded_text=compact_value_text,
                summary_unit_text=unit_text,
                expanded_suffix_text=f" {unit_text}" if unit_text else "",
            )

        if spec is None:
            compact_shape_html = ""
            if has_shape and self.value.size > 3:
                compact_shape_html = _repr_html_meta_suffix(shape_meta_text)
            value_html = _format_html_text(
                compact_value_text,
                preserve_spaces=True,
            )
            unit_html = _format_html_text(f" {unit_text}", preserve_spaces=True) if unit_text else ""
            return (
                "<samp class='mammos-entity-inline'>"
                f"{label_html}"
                f"{_REPR_HTML_META_SEPARATOR}"
                f"<span>{value_html}{unit_html}</span>"
                f"{compact_shape_html}"
                f"{'<br>' if description_html else ''}{description_html}"
                "</samp>"
            )

        expand = _repr_html_toggle_script("mammos-entity-inline", expanded=True)
        collapse = _repr_html_toggle_script("mammos-entity-inline", expanded=False)
        collapsible = _repr_html_collapsible(
            spec,
            expand_script=expand,
            collapse_script=collapse,
        )

        return (
            "<samp class='mammos-entity-inline' data-expanded='false'>"
            f"{label_html}{_repr_html_meta_suffix(shape_meta_text)}"
            "<br>"
            f"{description_html}"
            f"{'<br>' if description_html else ''}"
            f"{collapsible}"
            "</samp>"
        )

    def _repr_html_(self) -> str:
        """Render the entity as compact notebook-friendly HTML."""
        return f"{_repr_css()}{self._repr_html_fragment_()}"


class _EntityCollectionReprHtml:
    """Private mixin containing notebook HTML repr methods for EntityCollection."""

    def _repr_html_(self) -> str:
        """Render the collection as notebook-friendly HTML."""
        root_id = f"mammos-entity-collection-{uuid.uuid4().hex}"
        return f"{_repr_css()}{self._repr_html_block(root_id=root_id)}"

    @staticmethod
    def _repr_html_row(key: str, value_html: str) -> str:
        """Render a single key/value row."""
        return (
            "<div class='branch-item entity-row'>"
            f"<div class='entity-key'>{_format_html_text(key, preserve_spaces=True)}</div>"
            f"<div class='entity-value'>{value_html}</div>"
            "</div>"
        )

    @staticmethod
    def _repr_html_compact_value(
        spec: _CollapsibleTextSpec,
    ) -> str:
        """Render a collapsible preview for long plain values in collection rows."""
        expand = _repr_html_toggle_script("mammos-compact-value", expanded=True)
        collapse = _repr_html_toggle_script("mammos-compact-value", expanded=False)
        collapsible = _repr_html_collapsible(
            spec,
            expand_script=expand,
            collapse_script=collapse,
        )
        return f"<samp class='mammos-entity-inline mammos-compact-value' data-expanded='false'>{collapsible}</samp>"

    @classmethod
    def _repr_html_value(
        cls,
        key: str,
        value: mammos_entity.Entity
        | mammos_units.Quantity
        | numpy.typing.ArrayLike
        | list
        | tuple
        | dict[object, object],
    ) -> str:
        """Render one stored value, using HTML reprs when available."""
        if isinstance(value, _EntityCollectionReprHtml):
            return value._repr_html_nested(key)
        attr_names = (
            ("_repr_html_fragment_", "_repr_html_")
            if isinstance(value, _EntityReprHtml)
            else (
                "_repr_html_",
                "_repr_html_fragment_",
            )
        )
        for attr_name in attr_names:
            repr_html = getattr(value, attr_name, None)
            if not callable(repr_html):
                continue
            try:
                value_html = repr_html()
            except Exception:
                continue
            if not value_html:
                continue
            return cls._repr_html_row(key, value_html)

        repr_failed = False
        try:
            repr_value_text = repr(value)
        except Exception:
            repr_failed = True
            repr_value_text = object.__repr__(value)
        spec = _compact_value_text_spec(value)
        if spec is not None:
            compact_source_text = spec.expanded_text if repr_failed else repr_value_text
            if len(compact_source_text) > _ENTITY_REPR_MAX_INLINE_CHARS:
                return cls._repr_html_row(key, cls._repr_html_compact_value(spec))

        fallback_html = _format_html_text(repr_value_text, preserve_spaces=True)
        return cls._repr_html_row(key, fallback_html)

    def _repr_html_nested(self, key: str) -> str:
        """Render this collection as a nested expandable branch."""
        count = len(self._entities)
        item_label = "item" if count == 1 else "items"
        preview_keys = list(self._entities)[:3]
        preview_text = ", ".join(preview_keys)
        if len(self._entities) > 3:
            preview_text += ", ..."
        preview = f"{count} {item_label}" if not preview_text else f"{count} {item_label} · {preview_text}"
        return (
            "<details class='branch-item'>"
            "<summary>"
            f"<span class='summary-key'>{_format_html_text(key, preserve_spaces=True)}</span>"
            "<span class='summary-preview'>"
            f"{_format_html_text(self.__class__.__name__, preserve_spaces=True)}"
            f"&nbsp;·&nbsp;{_format_html_text(preview, preserve_spaces=True)}"
            "</span>"
            "</summary>"
            f"{self._repr_html_block(nested=True)}"
            "</details>"
        )

    @staticmethod
    def _repr_html_details_script(root_id: str, *, open_state: bool) -> str:
        """Build the inline script for top-level expand/collapse controls."""
        state = "true" if open_state else "false"
        label = "Expanding..." if open_state else "Collapsing..."
        return "".join(
            (
                f"const root = document.getElementById('{root_id}');",
                "if (!root || root.dataset.busy === 'true') return;",
                "const status = root.querySelector('.collection-status');",
                "const buttons = root.querySelectorAll('.collection-toolbar button');",
                "const details = Array.from(root.querySelectorAll('details.branch-item'));",
                "root.dataset.busy = 'true';",
                "root.setAttribute('aria-busy', 'true');",
                f"if (status) status.textContent = '{label}';",
                "buttons.forEach((button) => { button.disabled = true; });",
                "const batchSize = 50;",
                "let index = 0;",
                "const finish = () => {"
                "root.dataset.busy = 'false';"
                "root.setAttribute('aria-busy', 'false');"
                "if (status) status.textContent = '';"
                "buttons.forEach((button) => { button.disabled = false; });"
                "};",
                "const step = () => {"
                "details.slice(index, index + batchSize).forEach((element) => {"
                f"element.open = {state};"
                "});"
                "index += batchSize;"
                "if (index < details.length) { requestAnimationFrame(step); return; }"
                "finish();"
                "};",
                "requestAnimationFrame(() => { requestAnimationFrame(step); });",
            )
        )

    @classmethod
    def _repr_html_controls(cls, root_id: str) -> str:
        """Render top-level expand/collapse controls."""
        expand = cls._repr_html_details_script(root_id, open_state=True)
        collapse = cls._repr_html_details_script(root_id, open_state=False)
        return (
            "<div class='collection-toolbar'>"
            f"<button type='button' title='Collapse all' aria-label='Collapse all' "
            f'onclick="{collapse}">▸</button>'
            f"<button type='button' title='Expand all' aria-label='Expand all' "
            f'onclick="{expand}">▾</button>'
            "<span class='collection-status' aria-live='polite'></span>"
            "</div>"
        )

    def _repr_html_block(
        self,
        *,
        nested: bool = False,
        root_id: str | None = None,
    ) -> str:
        """Render either the top-level block or nested child content."""
        items = list(self._entities.items())
        children = []
        if self.description:
            children.append(
                "<div class='branch-item collection-description'>"
                f"{_format_html_text(self.description, preserve_spaces=True)}"
                "</div>"
            )
        children.extend(self._repr_html_value(key, value) for key, value in items)
        has_nested_collections = any(isinstance(value, _EntityCollectionReprHtml) for _, value in items)
        child_html = ""
        if children:
            child_class = "collection-children nested-children" if nested else "collection-children"
            child_html = f"<div class='{child_class}'>{''.join(children)}</div>"
        if nested:
            return child_html
        controls = ""
        if has_nested_collections:
            if root_id is None:
                raise ValueError("root_id is required for top-level HTML controls.")
            controls = self._repr_html_controls(root_id)
        return (
            f"<div id='{root_id}' class='mammos-entity-collection' "
            "data-busy='false' aria-busy='false'>"
            "<div class='collection-header'>"
            "<div class='collection-title'>"
            f"<span>{_format_html_text(self.__class__.__name__, preserve_spaces=True)}</span>"
            "</div>"
            f"{controls}"
            "</div>"
            "<div class='collection-body'>"
            f"{child_html}"
            "</div>"
            "</div>"
        )


@cache
def _repr_css() -> str:
    """Load the shared CSS used by entity HTML representations."""
    css = importlib.resources.files("mammos_entity").joinpath("_entity_collection_repr.css")
    return f"<style>{css.read_text(encoding='utf-8')}</style>"
