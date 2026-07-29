import html
import re
from pathlib import Path

import mammos_units as u
import numpy as np
import pytest

import mammos_entity as me
from mammos_entity._entity import Entity
from mammos_entity._entity_collection_tree import (
    _STATIC_ELLIPSIS_CHILD,
    _STATIC_MAX_CHILDREN_PER_COLLECTION,
    _STATIC_PREVIEW_NOTE,
    EntityCollectionTreeSession,
    EntityCollectionTreeWidget,
    render_entity_collection_text,
)
from mammos_entity._entity_collection_tree import _common as tree_common
from mammos_entity._entity_collection_tree import _html_helpers as tree_html


class _BrokenRepr:
    def __repr__(self):
        raise RuntimeError("broken repr")


def _nested_collection(depth: int) -> me.EntityCollection:
    collection = me.EntityCollection(leaf=1)
    for level in range(depth, 0, -1):
        collection = me.EntityCollection(**{f"level_{level}": collection})
    return collection


def _normalized_html_text(fragment: str) -> str:
    return html.unescape(fragment).replace("\xa0", " ")


def _lazy_node_id(html_fragment: str, patch: str) -> str:
    match = re.search(rf"data-lazy-id='([^']+)' data-lazy-patch='{re.escape(patch)}'", html_fragment)
    assert match is not None
    return match.group(1)


def _structured_leaf_cases() -> list[tuple[str, object, str]]:
    return [
        ("quantity", u.Quantity(np.arange(60.0), "A / m"), "shape=(60,)"),
        ("array", np.arange(60.0), "shape=(60,)"),
        ("list", list(range(60)), "len=60"),
        ("tuple", tuple(range(60)), "len=60"),
        ("mapping", {f"k{i}": i for i in range(60)}, "len=60"),
    ]


def _assert_js_free(html_fragment: str) -> None:
    assert "onclick=" not in html_fragment
    assert "onkeydown=" not in html_fragment
    assert "data-expanded=" not in html_fragment


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
    _assert_js_free(fragment)
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
    _assert_js_free(html_output)
    assert "long&nbsp;collection&nbsp;description" not in html_output
    assert "long&nbsp;entity&nbsp;description" not in html_output
    assert "overflow-wrap: anywhere;" in html_output
    assert "white-space: pre-wrap;" in html_output


def test_structured_leaf_open_state_css_targets_details_element():
    html_output = me.EntityCollection(values=list(range(60)))._repr_html_()

    assert "<details class='mammos-entity-inline mammos-compact-value lazy-leaf-details'>" in html_output
    assert ".lazy-leaf-details[open] > .lazy-leaf-summary > .entity-toggle:first-child" in html_output
    assert ".lazy-leaf-details[open] > .lazy-leaf-summary > .entity-toggle:nth-child(2)" in html_output
    assert ".lazy-leaf-details[open] > .entity-expanded-details" in html_output


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


def test_render_entity_collection_text_uses_bounded_collection_repr_style():
    collection = me.EntityCollection(**{f"k{i}": i for i in range(30)})

    text_output = render_entity_collection_text(collection)

    assert text_output.startswith("EntityCollection(\n")
    assert "    k19=19," in text_output
    assert "    k20=20," not in text_output
    assert "    ...," in text_output


def test_render_entity_collection_text_keeps_root_ellipsis_when_global_budget_is_exhausted():
    repeated_nested = me.EntityCollection(
        description="the collection description",
        **{f"entity{j}": j for j in range(400)},
    )
    collection = me.EntityCollection(**{f"element-{i}": repeated_nested for i in range(1000)})

    text_output = render_entity_collection_text(collection)

    assert "element-0=EntityCollection(" in text_output
    assert "\n    ...,\n)" in text_output


def test_render_entity_collection_text_bounds_large_quantity_leaf_values():
    collection = me.EntityCollection(q=u.Quantity(np.arange(60.0), "A / m"))

    text_output = render_entity_collection_text(collection)

    assert "q=<Quantity [0. 1. 2. ... 57. 58. 59.] A / m> (shape=(60,))," in text_output
    assert "30." not in text_output


