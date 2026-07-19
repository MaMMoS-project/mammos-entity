"""AnyWidget frontend wrapper for the lazy EntityCollection tree view."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import anywidget
import traitlets

from mammos_entity._entity_collection_tree import EntityCollectionTreeSession

if TYPE_CHECKING:
    pass


_ASSET_DIR = Path(__file__).resolve().parent


class EntityCollectionTreeWidget(anywidget.AnyWidget):
    """Render EntityCollection as a lazy-loading anywidget tree."""

    _esm = _ASSET_DIR / "_entity_collection_tree.js"
    _css = _ASSET_DIR / "_entity_collection_tree.css"

    root_html = traitlets.Unicode().tag(sync=True)

    def __init__(self, collection, *, page_size: int = 50):
        self._session = EntityCollectionTreeSession(collection, page_size=page_size)
        super().__init__(root_html=self._session.render_root_html())
        self.on_msg(self._handle_message)

    @property
    def root_node_id(self) -> str:
        """Stable node id for the root collection."""
        return self._session.root_node_id

    def _handle_message(self, _widget, content, _buffers: list[bytes]) -> None:
        """Answer lazy child-load requests from the frontend."""
        if not isinstance(content, dict):
            return

        if content.get("kind") != "render-lazy":
            return

        node_id = content.get("lazy_id")
        cursor = content.get("cursor", 0)
        load_all = bool(content.get("load_all", False))
        if not isinstance(node_id, str):
            return

        try:
            response = self._session.render_lazy_node(node_id, cursor=int(cursor), load_all=load_all)
        except Exception as exc:
            self.send(
                {
                    "kind": "lazy-error",
                    "lazy_id": node_id,
                    "message": str(exc),
                }
            )
            return

        self.send({"kind": "lazy-rendered", **response})
