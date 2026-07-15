"""Helpers and private mixins for notebook HTML representations."""

from __future__ import annotations

import html
import importlib.resources
import pprint
import reprlib
import uuid
from collections.abc import Callable
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


def _strip_array_repr_brackets(text: str) -> str:
    """Remove the outer brackets from a one-dimensional NumPy repr string."""
    if text.startswith("[") and text.endswith("]"):
        return text[1:-1]
    return text


def _format_html_text(text: str, *, preserve_spaces: bool = False) -> str:
    """Escape plain text for safe inline HTML display."""
    escaped = html.escape(text).replace("\n", "<br>")
    if preserve_spaces:
        escaped = escaped.replace(" ", "&nbsp;")
    return escaped


def _format_array_repr_summary(value: numpy.typing.ArrayLike) -> str:
    """Format a flattened preview for array values in HTML reprs."""

    def compact(text: str) -> str:
        return " ".join(text.split())

    flattened = np.ravel(value)
    if flattened.size <= 2 * _ENTITY_REPR_SUMMARY_EDGE_ITEMS:
        return compact(_strip_array_repr_brackets(np.array2string(flattened, max_line_width=10_000)))
    head = compact(
        _strip_array_repr_brackets(
            np.array2string(
                flattened[:_ENTITY_REPR_SUMMARY_EDGE_ITEMS],
                max_line_width=10_000,
            )
        )
    )
    tail = compact(
        _strip_array_repr_brackets(
            np.array2string(
                flattened[-_ENTITY_REPR_SUMMARY_EDGE_ITEMS:],
                max_line_width=10_000,
            )
        )
    )
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


def _repr_html_meta_text(text: str) -> str:
    """Render muted metadata text used by notebook HTML reprs."""
    return f"<span class='entity-meta'>{_format_html_text(text, preserve_spaces=True)}</span>"


def _repr_html_meta_separator() -> str:
    """Render the gray dot separator used by notebook HTML reprs."""
    return "&nbsp;<span class='entity-meta'>·</span>&nbsp;"


def _repr_html_meta_suffix(text: str) -> str:
    """Render muted metadata preceded by the shared gray dot separator."""
    return f"{_repr_html_meta_separator()}{_repr_html_meta_text(text)}"


def _repr_html_toggle_script(css_class: str, *, expanded: bool) -> str:
    """Build an inline script that toggles ``data-expanded`` on the nearest parent."""
    state = "true" if expanded else "false"
    return f"const root = this.closest('.{css_class}');if (!root) return;root.dataset.expanded = '{state}';"


def _repr_html_toggle_onkeydown() -> str:
    """Return the shared onkeydown handler for toggle buttons."""
    return "if(event.key==='Enter'||event.key===' '){event.preventDefault();this.click();}"


def _repr_html_collapsible(
    summary_content_html: str,
    expanded_details_html: str,
    expand_script: str,
    collapse_script: str,
) -> str:
    """Render the three collapsible sections: collapsed view, expanded view, and expanded details."""
    onkeydown = _repr_html_toggle_onkeydown()
    collapsed_html = (
        "<span class='entity-collapsed entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Expand value' "
        f'onclick="{expand_script}" onkeydown="{onkeydown}">[+]</span>'
        f"{summary_content_html}"
        "</span>"
    )
    expanded_summary_html = (
        "<span class='entity-expanded entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Collapse value' "
        f'onclick="{collapse_script}" onkeydown="{onkeydown}">[−]</span>'
        f"{summary_content_html}"
        "</span>"
    )
    expanded_details = f"<span class='entity-expanded-details'>{expanded_details_html}</span>"
    return f"{collapsed_html}{expanded_summary_html}{expanded_details}"


def _repr_html_summary_content(
    preview_html: str,
    *,
    unit_html: str = "",
    meta_html: str = "",
) -> str:
    """Render inline summary content without flex gaps between its parts."""
    return f"<span class='entity-summary-content'><span>{preview_html}{unit_html}</span>{meta_html}</span>"


class _ReprEllipsis:
    """Sentinel rendering as ``...`` inside pprint-based container reprs."""

    def __repr__(self) -> str:
        return "..."


_REPR_ELLIPSIS = _ReprEllipsis()


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


def _format_pprint_expanded(
    truncated: object,
    *,
    width: int = 88,
    sort_dicts: bool = True,
) -> str:
    """Bounded ``pprint.pformat`` of a truncated container."""
    return pprint.pformat(truncated, width=width, compact=True, sort_dicts=sort_dicts)