def test_render_entity_collection_text_bounds_large_entity_values():
    collection = me.EntityCollection(M=me.M(np.arange(60.0), "A/m", description="desc"))

    text_output = render_entity_collection_text(collection)

    assert "Entity(" in text_output
    assert "value=array([0. 1. 2. ... 57. 58. 59.])" in text_output
    assert "unit='A / m'" in text_output
    assert "description='desc'" in text_output
    assert "30." not in text_output


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
    assert data["text/plain"].startswith("EntityCollection(\n")
    assert "alpha=EntityCollection(" in data["text/plain"]
    assert "beta=EntityCollection(" in data["text/plain"]
    assert metadata == {}


@pytest.mark.parametrize(
    ("value", "fallback_fragment"),
    [
        ([_BrokenRepr(), *range(60)], "list object at"),
        ({"broken": _BrokenRepr(), **{f"k{i}": i for i in range(60)}}, "dict object at"),
    ],
)
def test_broken_nested_repr_uses_safe_fallback_across_renderers(value, fallback_fragment):
    collection = me.EntityCollection(value=value)

    repr_output = repr(collection)
    html_output = _normalized_html_text(collection._repr_html_())
    text_output = render_entity_collection_text(collection)
    mime_data, _ = collection._repr_mimebundle_()

    assert fallback_fragment in repr_output
    assert fallback_fragment in html_output
    assert fallback_fragment in text_output
    assert fallback_fragment in _normalized_html_text(mime_data["text/html"])
    assert fallback_fragment in mime_data["text/plain"]

    session = EntityCollectionTreeSession(collection)
    page = session.render_lazy_node(session.root_node_id)
    leaf_id = _lazy_node_id(page["html"], "replace-self")
    detail = session.render_lazy_node(leaf_id)

    assert detail["patch"] == "replace-self"
    assert fallback_fragment in _normalized_html_text(detail["html"])


def test_tree_session_root_html_starts_open_and_first_page_is_lazy():
    session = EntityCollectionTreeSession(me.EntityCollection(a=1, b=2, c=3), page_size=2)

    root_html = session.render_root_html()
    first_page = session.render_lazy_node(session.root_node_id)
    remaining_page = session.render_lazy_node(session.root_node_id, load_all=True)

    assert "<details class='mammos-entity-collection root-node' open" in root_html
    assert "data-lazy-cursor" not in root_html
    assert first_page["done"] is False
    assert "Load next 1" in first_page["controls_html"]
    assert "Load remaining 1" in first_page["controls_html"]
    assert remaining_page["done"] is True
    assert remaining_page["controls_html"] == ""


@pytest.mark.parametrize("page_size", [0, -1])
def test_tree_session_rejects_non_positive_page_size(page_size: int):
    with pytest.raises(ValueError, match="page_size must be greater than zero"):
        EntityCollectionTreeSession(me.EntityCollection(a=1), page_size=page_size)


def test_tree_session_nested_collection_uses_stable_child_ids_and_paging():
    nested = me.EntityCollection(**{f"k{i}": i for i in range(120)})
    session = EntityCollectionTreeSession(me.EntityCollection(group=nested), page_size=50)

    root_page = session.render_lazy_node(session.root_node_id)
    nested_id = _lazy_node_id(root_page["html"], "append-children")
    nested_page = session.render_lazy_node(nested_id)
    nested_remaining = session.render_lazy_node(nested_id, load_all=True)

    assert f"data-lazy-id='{nested_id}'" in root_page["html"]
    assert "Load next 50" in nested_page["controls_html"]
    assert "Load remaining 70" in nested_page["controls_html"]
    assert nested_page["done"] is False
    assert nested_remaining["done"] is True
    assert nested_remaining["controls_html"] == ""


