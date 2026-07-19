import html
from pathlib import Path

import mammos_units as u
import numpy as np
import pytest

import mammos_entity as me
from mammos_entity._entity import QuantityEntity
from mammos_entity._entity_collection_tree import (
    _STATIC_ELLIPSIS_CHILD,
    _STATIC_MAX_CHILDREN_PER_COLLECTION,
    _STATIC_PREVIEW_NOTE,
    EntityCollectionTreeSession,
)
from mammos_entity._entity_collection_tree_widget import EntityCollectionTreeWidget


def _nested_collection(depth: int) -> me.EntityCollection:
    collection = me.EntityCollection(leaf=1)
    for level in range(depth, 0, -1):
        collection = me.EntityCollection(**{f"level_{level}": collection})
    return collection


def _normalized_html_text(fragment: str) -> str:
    return html.unescape(fragment).replace("\xa0", " ")


def _collection_child_id(parent_id: str, index: int) -> str:
    return f"{parent_id}-collection-{index}"


def _leaf_child_id(parent_id: str, index: int) -> str:
    return f"{parent_id}-leaf-{index}"


def _structured_leaf_cases() -> list[tuple[str, object, str]]:
    return [
        ("quantity", u.Quantity(np.arange(60.0), "A / m"), "shape=(60,)"),
        ("array", np.arange(60.0), "shape=(60,)"),
        ("list", list(range(60)), "len=60"),
        ("tuple", tuple(range(60)), "len=60"),
        ("mapping", {f"k{i}": i for i in range(60)}, "len=60"),
    ]


@pytest.mark.parametrize("count", [1, 7, 60])
@pytest.mark.parametrize("description", ["", "desc"])
def test_entity_repr_html_is_js_free_and_uses_details_only_for_long_values(count, description):
    value = 1.0 if count == 1 else np.arange(float(count))
    entity = me.M(value, "A/m", description=description)

    html_output = entity._repr_html_()
    fragment = entity._repr_html_fragment_()
    normalized_fragment = _normalized_html_text(fragment)

    assert html_output.startswith("<style>")
    assert fragment in html_output
    assert entity.ontology_label in normalized_fragment
    assert "onclick=" not in fragment
    assert "onkeydown=" not in fragment
    assert "data-expanded=" not in fragment
    if description:
        assert description in normalized_fragment
    if count >= 60:
        assert "<details class='lazy-leaf-details'>" in fragment
        assert "<details class='lazy-leaf-details' open>" not in fragment
        assert "<summary class='lazy-leaf-summary'>" in fragment
    else:
        assert "<details class='lazy-leaf-details'>" not in fragment


def test_collection_repr_html_is_static_js_free_and_wraps_descriptions():
    collection = me.EntityCollection(
        description="long collection description that should wrap",
        M=me.M(np.arange(60.0), "A/m", description="long entity description that should wrap"),
    )

    html_output = collection._repr_html_()

    assert html_output.startswith("<style>")
    assert "<details class='mammos-entity-collection root-node' open>" in html_output
    assert "onclick=" not in html_output
    assert "onkeydown=" not in html_output
    assert "data-expanded=" not in html_output
    assert "long&nbsp;collection&nbsp;description" not in html_output
    assert "long&nbsp;entity&nbsp;description" not in html_output
    assert "overflow-wrap: anywhere;" in html_output
    assert "white-space: pre-wrap;" in html_output


def test_collection_repr_html_truncates_at_depth_limit():
    html_output = _normalized_html_text(_nested_collection(depth=5)._repr_html_())

    assert _STATIC_ELLIPSIS_CHILD in html_output
    assert _STATIC_PREVIEW_NOTE in html_output
    assert "level_5" in html_output
    assert "<div class='entity-key'>leaf</div>" not in html_output


def test_collection_repr_html_limits_each_collection_to_twenty_children():
    collection = me.EntityCollection(**{f"k{i}": i for i in range(30)})

    html_output = _normalized_html_text(collection._repr_html_())

    assert html_output.count("class='branch-item entity-row") == _STATIC_MAX_CHILDREN_PER_COLLECTION
    assert "<div class='entity-key'>k19</div>" in html_output
    assert "<div class='entity-key'>k20</div>" not in html_output
    assert _STATIC_ELLIPSIS_CHILD in html_output
    assert _STATIC_PREVIEW_NOTE in html_output


def test_collection_repr_html_keeps_root_ellipsis_when_global_budget_is_exhausted():
    repeated_nested = me.EntityCollection(
        description="the collection description",
        **{f"entity{j}": j for j in range(400)},
    )
    collection = me.EntityCollection(**{f"element-{i}": repeated_nested for i in range(1000)})

    html_output = collection._repr_html_()

    assert "<div class='static-preview-note'>" in html_output
    assert "<div class='branch-item collection-note'>...</div></div><div class='static-preview-note'>" in html_output