class _EntityReprHtml:
    """Private mixin containing notebook HTML repr methods for Entity."""

    @staticmethod
    def _repr_html_toggle_script(*, expanded: bool) -> str:
        """Build the inline script for expanding or collapsing long values."""
        return _repr_html_toggle_script("mammos-entity-inline-v2", expanded=expanded)

    def _repr_html_fragment_(self) -> str:
        """Render the entity HTML without injecting shared CSS."""
        value_text = str(self.value)
        expanded_value_text = value_text
        compact_value_text = " ".join(value_text.split())
        single_line_value_text = compact_value_text
        label_html = f"<span class='entity-label'>{_format_html_text(self.ontology_label)}</span>"
        unit_html_collapsed = ""
        unit_html_expanded = ""
        if not self.unit.is_equivalent(u.dimensionless_unscaled):
            unit_html_collapsed = f"&nbsp;{_format_html_text(str(self.unit), preserve_spaces=True)}"
            unit_html_expanded = f" {html.escape(str(self.unit))}"

        description_html = ""
        if self.description:
            description_html = f"<em>{_format_html_text(self.description)}</em>"

        preview_value_text = compact_value_text
        expanded_content_text = expanded_value_text
        shape_html = ""
        header_html = label_html
        shape = getattr(self.value, "shape", ())
        if shape not in [(), None]:
            preview_value_text = _format_array_repr_summary(self.value)
            expanded_content_text = _format_array_repr_expanded(self.value)
            shape_html = _repr_html_meta_suffix(f"shape={shape}")
        elif len(preview_value_text) > _ENTITY_REPR_MAX_INLINE_CHARS:
            preview_limit = _ENTITY_REPR_MAX_INLINE_CHARS - len("...")
            preview_value_text = f"{preview_value_text[:preview_limit].rstrip()}..."

        show_value_details = len(f"{single_line_value_text} {self.unit!s}".strip()) > _ENTITY_REPR_MAX_INLINE_CHARS
        if shape not in [(), None]:
            show_value_details = show_value_details or "..." in value_text

        if not show_value_details:
            compact_shape_html = ""
            if shape not in [(), None] and self.value.size > 3:
                compact_shape_html = _repr_html_meta_suffix(f"shape={shape}")
            compact_separator_html = _repr_html_meta_separator()
            value_html = _format_html_text(
                single_line_value_text,
                preserve_spaces=True,
            )
            return (
                "<samp class='mammos-entity-inline-v2'>"
                f"{label_html}"
                f"{compact_separator_html}"
                f"<span>{value_html}{unit_html_collapsed}</span>"
                f"{compact_shape_html}"
                f"{'<br>' if description_html else ''}{description_html}"
                "</samp>"
            )

        expand = self._repr_html_toggle_script(expanded=True)
        collapse = self._repr_html_toggle_script(expanded=False)
        preview_html = _format_html_text(preview_value_text, preserve_spaces=True)
        header_html = f"{header_html}{shape_html}"
        summary_content_html = _repr_html_summary_content(
            preview_html,
            unit_html=f"<span>{unit_html_collapsed}</span>",
        )
        expanded_details_inner = (
            f"<span class='entity-full-value'>"
            f"{html.escape(expanded_content_text)}"
            f"{'' if shape not in [(), None] else unit_html_expanded}"
            "</span>"
        )
        collapsible = _repr_html_collapsible(
            summary_content_html,
            expanded_details_inner,
            expand,
            collapse,
        )

        return (
            "<samp class='mammos-entity-inline-v2' data-expanded='false'>"
            f"{header_html}"
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
        root_id = f"mammos-entity-collection-v2-{uuid.uuid4().hex}"
        return f"{_repr_css()}{self._repr_html_block(root_id=root_id)}"

    @staticmethod
    def _format_html_text(text: str) -> str:
        """Escape plain text for safe inline HTML display."""
        return _format_html_text(text, preserve_spaces=True)

    @classmethod
    def _repr_html_row(cls, key: str, value_html: str) -> str:
        """Render a single key/value row."""
        return (
            "<div class='branch-item entity-row'>"
            f"<div class='entity-key'>{cls._format_html_text(key)}</div>"
            f"<div class='entity-value'>{value_html}</div>"
            "</div>"
        )

    @staticmethod
    def _repr_html_value_protocols(value: object) -> tuple[str, ...]:
        """Choose HTML repr methods in the right order for a stored value."""
        if isinstance(value, _EntityReprHtml):
            return ("_repr_html_fragment_", "_repr_html_")
        return ("_repr_html_", "_repr_html_fragment_")

    @staticmethod
    def _repr_html_value_fallback_text(value: object) -> str:
        """Return fallback text even if a custom ``__repr__`` implementation fails."""
        try:
            return repr(value)
        except Exception:
            return object.__repr__(value)

    @staticmethod
    def _repr_html_value_toggle_script(*, expanded: bool) -> str:
        """Build the inline script for compact row-value expand/collapse."""
        return _repr_html_toggle_script("mammos-compact-value-v2", expanded=expanded)

    @staticmethod
    def _format_quantity_repr_expanded(value: mammos_units.Quantity) -> str:
        """Format a bounded expanded representation for array-valued quantities."""
        with np.printoptions(
            threshold=_ENTITY_REPR_EXPANDED_THRESHOLD,
            edgeitems=_array_repr_expanded_edgeitems(value.value),
        ):
            return repr(value)

    @staticmethod
    def _format_sequence_repr_summary(value: list | tuple) -> str:
        """Format a compact head/tail preview for Python list and tuple values."""
        opener, closer = ("[", "]") if isinstance(value, list) else ("(", ")")
        return _format_repr_summary(list(value), opener, closer)

    @staticmethod
    def _format_sequence_repr_expanded(value: list | tuple) -> str:
        """Format a wrapped, bounded expanded representation for list/tuple values."""
        edge_items = _ENTITY_REPR_EXPANDED_THRESHOLD // 2
        if len(value) <= _ENTITY_REPR_EXPANDED_THRESHOLD:
            truncated = value
        elif isinstance(value, list):
            truncated = [*value[:edge_items], _REPR_ELLIPSIS, *value[-edge_items:]]
        else:
            truncated = (*value[:edge_items], _REPR_ELLIPSIS, *value[-edge_items:])
        return _format_pprint_expanded(truncated)

    @staticmethod
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

    @staticmethod
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
        return _format_pprint_expanded(dict(truncated_items), sort_dicts=False)

    @classmethod
    def _repr_html_compact_value(
        cls,
        preview_text: str,
        expanded_text: str,
        *,
        unit_html: str = "",
        meta_html: str = "",
    ) -> str:
        """Render a collapsible preview for long plain values in collection rows."""
        expand = cls._repr_html_value_toggle_script(expanded=True)
        collapse = cls._repr_html_value_toggle_script(expanded=False)
        preview_html = cls._format_html_text(preview_text)
        unit_span_html = f"<span>{unit_html}</span>" if unit_html else ""
        summary_content_html = _repr_html_summary_content(
            preview_html,
            unit_html=unit_span_html,
            meta_html=meta_html,
        )
        expanded_details_html = f"<span class='entity-full-value'>{html.escape(expanded_text)}</span>"
        collapsible = _repr_html_collapsible(
            summary_content_html,
            expanded_details_html,
            expand,
            collapse,
        )
        return (
            f"<samp class='mammos-entity-inline-v2 mammos-compact-value-v2' data-expanded='false'>{collapsible}</samp>"
        )

    @classmethod
    def _repr_html_compact_value_meta_html(
        cls,
        value: mammos_units.Quantity | numpy.typing.ArrayLike | list | tuple | dict[object, object],
    ) -> str:
        """Render metadata shown next to compact previews for supported plain values."""
        if isinstance(value, u.Quantity | np.ndarray):
            meta_text = f"shape={value.shape}"
        elif isinstance(value, list | tuple | dict):
            meta_text = f"len={len(value)}"
        else:
            return ""
        return _repr_html_meta_suffix(meta_text)

    @classmethod
    def _repr_html_compact_supported_value(
        cls,
        value: mammos_units.Quantity | numpy.typing.ArrayLike | list | tuple | dict[object, object],
    ) -> str | None:
        """Render compact previews for supported long plain values."""
        if isinstance(value, u.Quantity) and getattr(value, "shape", ()) not in [
            (),
            None,
        ]:
            return cls._repr_html_compact_value(
                _format_array_repr_summary(value.value),
                cls._format_quantity_repr_expanded(value),
                unit_html=f"&nbsp;{cls._format_html_text(str(value.unit))}",
                meta_html=cls._repr_html_compact_value_meta_html(value),
            )
        if isinstance(value, np.ndarray):
            return cls._repr_html_compact_value(
                _format_array_repr_summary(value),
                _format_array_repr_expanded(value),
                meta_html=cls._repr_html_compact_value_meta_html(value),
            )
        if isinstance(value, list | tuple):
            return cls._repr_html_compact_value(
                cls._format_sequence_repr_summary(value),
                cls._format_sequence_repr_expanded(value),
                meta_html=cls._repr_html_compact_value_meta_html(value),
            )
        if isinstance(value, dict):
            return cls._repr_html_compact_value(
                cls._format_dict_repr_summary(value),
                cls._format_dict_repr_expanded(value),
                meta_html=cls._repr_html_compact_value_meta_html(value),
            )
        return None

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
        used_custom_html = False
        for attr_name in cls._repr_html_value_protocols(value):
            repr_html = getattr(value, attr_name, None)
            if not callable(repr_html):
                continue
            used_custom_html = True
            try:
                value_html = repr_html()
            except Exception:
                continue
            if not value_html:
                continue
            return cls._repr_html_row(key, value_html)

        repr_value_text = cls._repr_html_value_fallback_text(value)
        if not used_custom_html and len(repr_value_text) > _ENTITY_REPR_MAX_INLINE_CHARS:
            compact_html = cls._repr_html_compact_supported_value(value)
            if compact_html is not None:
                return cls._repr_html_row(key, compact_html)

        fallback_html = cls._format_html_text(repr_value_text)
        return cls._repr_html_row(key, fallback_html)

    def _repr_html_summary_preview(self) -> str:
        """Build the compact preview text for nested collections."""
        count = len(self._entities)
        item_label = "item" if count == 1 else "items"
        preview_keys = list(self._entities)[:3]
        preview = ", ".join(preview_keys)
        if len(self._entities) > 3:
            preview += ", ..."
        if preview:
            return self._format_html_text(f"{count} {item_label} · {preview}")
        return self._format_html_text(f"{count} {item_label}")

    @classmethod
    def _repr_html_children(
        cls,
        children: list[str],
        *,
        nested: bool = False,
    ) -> str:
        """Wrap rendered child rows in the right container."""
        if not children:
            return ""
        child_class = "collection-children nested-children" if nested else "collection-children"
        return f"<div class='{child_class}'>{''.join(children)}</div>"

    def _repr_html_nested(self, key: str) -> str:
        """Render this collection as a nested expandable branch."""
        summary = self._format_html_text(key)
        preview = self._repr_html_summary_preview()
        return (
            "<details class='branch-item'>"
            "<summary>"
            f"<span class='summary-key'>{summary}</span>"
            "<span class='summary-preview'>"
            f"{self._format_html_text(self.__class__.__name__)}"
            f"&nbsp;·&nbsp;{preview}"
            "</span>"
            "</summary>"
            f"{self._repr_html_block(nested=True)}"
            "</details>"
        )

    @staticmethod
    def _repr_html_details_script(root_id: str, *, open_state: bool) -> str:
        """Build the inline script for top-level expand/collapse controls.

        The returned JavaScript is embedded directly in the HTML button's
        ``onclick`` handler so the notebook repr stays self-contained.

        When the button is clicked, the script:
        - looks up the collection root by ``root_id``
        - ignores the click if the collection is already processing another
          expand/collapse action
        - marks the collection as busy, updates the live status text, and
          disables the toolbar buttons
        - toggles nested ``<details>`` elements in small batches over multiple
          animation frames instead of in one large synchronous loop
        - clears the busy state and re-enables the controls when finished

        Batching the work allows the browser to repaint the busy feedback
        before all nested nodes have been updated, which keeps large
        collections from appearing frozen during expand/collapse.
        """
        state = "true" if open_state else "false"
        label = "Expanding..." if open_state else "Collapsing..."
        return (
            f"const root = document.getElementById('{root_id}');"
            "if (!root || root.dataset.busy === 'true') return;"
            "const status = root.querySelector('.collection-status');"
            "const buttons = root.querySelectorAll('.collection-toolbar button');"
            "const details = Array.from(root.querySelectorAll('details.branch-item'));"
            "root.dataset.busy = 'true';"
            "root.setAttribute('aria-busy', 'true');"
            f"if (status) status.textContent = '{label}';"
            "buttons.forEach((button) => { button.disabled = true; });"
            "const batchSize = 50;"
            "let index = 0;"
            "const finish = () => {"
            "root.dataset.busy = 'false';"
            "root.setAttribute('aria-busy', 'false');"
            "if (status) status.textContent = '';"
            "buttons.forEach((button) => { button.disabled = false; });"
            "};"
            # Process the tree in batches so the busy state can repaint between frames.
            "const step = () => {"
            "details.slice(index, index + batchSize).forEach((element) => { "
            f"element.open = {state};"
            " });"
            "index += batchSize;"
            "if (index < details.length) { requestAnimationFrame(step); return; }"
            "finish();"
            "};"
            # Use a second frame before the first batch so the busy UI can paint first.
            "requestAnimationFrame(() => { requestAnimationFrame(step); });"
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
        children = []
        if self.description:
            children.append(
                f"<div class='branch-item collection-description'>{self._format_html_text(self.description)}</div>"
            )
        has_nested_collections = False
        for key, value in self._entities.items():
            has_nested_collections = has_nested_collections or isinstance(value, _EntityCollectionReprHtml)
            children.append(self._repr_html_value(key, value))
        child_html = self._repr_html_children(children, nested=nested)
        if nested:
            return child_html
        controls = ""
        if has_nested_collections:
            if root_id is None:
                raise ValueError("root_id is required for top-level HTML controls.")
            controls = self._repr_html_controls(root_id)
        return (
            f"<div id='{root_id}' class='mammos-entity-collection-v2' "
            "data-busy='false' aria-busy='false'>"
            "<div class='collection-header'>"
            "<div class='collection-title'>"
            f"<span>{self._format_html_text(self.__class__.__name__)}</span>"
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