def test_tree_session_paginates_over_python_snapshot_until_release():
    collection = me.EntityCollection(**{f"k{i}": i for i in range(6)})
    session = EntityCollectionTreeSession(collection, page_size=2)

    first_page = session.render_lazy_node(session.root_node_id)
    del collection["k0"]
    collection["new"] = 6
    second_page = session.render_lazy_node(session.root_node_id)
    remaining_page = session.render_lazy_node(session.root_node_id, load_all=True)

    assert "k0" in first_page["html"]
    assert "k1" in first_page["html"]
    assert "k2" in second_page["html"]
    assert "k3" in second_page["html"]
    assert "k4" not in second_page["html"]
    assert "k4" in remaining_page["html"]
    assert "k5" in remaining_page["html"]
    assert "new" not in remaining_page["html"]

    session.release_lazy_descendants(session.root_node_id)
    reloaded_page = session.render_lazy_node(session.root_node_id)

    assert "k0" not in reloaded_page["html"]
    assert "k1" in reloaded_page["html"]
    assert "k2" in reloaded_page["html"]


def test_tree_session_registered_collection_survives_parent_mutation():
    nested = me.EntityCollection(value=1)
    collection = me.EntityCollection(before=0, group=nested, after=2)
    session = EntityCollectionTreeSession(collection)
    root_page = session.render_lazy_node(session.root_node_id)
    nested_id = _lazy_node_id(root_page["html"], "append-children")

    del collection["before"]
    nested_page = session.render_lazy_node(nested_id)

    assert "<div class='entity-key'>value</div>" in nested_page["html"]
    assert "<div class='entity-value'>1</div>" in nested_page["html"]


def test_tree_session_registered_leaf_survives_parent_mutation():
    collection = me.EntityCollection(before=0, values=list(range(60)))
    session = EntityCollectionTreeSession(collection)
    root_page = session.render_lazy_node(session.root_node_id)
    leaf_id = _lazy_node_id(root_page["html"], "replace-self")

    del collection["before"]
    detail = session.render_lazy_node(leaf_id)

    assert detail["patch"] == "replace-self"
    assert "entity-full-value" in detail["html"]
    assert "59" in detail["html"]


def test_tree_session_defers_expanded_sequence_formatting(monkeypatch):
    expanded_calls = 0
    original_formatter = tree_common._format_sequence_repr_expanded

    def counted_formatter(value):
        nonlocal expanded_calls
        expanded_calls += 1
        return original_formatter(value)

    monkeypatch.setattr(tree_common, "_format_sequence_repr_expanded", counted_formatter)
    session = EntityCollectionTreeSession(me.EntityCollection(values=list(range(60))))

    page = session.render_lazy_node(session.root_node_id)
    leaf_id = _lazy_node_id(page["html"], "replace-self")
    assert expanded_calls == 0

    session.render_lazy_node(leaf_id)
    assert expanded_calls == 1


def test_tree_session_does_not_call_full_repr_for_truncated_sequence():
    repr_calls = 0

    class CountedList(list):
        def __repr__(self):
            nonlocal repr_calls
            repr_calls += 1
            return super().__repr__()

    session = EntityCollectionTreeSession(me.EntityCollection(values=CountedList(range(60))))

    page = session.render_lazy_node(session.root_node_id)
    leaf_id = _lazy_node_id(page["html"], "replace-self")
    assert repr_calls == 0

    session.render_lazy_node(leaf_id)
    assert repr_calls == 0


def test_tree_session_defers_expanded_entity_formatting(monkeypatch):
    expanded_calls = 0
    original_formatter = tree_html._format_array_repr_expanded

    def counted_formatter(value):
        nonlocal expanded_calls
        expanded_calls += 1
        return original_formatter(value)

    monkeypatch.setattr(tree_html, "_format_array_repr_expanded", counted_formatter)
    session = EntityCollectionTreeSession(me.EntityCollection(M=me.M(np.arange(60.0), "A/m")))

    page = session.render_lazy_node(session.root_node_id)
    leaf_id = _lazy_node_id(page["html"], "replace-self")
    assert expanded_calls == 0

    session.render_lazy_node(leaf_id)
    assert expanded_calls == 1