def test_collection_repr_html_omits_preview_note_when_not_truncated():
    html_output = me.EntityCollection(a=1, b=2, c=3)._repr_html_()

    assert _STATIC_PREVIEW_NOTE not in html_output
    assert "class='static-preview-note'" not in html_output


def test_repr_mimebundle_includes_widget_html_plain_and_avoids_collection_repr(monkeypatch):
    collection = me.EntityCollection(
        alpha=me.EntityCollection(left=me.EntityCollection(a=me.M(1, "A/m"))),
        beta=me.EntityCollection(right=me.EntityCollection(b=2)),
    )

    def broken_repr(self):
        raise RuntimeError("repr should not be used for mimebundle generation")

    monkeypatch.setattr(me.EntityCollection, "__repr__", broken_repr)

    data, metadata = collection._repr_mimebundle_()

    assert "application/vnd.jupyter.widget-view+json" in data
    assert data["text/html"].startswith("<style>")
    assert data["text/plain"] == "EntityCollection(2 items · alpha, beta)"
    assert metadata == {}


def test_tree_session_root_html_starts_open_and_first_page_is_lazy():
    session = EntityCollectionTreeSession(me.EntityCollection(a=1, b=2, c=3), page_size=2)

    root_html = session.render_root_html()
    first_page = session.render_lazy_node(session.root_node_id, cursor=0)
    remaining_page = session.render_lazy_node(session.root_node_id, cursor=2, load_all=True)

    assert "<details class='mammos-entity-collection root-node' open" in root_html
    assert "data-lazy-cursor='0'" in root_html
    assert first_page["done"] is False
    assert first_page["next_cursor"] == 2
    assert "Load next 1" in first_page["controls_html"]
    assert "Load remaining 1" in first_page["controls_html"]
    assert remaining_page["done"] is True
    assert remaining_page["controls_html"] == ""
    assert remaining_page["next_cursor"] == 3


def test_tree_session_nested_collection_uses_stable_child_ids_and_paging():
    nested = me.EntityCollection(**{f"k{i}": i for i in range(120)})
    session = EntityCollectionTreeSession(me.EntityCollection(group=nested), page_size=50)
    nested_id = _collection_child_id(session.root_node_id, 0)

    root_page = session.render_lazy_node(session.root_node_id, cursor=0)
    nested_page = session.render_lazy_node(nested_id)
    nested_remaining = session.render_lazy_node(nested_id, cursor=50, load_all=True)

    assert f"data-lazy-id='{nested_id}'" in root_page["html"]
    assert "Load next 50" in nested_page["controls_html"]
    assert "Load remaining 70" in nested_page["controls_html"]
    assert nested_page["done"] is False
    assert nested_page["next_cursor"] == 50
    assert nested_remaining["done"] is True
    assert nested_remaining["controls_html"] == ""
    assert nested_remaining["next_cursor"] == 120


def test_tree_session_reuses_entity_fragment_for_eager_entities(monkeypatch):
    collection = me.EntityCollection(M=me.M(1, "A/m"))
    custom_fragment = "<samp class='mammos-entity-inline'>custom eager fragment</samp>"

    monkeypatch.setattr(QuantityEntity, "_repr_html_fragment_", lambda self: custom_fragment)

    html_output = collection._repr_html_()
    session = EntityCollectionTreeSession(collection, page_size=10)
    page = session.render_lazy_node(session.root_node_id, cursor=0)

    assert custom_fragment in html_output
    assert custom_fragment in page["html"]


def test_tree_session_large_entity_leaf_is_lazy_and_replaces_on_expand(monkeypatch):
    collection = me.EntityCollection(M=me.M(np.arange(60.0), "A/m"))

    def broken_fragment(self):
        raise RuntimeError("lazy entity widget path should not call entity HTML fragments")

    monkeypatch.setattr(QuantityEntity, "_repr_html_fragment_", broken_fragment)

    session = EntityCollectionTreeSession(collection, page_size=10)
    leaf_id = _leaf_child_id(session.root_node_id, 0)
    page = session.render_lazy_node(session.root_node_id, cursor=0)
    detail = session.render_lazy_node(leaf_id)

    assert f"data-lazy-id='{leaf_id}'" in page["html"]
    assert "entity-full-value" not in page["html"]
    assert detail["patch"] == "replace-self"
    assert "<details class='lazy-leaf-details' open>" in detail["html"]
    assert "entity-full-value" in detail["html"]


@pytest.mark.parametrize(("key", "value", "meta_fragment"), _structured_leaf_cases())
def test_tree_session_special_leaves_use_lazy_details(key, value, meta_fragment):
    session = EntityCollectionTreeSession(me.EntityCollection(**{key: value}), page_size=10)
    leaf_id = _leaf_child_id(session.root_node_id, 0)

    page = session.render_lazy_node(session.root_node_id, cursor=0)
    detail = session.render_lazy_node(leaf_id)

    assert f"data-lazy-id='{leaf_id}'" in page["html"]
    assert "branch-item entity-row leaf-row" in page["html"]
    assert "<summary class='lazy-leaf-summary'>" in page["html"]
    assert "entity-full-value" not in page["html"]
    assert detail["patch"] == "replace-self"
    assert "entity-full-value" in detail["html"]
    assert meta_fragment in _normalized_html_text(detail["html"])


