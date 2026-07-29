"""Lazy widget renderer for EntityCollection tree display."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path

import anywidget
import traitlets

from ._common import _DEFAULT_WIDGET_PAGE_SIZE, _EntityCollectionLike, _is_collection_like
from ._html_helpers import (
    _COMPACT_DETAILS_CSS_CLASSES,
    _entity_requires_lazy_details,
    _is_entity_like,
    _leaf_render_state,
    _render_collection_controls,
    _render_expanded_entity_value_html,
    _render_expanded_leaf_value_html,
    _render_lazy_entity_value_html,
    _render_leaf_details,
    _render_leaf_value_html,
    _render_row,
    _render_widget_branch,
    _render_widget_root,
)

_ASSET_DIR = Path(__file__).resolve().parent


@dataclass(slots=True)
class _LazyNode:
    """Python-side state for one lazy-rendered node."""

    patch: str
    target: object
    snapshot: tuple[tuple[str, object], ...] | None = None
    next_index: int = 0


class EntityCollectionTreeSession:
    """Stateful lazy renderer used by the anywidget frontend."""

    def __init__(self, collection: _EntityCollectionLike, *, page_size: int = _DEFAULT_WIDGET_PAGE_SIZE):
        if page_size <= 0:
            raise ValueError("page_size must be greater than zero.")
        self._root_collection = collection
        self._page_size = page_size
        self._node_ids = itertools.count()
        self._lazy_nodes: dict[str, _LazyNode] = {}
        self._lazy_children: dict[str, set[str]] = {}
        self._root_node_id = self._register_lazy_node("append-children", collection)

    @property
    def root_node_id(self) -> str:
        """Stable node id for the root collection."""
        return self._root_node_id

    def _register_lazy_node(self, patch: str, target: object, *, parent_id: str | None = None) -> str:
        """Register a rendered target under an opaque session-local node id."""
        node_id = f"lazy-node-{next(self._node_ids)}"
        self._lazy_nodes[node_id] = _LazyNode(patch, target)
        if parent_id is not None:
            self._lazy_children.setdefault(parent_id, set()).add(node_id)
        return node_id

    def _lazy_node(self, node_id: str) -> _LazyNode:
        """Return the registered state for a lazy node."""
        try:
            return self._lazy_nodes[node_id]
        except KeyError:
            raise KeyError(f"Unknown lazy node id: {node_id}") from None

    def _release_lazy_node(self, node_id: str) -> None:
        """Release one lazy node and all descendants registered beneath it."""
        for child_id in self._lazy_children.pop(node_id, set()):
            self._release_lazy_node(child_id)
        self._lazy_nodes.pop(node_id, None)

    def release_lazy_descendants(self, node_id: str) -> None:
        """Reset a collection node and release all descendants registered beneath it."""
        node = self._lazy_nodes.get(node_id)
        if node is not None:
            node.snapshot = None
            node.next_index = 0
        for child_id in self._lazy_children.pop(node_id, set()):
            self._release_lazy_node(child_id)

    def render_root_html(self) -> str:
        """Render the root widget container."""
        return _render_widget_root(self._root_collection, self._root_node_id)

    def _render_widget_row(self, key: str, value: object, *, parent_id: str) -> str:
        """Render one widget row or nested branch for a collection item."""
        if _is_collection_like(value):
            node_id = self._register_lazy_node("append-children", value, parent_id=parent_id)
            return _render_widget_branch(key, value, node_id)
        if _is_entity_like(value) and _entity_requires_lazy_details(value):
            node_id = self._register_lazy_node("replace-self", value, parent_id=parent_id)
            return _render_row(key, _render_lazy_entity_value_html(value, node_id))
        leaf_state = _leaf_render_state(value, include_expanded=False)
        if leaf_state.compact_spec is not None and leaf_state.use_compact:
            node_id = self._register_lazy_node("replace-self", value, parent_id=parent_id)
            return _render_row(
                key,
                _render_leaf_details(
                    leaf_state.compact_spec,
                    css_classes=_COMPACT_DETAILS_CSS_CLASSES,
                    node_id=node_id,
                    include_body=False,
                ),
                row_class="leaf-row",
            )
        return _render_row(key, _render_leaf_value_html(value), row_class="leaf-row")

    def render_lazy_node(self, node_id: str, *, load_all: bool = False) -> dict[str, object]:
        """Render one lazy widget node page or replacement fragment."""
        node = self._lazy_node(node_id)
        if node.patch == "append-children":
            if not _is_collection_like(node.target):
                raise TypeError(f"Lazy node {node_id!r} does not contain a collection.")
            if node.snapshot is None:
                node.snapshot = tuple(node.target._entities.items())
            start = node.next_index
            total = len(node.snapshot)
            end = total if load_all else min(start + self._page_size, total)
            rows = [self._render_widget_row(key, value, parent_id=node_id) for key, value in node.snapshot[start:end]]
            node.next_index = end
            return {
                "lazy_id": node_id,
                "patch": node.patch,
                "html": "".join(rows),
                "controls_html": _render_collection_controls(
                    node_id,
                    next_index=node.next_index,
                    total=total,
                    page_size=self._page_size,
                ),
                "done": node.next_index >= total,
            }

        if node.patch != "replace-self":
            raise ValueError(f"Lazy node {node_id!r} has an unsupported patch type: {node.patch!r}.")
        value = node.target
        if _is_entity_like(value):
            html = _render_expanded_entity_value_html(value)
        else:
            html = _render_expanded_leaf_value_html(value)
        return {
            "lazy_id": node_id,
            "patch": node.patch,
            "html": html,
            "controls_html": "",
            "done": True,
        }


class EntityCollectionTreeWidget(anywidget.AnyWidget):
    """Render EntityCollection as a lazy-loading anywidget tree."""

    _esm = _ASSET_DIR / "_widget.js"
    _css = _ASSET_DIR / "_styles.css"

    root_html = traitlets.Unicode().tag(sync=True)

    def __init__(self, collection: _EntityCollectionLike, *, page_size: int = _DEFAULT_WIDGET_PAGE_SIZE):
        self._session = EntityCollectionTreeSession(collection, page_size=page_size)
        super().__init__(root_html=self._session.render_root_html())
        self.on_msg(self._handle_message)

    @property
    def root_node_id(self) -> str:
        """Stable node id for the root collection."""
        return self._session.root_node_id

    def _handle_message(self, _widget: object, content: object, _buffers: list[bytes]) -> None:
        """Answer lazy child-load requests from the frontend."""
        if not isinstance(content, dict):
            return

        node_id = content.get("lazy_id")
        if not isinstance(node_id, str):
            return
        if content.get("kind") == "release-lazy":
            self._session.release_lazy_descendants(node_id)
            return
        if content.get("kind") != "render-lazy":
            return
        request_id = content.get("request_id")

        try:
            response = self._session.render_lazy_node(
                node_id,
                load_all=bool(content.get("load_all", False)),
            )
        except Exception as exc:
            self.send({"kind": "lazy-error", "lazy_id": node_id, "request_id": request_id, "message": str(exc)})
            return

        self.send({"kind": "lazy-rendered", "request_id": request_id, **response})