def test_tree_session_releases_registered_descendants():
    nested = me.EntityCollection(values=list(range(60)))
    session = EntityCollectionTreeSession(me.EntityCollection(group=nested))
    root_page = session.render_lazy_node(session.root_node_id)
    nested_id = _lazy_node_id(root_page["html"], "append-children")
    nested_page = session.render_lazy_node(nested_id)
    leaf_id = _lazy_node_id(nested_page["html"], "replace-self")

    assert set(session._lazy_nodes) == {session.root_node_id, nested_id, leaf_id}

    session.release_lazy_descendants(session.root_node_id)

    assert set(session._lazy_nodes) == {session.root_node_id}
    with pytest.raises(KeyError, match=f"Unknown lazy node id: {nested_id}"):
        session.render_lazy_node(nested_id)

    reloaded_root_page = session.render_lazy_node(session.root_node_id)
    reloaded_nested_id = _lazy_node_id(reloaded_root_page["html"], "append-children")
    assert reloaded_nested_id != nested_id
    assert "values" in session.render_lazy_node(reloaded_nested_id)["html"]


def test_tree_session_reuses_entity_fragment_for_eager_entities(monkeypatch):
    collection = me.EntityCollection(M=me.M(1, "A/m"))
    custom_fragment = "<samp class='mammos-entity-inline'>custom eager fragment</samp>"

    monkeypatch.setattr(Entity, "_repr_html_fragment_", lambda self: custom_fragment)

    html_output = collection._repr_html_()
    session = EntityCollectionTreeSession(collection, page_size=10)
    page = session.render_lazy_node(session.root_node_id)

    assert custom_fragment in html_output
    assert custom_fragment in page["html"]


def test_tree_session_large_entity_leaf_is_lazy_and_replaces_on_expand(monkeypatch):
    collection = me.EntityCollection(M=me.M(np.arange(60.0), "A/m"))

    def broken_fragment(self):
        raise RuntimeError("lazy entity widget path should not call entity HTML fragments")

    monkeypatch.setattr(Entity, "_repr_html_fragment_", broken_fragment)

    session = EntityCollectionTreeSession(collection, page_size=10)
    page = session.render_lazy_node(session.root_node_id)
    leaf_id = _lazy_node_id(page["html"], "replace-self")
    detail = session.render_lazy_node(leaf_id)

    assert f"data-lazy-id='{leaf_id}'" in page["html"]
    assert "entity-full-value" not in page["html"]
    assert detail["patch"] == "replace-self"
    assert "<details class='lazy-leaf-details' open>" in detail["html"]
    assert "entity-full-value" in detail["html"]


@pytest.mark.parametrize(("key", "value", "meta_fragment"), _structured_leaf_cases())
def test_tree_session_special_leaves_use_lazy_details(key, value, meta_fragment):
    session = EntityCollectionTreeSession(me.EntityCollection(**{key: value}), page_size=10)

    page = session.render_lazy_node(session.root_node_id)
    leaf_id = _lazy_node_id(page["html"], "replace-self")
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
        {"kind": "render-lazy", "lazy_id": widget.root_node_id, "request_id": 11},
        [],
    )

    assert len(sent_messages) == 1
    message = sent_messages[0]
    assert message["kind"] == "lazy-rendered"
    assert message["lazy_id"] == widget.root_node_id
    assert message["request_id"] == 11
    assert message["patch"] == "append-children"
    assert "<div class='entity-key'>first</div>" in message["html"]
    assert "Load next 1" in message["controls_html"]
    assert "Load remaining 1" in message["controls_html"]
    assert message["done"] is False


