"""Private tree-view helpers for EntityCollection notebook display."""

from __future__ import annotations

from ._common import (
    _STATIC_ELLIPSIS_CHILD,
    _STATIC_MAX_CHILDREN_PER_COLLECTION,
    _STATIC_PREVIEW_NOTE,
    _EntityCollectionLike,
)
from ._html_helpers import _render_entity_value_html
from ._plain_text import render_entity_collection_text
from ._static_html import _tree_css, render_entity_collection_html
from ._widget import EntityCollectionTreeSession, EntityCollectionTreeWidget

__all__ = [
    "_STATIC_ELLIPSIS_CHILD",
    "_STATIC_MAX_CHILDREN_PER_COLLECTION",
    "_STATIC_PREVIEW_NOTE",
    "_render_entity_value_html",
    "_tree_css",
    "EntityCollectionTreeSession",
    "EntityCollectionTreeWidget",
    "render_entity_collection_html",
    "render_entity_collection_mimebundle",
    "render_entity_collection_text",
]


def render_entity_collection_mimebundle(
    collection: _EntityCollectionLike,
    **kwargs: object,
) -> tuple[dict[str, object], dict[str, object]]:
    """Render a widget-first mimebundle with static HTML and text fallbacks."""
    html_fallback = render_entity_collection_html(collection)
    text_fallback = render_entity_collection_text(collection)
    fallback_data = {"text/html": html_fallback, "text/plain": text_fallback}

    try:
        widget = EntityCollectionTreeWidget(collection)
        widget_bundle = widget._repr_mimebundle_(**kwargs)
    except Exception:
        return fallback_data, {}

    if widget_bundle is None:
        return fallback_data, {}

    widget_data, widget_metadata = widget_bundle
    data = dict(widget_data)
    data["text/html"] = html_fallback
    data["text/plain"] = text_fallback
    return data, dict(widget_metadata)