def test_widget_handles_root_page_request(monkeypatch):
    widget = EntityCollectionTreeWidget(me.EntityCollection(first=1, second=2), page_size=1)
    sent_messages = []
    monkeypatch.setattr(widget, "send", lambda content, buffers=None: sent_messages.append(content))

    widget._handle_message(
        widget,
        {"kind": "render-lazy", "lazy_id": widget.root_node_id, "cursor": 0},
        [],
    )

    assert sent_messages == [
        {
            "kind": "lazy-rendered",
            "lazy_id": widget.root_node_id,
            "patch": "append-children",
            "html": (
                "<div class='branch-item entity-row leaf-row'>"
                "<div class='entity-key'>first</div>"
                "<div class='entity-value'>1</div>"
                "</div>"
            ),
            "controls_html": (
                "<div class='collection-controls'>"
                "<button type='button' class='collection-control' "
                "data-lazy-action='next' data-lazy-target-id='lazy-node-0'>"
                "Load next 1"
                "</button>"
                "<button type='button' class='collection-control' "
                "data-lazy-action='all' data-lazy-target-id='lazy-node-0'>"
                "Load remaining 1"
                "</button>"
                "</div>"
            ),
            "next_cursor": 1,
            "done": False,
        }
    ]


def test_widget_handles_load_all_request(monkeypatch):
    widget = EntityCollectionTreeWidget(me.EntityCollection(**{f"k{i}": i for i in range(120)}), page_size=50)
    sent_messages = []
    monkeypatch.setattr(widget, "send", lambda content, buffers=None: sent_messages.append(content))

    widget._handle_message(
        widget,
        {"kind": "render-lazy", "lazy_id": widget.root_node_id, "cursor": 50, "load_all": True},
        [],
    )

    assert sent_messages == [
        {
            "kind": "lazy-rendered",
            "lazy_id": widget.root_node_id,
            "patch": "append-children",
            "html": "".join(
                (
                    "<div class='branch-item entity-row leaf-row'>"
                    f"<div class='entity-key'>k{i}</div>"
                    f"<div class='entity-value'>{i}</div>"
                    "</div>"
                )
                for i in range(50, 120)
            ),
            "controls_html": "",
            "next_cursor": 120,
            "done": True,
        }
    ]


def test_widget_handles_lazy_leaf_replacement(monkeypatch):
    widget = EntityCollectionTreeWidget(me.EntityCollection(M=me.M(np.arange(60.0), "A/m")), page_size=10)
    leaf_id = _leaf_child_id(widget.root_node_id, 0)
    widget._session.render_lazy_node(widget.root_node_id, cursor=0)
    detail_html = widget._session.render_lazy_node(leaf_id)["html"]
    sent_messages = []
    monkeypatch.setattr(widget, "send", lambda content, buffers=None: sent_messages.append(content))

    widget._handle_message(widget, {"kind": "render-lazy", "lazy_id": leaf_id}, [])

    assert sent_messages == [
        {
            "kind": "lazy-rendered",
            "lazy_id": leaf_id,
            "patch": "replace-self",
            "html": detail_html,
            "controls_html": "",
            "next_cursor": 0,
            "done": True,
        }
    ]


def test_widget_reports_lazy_errors(monkeypatch):
    widget = EntityCollectionTreeWidget(me.EntityCollection(a=1))
    sent_messages = []
    monkeypatch.setattr(widget, "send", lambda content, buffers=None: sent_messages.append(content))

    widget._handle_message(widget, {"kind": "render-lazy", "lazy_id": "unknown-node"}, [])

    assert len(sent_messages) == 1
    assert sent_messages[0]["kind"] == "lazy-error"
    assert sent_messages[0]["lazy_id"] == "unknown-node"
    assert "Unknown lazy node id: unknown-node" in sent_messages[0]["message"]


def test_widget_javascript_source_uses_generic_lazy_protocol_without_loading_indicator():
    js_text = (Path(me.__file__).resolve().parent / "_entity_collection_tree.js").read_text(encoding="utf-8")

    assert 'kind: "render-lazy"' in js_text
    assert 'if (message.patch === "replace-self")' in js_text
    assert 'if (target.dataset.lazyPatch === "append-children")' in js_text
    assert "button.dataset.lazyTargetId" in js_text
    assert 'el.addEventListener("toggle", handleToggle, true);' in js_text
    assert 'el.addEventListener("click", handleCollectionControl);' in js_text
    assert "Loading..." not in js_text
    assert "Load more" not in js_text