def test_widget_handles_load_all_request(monkeypatch):
    widget = EntityCollectionTreeWidget(me.EntityCollection(**{f"k{i}": i for i in range(120)}), page_size=50)
    sent_messages = []
    monkeypatch.setattr(widget, "send", lambda content, buffers=None: sent_messages.append(content))

    widget._handle_message(
        widget,
        {"kind": "render-lazy", "lazy_id": widget.root_node_id, "request_id": 12},
        [],
    )
    sent_messages.clear()
    widget._handle_message(
        widget,
        {"kind": "render-lazy", "lazy_id": widget.root_node_id, "request_id": 13, "load_all": True},
        [],
    )

    assert len(sent_messages) == 1
    message = sent_messages[0]
    assert message["kind"] == "lazy-rendered"
    assert message["lazy_id"] == widget.root_node_id
    assert message["request_id"] == 13
    assert message["patch"] == "append-children"
    assert "<div class='entity-key'>k50</div>" in message["html"]
    assert "<div class='entity-key'>k119</div>" in message["html"]
    assert message["controls_html"] == ""
    assert message["done"] is True


def test_widget_handles_lazy_leaf_replacement(monkeypatch):
    widget = EntityCollectionTreeWidget(me.EntityCollection(M=me.M(np.arange(60.0), "A/m")), page_size=10)
    sent_messages = []
    monkeypatch.setattr(widget, "send", lambda content, buffers=None: sent_messages.append(content))

    widget._handle_message(
        widget,
        {"kind": "render-lazy", "lazy_id": widget.root_node_id, "request_id": 13},
        [],
    )
    leaf_id = _lazy_node_id(sent_messages.pop()["html"], "replace-self")
    widget._handle_message(widget, {"kind": "render-lazy", "lazy_id": leaf_id, "request_id": 14}, [])

    assert len(sent_messages) == 1
    message = sent_messages[0]
    assert message["kind"] == "lazy-rendered"
    assert message["lazy_id"] == leaf_id
    assert message["request_id"] == 14
    assert message["patch"] == "replace-self"
    assert "<details class='lazy-leaf-details' open>" in message["html"]
    assert message["controls_html"] == ""
    assert message["done"] is True


def test_widget_reports_lazy_errors(monkeypatch):
    widget = EntityCollectionTreeWidget(me.EntityCollection(a=1))
    sent_messages = []
    monkeypatch.setattr(widget, "send", lambda content, buffers=None: sent_messages.append(content))

    widget._handle_message(widget, {"kind": "render-lazy", "lazy_id": "unknown-node", "request_id": 15}, [])

    assert len(sent_messages) == 1
    assert sent_messages[0]["kind"] == "lazy-error"
    assert sent_messages[0]["lazy_id"] == "unknown-node"
    assert sent_messages[0]["request_id"] == 15
    assert "Unknown lazy node id: unknown-node" in sent_messages[0]["message"]


def test_widget_handles_release_request(monkeypatch):
    widget = EntityCollectionTreeWidget(me.EntityCollection(group=me.EntityCollection(value=1)))
    sent_messages = []
    monkeypatch.setattr(widget, "send", lambda content, buffers=None: sent_messages.append(content))
    root_page = widget._session.render_lazy_node(widget.root_node_id)
    nested_id = _lazy_node_id(root_page["html"], "append-children")

    widget._handle_message(widget, {"kind": "release-lazy", "lazy_id": widget.root_node_id}, [])

    assert sent_messages == []
    with pytest.raises(KeyError, match=f"Unknown lazy node id: {nested_id}"):
        widget._session.render_lazy_node(nested_id)


def test_widget_javascript_source_uses_generic_lazy_protocol_without_loading_indicator():
    js_text = Path(EntityCollectionTreeWidget._esm._path).read_text(encoding="utf-8")

    assert 'kind: "render-lazy"' in js_text
    assert "request_id: requestId" in js_text
    assert 'if (message.patch === "replace-self")' in js_text
    assert "responseMatchesRequest(node, message)" in js_text
    assert "invalidateLazyRequest(target)" in js_text
    assert "delete node.dataset.lazyRequestId" in js_text
    assert 'kind: "release-lazy"' in js_text
    assert "lazyCursor" not in js_text
    assert "button.dataset.lazyTargetId" in js_text
    assert 'el.addEventListener("toggle", handleToggle, true);' in js_text
    assert 'el.addEventListener("click", handleCollectionControl);' in js_text
    assert "Loading..." not in js_text
    assert "Load more" not in js_text
