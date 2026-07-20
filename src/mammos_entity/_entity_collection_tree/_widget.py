"""Lazy widget renderer for EntityCollection tree display."""

from __future__ import annotations

import itertools
from pathlib import Path

import anywidget
import traitlets

from ._common import _DEFAULT_WIDGET_PAGE_SIZE, _EntityCollectionLike, _is_collection_like
from ._html_helpers import (
    _COMPACT_DETAILS_CSS_CLASSES,
    _entity_requires_lazy_details,
    _is_entity_like,
    _leaf_render_state,
    _leaf_requires_lazy_details,
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
        return f"{self._root_node_id}{''.join(f'-collection-{index}' for index in path)}"

    def _replace_child_node_id(self, path: tuple[int, ...]) -> str:
        if not path:
            raise KeyError("Leaf paths must contain at least one index.")
        suffix = "".join(f"-collection-{index}" for index in path[:-1])
        return f"{self._root_node_id}{suffix}-leaf-{path[-1]}"

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
            rows = [
                self._render_widget_row(key, value, (*path, index))
                for index, (key, value) in enumerate(
                    itertools.islice(collection._entities.items(), start, end),
                    start=start,
                )
            ]
            total = len(collection._entities)
            next_cursor = min(end, total)
            return {
                "lazy_id": node_id,
                "patch": patch,
                "html": "".join(rows),
                "controls_html": _render_collection_controls(
                    node_id,
                    next_cursor=next_cursor,
                    total=total,
                    page_size=self._page_size,
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

    def _handle_message(self, _widget, content, _buffers: list[bytes]) -> None:
        """Answer lazy child-load requests from the frontend."""
        if not isinstance(content, dict) or content.get("kind") != "render-lazy":
            return

        node_id = content.get("lazy_id")
        if not isinstance(node_id, str):
            return

        try:
            response = self._session.render_lazy_node(
                node_id,
                cursor=int(content.get("cursor", 0)),
                load_all=bool(content.get("load_all", False)),
            )
        except Exception as exc:
            self.send({"kind": "lazy-error", "lazy_id": node_id, "message": str(exc)})
            return

        self.send({"kind": "lazy-rendered", **response})
