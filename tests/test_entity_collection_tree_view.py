import html
import json
import subprocess
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


def _inner_samp_html(fragment: str) -> str:
    start = fragment.find(">")
    end = fragment.rfind("</samp>")
    assert start != -1
    assert end != -1
    return fragment[start + 1 : end]


def _structured_leaf_cases():
    return [
        ("quantity", u.Quantity(np.arange(60.0), "A / m"), "shape=(60,)"),
        ("array", np.arange(60.0), "shape=(60,)"),
        ("list", list(range(60)), "len=60"),
        ("tuple", tuple(range(60)), "len=60"),
        ("mapping", {f"k{i}": i for i in range(60)}, "len=60"),
    ]


def _collection_child_id(parent_id: str, index: int) -> str:
    return f"{parent_id}-collection-{index}"


def _leaf_child_id(parent_id: str, index: int) -> str:
    return f"{parent_id}-leaf-{index}"


def test_repr_html_uses_new_tree_view_markup():
    inner = me.EntityCollection("inner descr", T=2)
    outer = me.EntityCollection("outer descr", outer=1, inner=inner)

    html = outer._repr_html_()

    assert html.startswith("<style>")
    assert "<details class='mammos-entity-collection root-node' open>" in html
    assert "<span class='collection-title'>EntityCollection</span>" in html
    assert "outer descr" in html
    assert "inner descr" in html
    assert "<details class='branch-item branch-node'>" in html
    assert "data-node-id='collection-node-0'" not in html
    assert "onclick=" not in html
    assert "onkeydown=" not in html
    assert ".collection-children > .collection-note::before" in html
    assert ".mammos-entity-inline .entity-description" in html


def test_descriptions_use_wrap_friendly_html_and_css():
    collection = me.EntityCollection(
        description="long collection description that should wrap",
        M=me.M(1, "A/m", description="long entity description that should wrap"),
    )

    html = collection._repr_html_()

    assert "long&nbsp;collection&nbsp;description" not in html
    assert "long&nbsp;entity&nbsp;description" not in html
    assert "<em class='entity-description'>" in html
    assert "overflow-wrap: anywhere;" in html
    assert "white-space: pre-wrap;" in html


def test_repr_html_truncates_nested_collections_at_static_depth_limit():
    html = _normalized_html_text(_nested_collection(depth=5)._repr_html_())

    assert _STATIC_ELLIPSIS_CHILD in html
    assert _STATIC_PREVIEW_NOTE in html
    assert "class='static-preview-note'" in html
    assert "level_5" in html
    assert "<div class='entity-key'>leaf</div>" not in html


def test_repr_html_truncates_large_flat_collections():
    collection = me.EntityCollection(**{f"k{i}": i for i in range(600)})

    html = _normalized_html_text(collection._repr_html_())

    assert _STATIC_ELLIPSIS_CHILD in html
    assert _STATIC_PREVIEW_NOTE in html
    assert "class='static-preview-note'" in html
    assert html.count("class='branch-item entity-row") == _STATIC_MAX_CHILDREN_PER_COLLECTION


def test_repr_html_limits_each_collection_to_twenty_children():
    collection = me.EntityCollection(**{f"k{i}": i for i in range(30)})

    html = _normalized_html_text(collection._repr_html_())

    assert "<div class='entity-key'>k19</div>" in html
    assert "<div class='entity-key'>k20</div>" not in html
    assert _STATIC_ELLIPSIS_CHILD in html
    assert _STATIC_PREVIEW_NOTE in html


def test_repr_html_limits_nested_collection_children_to_twenty():
    inner = me.EntityCollection(**{f"child_{i}": i for i in range(25)})
    outer = me.EntityCollection(nested=inner)

    html = _normalized_html_text(outer._repr_html_())

    assert "<div class='entity-key'>child_19</div>" in html
    assert "<div class='entity-key'>child_20</div>" not in html
    assert html.count(_STATIC_ELLIPSIS_CHILD) >= 1
    assert _STATIC_PREVIEW_NOTE in html


def test_repr_html_keeps_root_ellipsis_when_nested_branches_exhaust_global_budget():
    repeated_nested = me.EntityCollection(
        description="the collection description",
        **{f"entity{j}": j for j in range(400)},
    )
    collection = me.EntityCollection(**{f"element-{i}": repeated_nested for i in range(1000)})

    html = collection._repr_html_()

    assert "<div class='static-preview-note'>" in html
    assert "<div class='branch-item collection-note'>...</div></div><div class='static-preview-note'>" in html


def test_repr_html_omits_static_preview_note_when_not_truncated():
    collection = me.EntityCollection(a=1, b=2, c=3)

    html = _normalized_html_text(collection._repr_html_())

    assert _STATIC_PREVIEW_NOTE not in html
    assert "class='static-preview-note'" not in html


def test_tree_session_renders_root_lazily_and_paginates():
    collection = me.EntityCollection(
        first=1,
        second=2,
        nested=me.EntityCollection(inner=3),
        fourth=4,
        fifth=5,
    )
    session = EntityCollectionTreeSession(collection, page_size=2)

    root_html = session.render_root_html()
    first_page = session.render_lazy_node(session.root_node_id, cursor=0)
    second_page = session.render_lazy_node(session.root_node_id, cursor=2)
    third_page = session.render_lazy_node(session.root_node_id, cursor=4)

    assert "<details class='mammos-entity-collection root-node' open" in root_html
    assert "data-lazy-cursor='0'" in root_html
    assert first_page["done"] is False
    assert "Load next 2" in first_page["controls_html"]
    assert "Load remaining 3" in first_page["controls_html"]
    assert first_page["next_cursor"] == 2
    assert second_page["done"] is False
    assert "Load next 1" in second_page["controls_html"]
    assert second_page["next_cursor"] == 4
    assert f"data-lazy-id='{_collection_child_id(session.root_node_id, 2)}'" in second_page["html"]
    assert third_page["done"] is True
    assert third_page["controls_html"] == ""
    assert third_page["next_cursor"] == 5


def test_repr_mimebundle_includes_widget_and_html_fallback():
    bundle = me.EntityCollection(a=1)._repr_mimebundle_()
    data, metadata = bundle

    assert "application/vnd.jupyter.widget-view+json" in data
    assert "text/html" in data
    assert "text/plain" in data
    assert data["text/html"].startswith("<style>")
    assert data["text/plain"] == "EntityCollection(1 item · a)"
    assert metadata == {}


def test_widget_handles_lazy_child_request(monkeypatch):
    widget = EntityCollectionTreeWidget(me.EntityCollection(first=1, second=2), page_size=1)
    sent_messages = []
    monkeypatch.setattr(widget, "send", lambda content, buffers=None: sent_messages.append(content))

    widget._handle_message(
        widget,
        {
            "kind": "render-lazy",
            "lazy_id": widget.root_node_id,
            "cursor": 0,
        },
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


def test_widget_javascript_handles_root_collection_node():
    js_file = Path(me.__file__).resolve().parent / "_entity_collection_tree.js"
    js_text = js_file.read_text(encoding="utf-8")

    assert "if (root.dataset.lazyId === lazyId)" in js_text


def test_widget_javascript_captures_nested_toggle_and_has_no_loading_indicator():
    js_file = Path(me.__file__).resolve().parent / "_entity_collection_tree.js"
    css_file = Path(me.__file__).resolve().parent / "_entity_collection_tree.css"
    js_text = js_file.read_text(encoding="utf-8")
    css_text = css_file.read_text(encoding="utf-8")

    assert 'el.addEventListener("toggle", handleToggle, true);' in js_text
    assert 'el.removeEventListener("toggle", handleToggle, true);' in js_text
    assert 'kind: "render-lazy"' in js_text
    assert 'el.addEventListener("click", handleCollectionControl);' in js_text
    assert 'el.removeEventListener("click", handleCollectionControl);' in js_text
    assert "if (!message.done) {" not in js_text
    assert "Loading..." not in js_text
    assert "Load more" not in js_text
    assert 'node.dataset.hasControls = htmlText ? "true" : "false";' in js_text
    assert 'node.dataset.hasControls = "false";' in js_text
    assert "button.dataset.lazyTargetId" in js_text
    assert ".mammos-entity-collection .collection-footer" in css_text
    assert "display: inline-flex;" in css_text
    assert 'details[data-has-controls="true"] > .collection-footer > .collection-controls::before' in css_text
    assert 'details[data-has-controls="true"] > .collection-children > .branch-item:last-child::after' in css_text
    assert ".mammos-entity-collection .collection-control" in css_text
    assert ".mammos-entity-collection summary:hover::marker" in css_text
    assert ".mammos-entity-collection .entity-row.leaf-row" in css_text
    assert ".mammos-entity-inline .lazy-leaf-summary:hover .entity-toggle" in css_text
    assert ".mammos-entity-inline .lazy-leaf-summary {" in css_text
    assert ".mammos-entity-inline .lazy-leaf-details[open] > .entity-expanded-details" in css_text
    assert '[data-expanded="true"]' not in css_text


def test_repr_mimebundle_does_not_recurse_into_collection_repr(monkeypatch):
    collection = me.EntityCollection(
        alpha=me.EntityCollection(left=me.EntityCollection(a=me.M(1, "A/m"))),
        beta=me.EntityCollection(right=me.EntityCollection(b=2)),
    )

    def broken_repr(self):
        raise RuntimeError("repr should not be used for mimebundle generation")

    monkeypatch.setattr(me.EntityCollection, "__repr__", broken_repr)

    data, metadata = collection._repr_mimebundle_()

    assert "application/vnd.jupyter.widget-view+json" in data
    assert data["text/plain"] == "EntityCollection(2 items · alpha, beta)"
    assert data["text/html"].startswith("<style>")
    assert metadata == {}


def test_tree_view_reuses_entity_html_fragment_for_eager_entities(monkeypatch):
    collection = me.EntityCollection(M=me.M(1, "A/m"))
    custom_fragment = "<samp class='mammos-entity-inline'>custom eager fragment</samp>"

    monkeypatch.setattr(QuantityEntity, "_repr_html_fragment_", lambda self: custom_fragment)

    html = collection._repr_html_()
    session = EntityCollectionTreeSession(collection, page_size=10)
    page = session.render_lazy_node(session.root_node_id, cursor=0)

    assert custom_fragment in html
    assert custom_fragment in page["html"]


def test_widget_large_entity_lazy_render_does_not_require_entity_html_fragment(monkeypatch):
    collection = me.EntityCollection(M=me.M(np.arange(60.0), "A/m"))

    def broken_fragment(self):
        raise RuntimeError("lazy entity widget path should not call entity HTML fragments")

    monkeypatch.setattr(QuantityEntity, "_repr_html_fragment_", broken_fragment)

    session = EntityCollectionTreeSession(collection, page_size=10)
    leaf_id = _leaf_child_id(session.root_node_id, 0)
    page = session.render_lazy_node(session.root_node_id, cursor=0)
    detail = session.render_lazy_node(leaf_id)

    assert f"data-lazy-id='{leaf_id}'" in page["html"]
    assert detail["patch"] == "replace-self"
    assert "<details class='lazy-leaf-details' open>" in detail["html"]


@pytest.mark.parametrize("count", [1, 3, 7, 60, 500])
@pytest.mark.parametrize("description", ["", "desc"])
def test_entity_repr_html_uses_tree_markup(count, description):
    if count == 1:
        entity = me.M(1.0, "A/m", description=description)
    else:
        entity = me.M(np.arange(float(count)), "A/m", description=description)

    html = entity._repr_html_()
    fragment = entity._repr_html_fragment_()

    assert html.startswith("<style>")
    assert fragment in html
    assert entity.ontology_label in _normalized_html_text(fragment)
    assert "onclick=" not in fragment
    assert "onkeydown=" not in fragment
    assert "data-expanded=" not in fragment
    if description:
        assert description in _normalized_html_text(fragment)
    else:
        assert "<em>desc</em>" not in fragment
    if count >= 60:
        assert "<details class='lazy-leaf-details'>" in fragment
        assert "<details class='lazy-leaf-details' open>" not in fragment
        assert "<summary class='lazy-leaf-summary'>" in fragment
        assert "entity-full-value" in fragment
    else:
        assert "<details class='lazy-leaf-details'>" not in fragment


def test_widget_root_html_is_collapsible_and_open_by_default():
    session = EntityCollectionTreeSession(me.EntityCollection(a=1), page_size=10)
    root_html = session.render_root_html()

    assert "<details class='mammos-entity-collection root-node' open" in root_html
    assert "<summary><span class='collection-title'>EntityCollection</span>" in root_html


@pytest.mark.parametrize("count", [1, 3, 7, 60, 500])
@pytest.mark.parametrize("description", ["", "desc"])
def test_static_tree_view_entity_rendering_uses_tree_markup(count, description):
    value = 1.0 if count == 1 else np.arange(float(count))
    entity = me.M(value, "A/m", description=description)
    collection = me.EntityCollection(M=entity)

    static_html = collection._repr_html_()

    assert entity.ontology_label in _normalized_html_text(static_html)
    assert "onclick=" not in static_html
    assert "onkeydown=" not in static_html
    assert "data-expanded=" not in static_html
    if description:
        assert description in _normalized_html_text(static_html)
    else:
        assert "<em>desc</em>" not in static_html
    if count >= 60:
        assert "<details class='lazy-leaf-details'>" in static_html
        assert "<details class='lazy-leaf-details' open>" not in static_html
        assert "<summary class='lazy-leaf-summary'>" in static_html
        assert "entity-full-value" in static_html
        assert "data-lazy-id=" not in static_html
    else:
        assert "<details class='lazy-leaf-details'>" not in static_html


@pytest.mark.parametrize("count", [1, 3, 7])
@pytest.mark.parametrize("description", ["", "desc"])
def test_widget_tree_view_small_entity_rendering_is_eager(count, description):
    value = 1.0 if count == 1 else np.arange(float(count))
    entity = me.M(value, "A/m", description=description)
    session = EntityCollectionTreeSession(me.EntityCollection(M=entity), page_size=10)

    page = session.render_lazy_node(session.root_node_id, cursor=0)

    normalized_page = _normalized_html_text(page["html"])
    assert entity.ontology_label in normalized_page
    assert "onclick=" not in page["html"]
    assert "onkeydown=" not in page["html"]
    assert "data-expanded=" not in page["html"]
    assert "data-lazy-id=" not in page["html"]
    assert "<details class='lazy-leaf-details'" not in page["html"]
    if description:
        assert description in normalized_page


@pytest.mark.parametrize("count", [60, 500])
@pytest.mark.parametrize("description", ["", "desc"])
def test_widget_tree_view_large_entity_loading_is_lazy(count, description):
    entity = me.M(np.arange(float(count)), "A/m", description=description)
    session = EntityCollectionTreeSession(me.EntityCollection(M=entity), page_size=10)
    leaf_id = _leaf_child_id(session.root_node_id, 0)

    page = session.render_lazy_node(session.root_node_id, cursor=0)
    detail = session.render_lazy_node(leaf_id)

    normalized_page = _normalized_html_text(page["html"])
    normalized_detail = _normalized_html_text(detail["html"])
    assert entity.ontology_label in normalized_page
    assert f"data-lazy-id='{leaf_id}'" in page["html"]
    assert "<details class='lazy-leaf-details'" in page["html"]
    assert "<summary class='lazy-leaf-summary'>" in page["html"]
    assert "entity-full-value" not in page["html"]
    assert "onclick=" not in page["html"]
    assert "onkeydown=" not in page["html"]
    assert "data-expanded=" not in page["html"]
    assert detail["patch"] == "replace-self"
    assert "<details class='lazy-leaf-details' open>" in detail["html"]
    assert "entity-full-value" in detail["html"]
    assert "onclick=" not in detail["html"]
    assert "onkeydown=" not in detail["html"]
    assert "data-expanded=" not in detail["html"]
    if description:
        assert description in normalized_page
    assert entity.ontology_label not in normalized_detail


def test_widget_handles_lazy_entity_request(monkeypatch):
    entity = me.M(np.arange(60.0), "A/m")
    widget = EntityCollectionTreeWidget(me.EntityCollection(M=entity), page_size=10)
    leaf_id = _leaf_child_id(widget.root_node_id, 0)
    widget._session.render_lazy_node(widget.root_node_id, cursor=0)
    detail_html = widget._session.render_lazy_node(leaf_id)["html"]
    sent_messages = []
    monkeypatch.setattr(widget, "send", lambda content, buffers=None: sent_messages.append(content))

    widget._handle_message(
        widget,
        {
            "kind": "render-lazy",
            "lazy_id": leaf_id,
        },
        [],
    )

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


def test_widget_javascript_clicking_lazy_entity_leaf_requests_and_replaces(tmp_path):
    session = EntityCollectionTreeSession(
        me.EntityCollection(M=me.M(np.arange(60.0), "A/m")),
        page_size=10,
    )
    leaf_id = _leaf_child_id(session.root_node_id, 0)
    root_html = session.render_root_html()
    page = session.render_lazy_node(session.root_node_id, cursor=0)
    detail = session.render_lazy_node(leaf_id)
    js_source_path = Path(me.__file__).resolve().parent / "_entity_collection_tree.js"
    script_path = tmp_path / "lazy_entity_click_test.cjs"
    script_path.write_text(
        f"""
const fs = require("fs");
const vm = require("vm");

const ROOT_HTML = {json.dumps(root_html)};
const PAGE_HTML = {json.dumps(page["html"])};
const DETAIL_HTML = {json.dumps(detail["html"])};
const ROOT_LAZY_ID = {json.dumps(session.root_node_id)};
const LEAF_LAZY_ID = {json.dumps(leaf_id)};
const JS_SOURCE_PATH = {json.dumps(str(js_source_path))};

function fail(message) {{
  throw new Error(message);
}}

function assert(condition, message) {{
  if (!condition) {{
    fail(message);
  }}
}}

class FakeFragment {{
  constructor(children = []) {{
    this.children = children;
    for (const child of this.children) {{
      child.parent = this;
    }}
  }}

  get firstElementChild() {{
    return this.children[0] ?? null;
  }}
}}

class FakeElement {{
  constructor(tagName, classNames = []) {{
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.parent = null;
    this.dataset = {{}};
    this._classNames = [...classNames];
    this.className = this._classNames.join(" ");
    this.open = false;
  }}

  append(child) {{
    if (child instanceof FakeFragment) {{
      for (const fragmentChild of child.children) {{
        this.append(fragmentChild);
      }}
      return;
    }}
    child.parent = this;
    this.children.push(child);
  }}

  replaceWith(replacement) {{
    const siblings = this.parent?.children;
    if (!siblings) {{
      fail("replaceWith called without parent");
    }}
    const index = siblings.indexOf(this);
    if (index === -1) {{
      fail("replaceWith could not find node in parent");
    }}
    replacement.parent = this.parent;
    siblings.splice(index, 1, replacement);
  }}

  querySelector(selector) {{
    return this.querySelectorAll(selector)[0] ?? null;
  }}

  querySelectorAll(selector) {{
    const matches = [];
    for (const child of this.children) {{
      if (child.matches(selector)) {{
        matches.push(child);
      }}
      matches.push(...child.querySelectorAll(selector));
    }}
    return matches;
  }}

  closest(selector) {{
    let node = this;
    while (node instanceof FakeElement) {{
      if (node.matches(selector)) {{
        return node;
      }}
      node = node.parent;
    }}
    return null;
  }}

  matches(selector) {{
    if (selector.startsWith(".")) {{
      const className = selector.slice(1);
      return this._classNames.includes(className);
    }}
    if (selector === "[data-lazy-id]") {{
      return Object.prototype.hasOwnProperty.call(this.dataset, "lazyId");
    }}
    return false;
  }}
}}

class FakeHTMLElement extends FakeElement {{}}
class FakeHTMLDetailsElement extends FakeHTMLElement {{}}

class FakeTemplateElement extends FakeHTMLElement {{
  constructor() {{
    super("template");
    this.content = new FakeFragment();
  }}

  set innerHTML(value) {{
    this.content = buildFragment(value);
  }}
}}

class FakeHostElement extends FakeHTMLElement {{
  constructor() {{
    super("div");
    this._listeners = new Map();
  }}

  addEventListener(type, listener) {{
    const listeners = this._listeners.get(type) ?? [];
    listeners.push(listener);
    this._listeners.set(type, listeners);
  }}

  removeEventListener(type, listener) {{
    const listeners = this._listeners.get(type) ?? [];
    this._listeners.set(
      type,
      listeners.filter((candidate) => candidate !== listener),
    );
  }}

  dispatchEvent(event) {{
    const listeners = this._listeners.get(event.type) ?? [];
    for (const listener of listeners) {{
      listener(event);
    }}
  }}

  set innerHTML(value) {{
    this.children = [];
    const root = buildRoot(value);
    if (root) {{
      this.append(root);
    }}
  }}
}}

function extractLazyId(htmlText) {{
  const match = htmlText.match(/data-lazy-id='([^']+)'/);
  return match ? match[1] : null;
}}

function buildRoot(htmlText) {{
  assert(htmlText.includes("mammos-entity-collection"), "unexpected root html");
  const root = new FakeHTMLDetailsElement("details", ["mammos-entity-collection", "root-node"]);
  root.dataset.lazyId = extractLazyId(htmlText);
  root.dataset.lazyCursor = "0";
  root.dataset.lazyLoading = "false";
  root.dataset.lazyDone = "false";
  root.open = true;

  const summary = new FakeHTMLElement("summary");
  const children = new FakeHTMLElement("div", ["collection-children"]);
  root.append(summary);
  root.append(children);
  return root;
}}

function buildLazyEntityRow(htmlText) {{
  assert(htmlText.includes("mammos-entity-inline"), "unexpected page html");
  const row = new FakeHTMLElement("div", ["branch-item", "entity-row"]);
  const key = new FakeHTMLElement("div", ["entity-key"]);
  const value = new FakeHTMLElement("div", ["entity-value"]);
  const wrapper = new FakeHTMLElement("div", ["mammos-entity-inline"]);
  const details = new FakeHTMLDetailsElement("details", ["lazy-leaf-details"]);
  details.dataset.lazyId = extractLazyId(htmlText);
  details.dataset.lazyCursor = "0";
  details.dataset.lazyLoading = "false";
  details.dataset.lazyDone = "false";
  details.open = false;
  const summary = new FakeHTMLElement("summary", ["lazy-leaf-summary"]);
  details.append(summary);
  wrapper.append(details);
  value.append(wrapper);
  row.append(key);
  row.append(value);
  return new FakeFragment([row]);
}}

function buildExpandedLazyLeaf(htmlText) {{
  assert(htmlText.includes("entity-expanded-details"), "unexpected detail html");
  const details = new FakeHTMLDetailsElement("details", ["lazy-leaf-details"]);
  details.open = true;
  const summary = new FakeHTMLElement("summary", ["lazy-leaf-summary"]);
  const body = new FakeHTMLElement("div", ["entity-expanded-details"]);
  details.append(summary);
  details.append(body);
  return new FakeFragment([details]);
}}

function buildFragment(htmlText) {{
  if (htmlText.includes("branch-item entity-row")) {{
    return buildLazyEntityRow(htmlText);
  }}
  if (htmlText.includes("lazy-leaf-details")) {{
    return buildExpandedLazyLeaf(htmlText);
  }}
  return new FakeFragment();
}}

globalThis.HTMLElement = FakeHTMLElement;
globalThis.HTMLDetailsElement = FakeHTMLDetailsElement;
globalThis.document = {{
  createElement(tagName) {{
    if (tagName === "template") {{
      return new FakeTemplateElement();
    }}
    return new FakeHTMLElement(tagName);
  }},
}};

const source = fs
  .readFileSync(JS_SOURCE_PATH, "utf8")
  .replace("export function render", "function render");
vm.runInThisContext(source + "\\nglobalThis.__treeRender = render;");

class FakeModel {{
  constructor() {{
    this.sent = [];
    this.listeners = new Map();
  }}

  get(name) {{
    if (name === "root_html") {{
      return ROOT_HTML;
    }}
    return null;
  }}

  send(message) {{
    this.sent.push(message);
  }}

  on(name, listener) {{
    this.listeners.set(name, listener);
  }}

  off(name) {{
    this.listeners.delete(name);
  }}

  emit(name, payload) {{
    const listener = this.listeners.get(name);
    if (listener) {{
      listener(payload);
    }}
  }}
}}

const model = new FakeModel();
const host = new FakeHostElement();
globalThis.__treeRender({{ model, el: host }});

assert(model.sent.length === 1, "root render should request first page");
assert(model.sent[0].lazy_id === ROOT_LAZY_ID, "unexpected root lazy id");

model.emit("msg:custom", {{
  kind: "lazy-rendered",
  lazy_id: ROOT_LAZY_ID,
  patch: "append-children",
  html: PAGE_HTML,
  controls_html: "",
  next_cursor: 1,
  done: true,
}});

const root = host.querySelector(".mammos-entity-collection");
const leaf = root.querySelectorAll("[data-lazy-id]").find((node) => node.dataset.lazyId === LEAF_LAZY_ID);
assert(leaf, "lazy entity leaf should exist after first page render");
leaf.open = true;
host.dispatchEvent({{ type: "toggle", target: leaf }});

assert(model.sent.length === 2, "leaf toggle should request one lazy render");
assert(model.sent[1].lazy_id === LEAF_LAZY_ID, "unexpected lazy entity leaf id");

model.emit("msg:custom", {{
  kind: "lazy-rendered",
  lazy_id: LEAF_LAZY_ID,
  patch: "replace-self",
  html: DETAIL_HTML,
  controls_html: "",
  next_cursor: 0,
  done: true,
}});

const expandedBody = root.querySelector(".entity-expanded-details");
assert(expandedBody, "expanded lazy entity body should be present after replacement");
""",
        encoding="utf-8",
    )

    subprocess.run(["node", str(script_path)], check=True, cwd=Path.cwd())


def test_widget_javascript_collapsing_collection_resets_loaded_children(tmp_path):
    session = EntityCollectionTreeSession(
        me.EntityCollection(**{f"k{i}": i for i in range(120)}),
        page_size=50,
    )
    root_html = session.render_root_html()
    first_page = session.render_lazy_node(session.root_node_id)
    js_source_path = Path(me.__file__).resolve().parent / "_entity_collection_tree.js"
    script_path = tmp_path / "collection_collapse_reset_test.cjs"
    script_path.write_text(
        f"""
const fs = require("fs");
const vm = require("vm");

const ROOT_HTML = {json.dumps(root_html)};
const PAGE_HTML = {json.dumps(first_page["html"])};
const CONTROLS_HTML = {json.dumps(first_page["controls_html"])};
const JS_SOURCE_PATH = {json.dumps(str(js_source_path))};

function fail(message) {{
  throw new Error(message);
}}

function assert(condition, message) {{
  if (!condition) {{
    fail(message);
  }}
}}

class FakeFragment {{
  constructor(children = []) {{
    this.children = children;
    for (const child of this.children) {{
      child.parent = this;
    }}
  }}

  get firstElementChild() {{
    return this.children[0] ?? null;
  }}
}}

class FakeElement {{
  constructor(tagName, classNames = []) {{
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.parent = null;
    this.dataset = {{}};
    this._classNames = [...classNames];
    this.className = this._classNames.join(" ");
    this.open = false;
  }}

  append(child) {{
    if (child instanceof FakeFragment) {{
      for (const fragmentChild of child.children) {{
        this.append(fragmentChild);
      }}
      return;
    }}
    child.parent = this;
    this.children.push(child);
  }}

  querySelector(selector) {{
    return this.querySelectorAll(selector)[0] ?? null;
  }}

  querySelectorAll(selector) {{
    const matches = [];
    for (const child of this.children) {{
      if (child.matches(selector)) {{
        matches.push(child);
      }}
      matches.push(...child.querySelectorAll(selector));
    }}
    return matches;
  }}

  matches(selector) {{
    if (selector.startsWith(".")) {{
      return this._classNames.includes(selector.slice(1));
    }}
    if (selector === "[data-lazy-id]") {{
      return Object.prototype.hasOwnProperty.call(this.dataset, "lazyId");
    }}
    return false;
  }}

  set innerHTML(value) {{
    this.children = [];
    const fragment = buildFragment(value);
    for (const child of fragment.children) {{
      this.append(child);
    }}
  }}
}}

class FakeHTMLElement extends FakeElement {{}}
class FakeHTMLDetailsElement extends FakeHTMLElement {{}}

class FakeTemplateElement extends FakeHTMLElement {{
  constructor() {{
    super("template");
    this.content = new FakeFragment();
  }}

  set innerHTML(value) {{
    this.content = buildFragment(value);
  }}
}}

class FakeHostElement extends FakeHTMLElement {{
  constructor() {{
    super("div");
    this._listeners = new Map();
  }}

  addEventListener(type, listener) {{
    const listeners = this._listeners.get(type) ?? [];
    listeners.push(listener);
    this._listeners.set(type, listeners);
  }}

  removeEventListener(type, listener) {{
    const listeners = this._listeners.get(type) ?? [];
    this._listeners.set(type, listeners.filter((candidate) => candidate !== listener));
  }}

  dispatchEvent(event) {{
    const listeners = this._listeners.get(event.type) ?? [];
    for (const listener of listeners) {{
      listener(event);
    }}
  }}

  set innerHTML(value) {{
    this.children = [];
    const root = buildRoot(value);
    if (root) {{
      this.append(root);
    }}
  }}
}}

function extractLazyId(htmlText) {{
  const match = htmlText.match(/data-lazy-id='([^']+)'/);
  return match ? match[1] : null;
}}

function buildRoot(htmlText) {{
  const root = new FakeHTMLDetailsElement("details", ["mammos-entity-collection", "root-node"]);
  root.dataset.lazyId = extractLazyId(htmlText);
  root.dataset.lazyPatch = "append-children";
  root.dataset.lazyCursor = "0";
  root.dataset.lazyLoading = "false";
  root.dataset.lazyLoaded = "false";
  root.dataset.lazyDone = "false";
  root.dataset.initialChildrenHtml = "";
  root.open = true;

  const summary = new FakeHTMLElement("summary");
  const children = new FakeHTMLElement("div", ["collection-children"]);
  const controls = new FakeHTMLElement("div", ["collection-footer"]);
  root.append(summary);
  root.append(children);
  root.append(controls);
  return root;
}}

function buildRows(htmlText) {{
  const count = (htmlText.match(/branch-item entity-row/g) ?? []).length;
  const rows = [];
  for (let index = 0; index < count; index += 1) {{
    rows.push(new FakeHTMLElement("div", ["branch-item", "entity-row"]));
  }}
  return rows;
}}

function buildControls(htmlText) {{
  if (!htmlText.includes("collection-controls")) {{
    return [];
  }}
  const controls = new FakeHTMLElement("div", ["collection-controls"]);
  const matches = htmlText.matchAll(/data-lazy-action='([^']+)' data-lazy-target-id='([^']+)'>([^<]+)/g);
  for (const match of matches) {{
    const button = new FakeHTMLElement("button", ["collection-control"]);
    button.dataset.lazyAction = match[1];
    button.dataset.lazyTargetId = match[2];
    controls.append(button);
  }}
  return [controls];
}}

function buildFragment(htmlText) {{
  return new FakeFragment([
    ...buildRows(htmlText),
    ...buildControls(htmlText),
  ]);
}}

globalThis.HTMLElement = FakeHTMLElement;
globalThis.HTMLDetailsElement = FakeHTMLDetailsElement;
globalThis.document = {{
  createElement(tagName) {{
    if (tagName === "template") {{
      return new FakeTemplateElement();
    }}
    return new FakeHTMLElement(tagName);
  }},
}};

const source = fs
  .readFileSync(JS_SOURCE_PATH, "utf8")
  .replace("export function render", "function render");
vm.runInThisContext(source + "\\nglobalThis.__treeRender = render;");

class FakeModel {{
  constructor() {{
    this.sent = [];
    this.listeners = new Map();
  }}

  get(name) {{
    if (name === "root_html") {{
      return ROOT_HTML;
    }}
    return null;
  }}

  send(message) {{
    this.sent.push(message);
  }}

  on(name, listener) {{
    this.listeners.set(name, listener);
  }}

  off(name) {{
    this.listeners.delete(name);
  }}

  emit(name, payload) {{
    const listener = this.listeners.get(name);
    if (listener) {{
      listener(payload);
    }}
  }}
}}

const model = new FakeModel();
const host = new FakeHostElement();
globalThis.__treeRender({{ model, el: host }});

assert(model.sent.length === 1, "root should request first page once");
assert(model.sent[0].cursor === 0, "first request should start at cursor 0");

model.emit("msg:custom", {{
  kind: "lazy-rendered",
  lazy_id: "lazy-node-0",
  patch: "append-children",
  html: PAGE_HTML,
  controls_html: CONTROLS_HTML,
  next_cursor: 50,
  done: false,
}});

assert(model.sent.length === 1, "first page render should not auto-fetch another page");
const root = host.querySelector(".mammos-entity-collection");
const children = root.querySelector(".collection-children");
const controls = root.querySelector(".collection-footer");
assert(root.dataset.lazyLoaded === "true", "root should be marked loaded after first page");
assert(children.children.length === 50, "first page should append 50 rows");
assert(controls.children.length === 1, "controls should be rendered after first page");
assert(root.dataset.hasControls === "true", "root should track that controls are present");

root.open = false;
host.dispatchEvent({{ type: "toggle", target: root }});

assert(root.dataset.lazyLoaded === "false", "collapse should clear loaded flag");
assert(root.dataset.lazyCursor === "0", "collapse should reset cursor to 0");
assert(root.dataset.lazyDone === "false", "collapse should reset done flag");
assert(children.children.length === 0, "collapse should clear rendered children");
assert(controls.children.length === 0, "collapse should clear controls");
assert(root.dataset.hasControls === "false", "collapse should clear controls state");

root.open = true;
host.dispatchEvent({{ type: "toggle", target: root }});

assert(model.sent.length === 2, "reopening should request the first page once");
assert(model.sent[1].cursor === 0, "reopen should restart at cursor 0");
assert(model.sent[1].load_all === false, "reopen should not request load_all");
""",
        encoding="utf-8",
    )

    subprocess.run(["node", str(script_path)], check=True, cwd=Path.cwd())


def test_widget_javascript_clicking_nested_collection_control_appends_children(tmp_path):
    nested = me.EntityCollection(**{f"k{i}": i for i in range(120)})
    session = EntityCollectionTreeSession(me.EntityCollection(group=nested), page_size=50)
    nested_id = _collection_child_id(session.root_node_id, 0)
    root_html = session.render_root_html()
    root_page = session.render_lazy_node(session.root_node_id, cursor=0)["html"]
    nested_first_page = session.render_lazy_node(nested_id)
    nested_second_page = session.render_lazy_node(nested_id, cursor=50)
    js_source_path = Path(me.__file__).resolve().parent / "_entity_collection_tree.js"
    script_path = tmp_path / "nested_collection_control_test.cjs"
    script_path.write_text(
        f"""
const fs = require("fs");
const vm = require("vm");

const ROOT_HTML = {json.dumps(root_html)};
const ROOT_PAGE_HTML = {json.dumps(root_page)};
const NESTED_PAGE_HTML = {json.dumps(nested_first_page["html"])};
const NESTED_CONTROLS_HTML = {json.dumps(nested_first_page["controls_html"])};
const NESTED_SECOND_HTML = {json.dumps(nested_second_page["html"])};
const NESTED_SECOND_CONTROLS = {json.dumps(nested_second_page["controls_html"])};
const ROOT_LAZY_ID = {json.dumps(session.root_node_id)};
const NESTED_LAZY_ID = {json.dumps(nested_id)};
const JS_SOURCE_PATH = {json.dumps(str(js_source_path))};

function fail(message) {{
  throw new Error(message);
}}

function assert(condition, message) {{
  if (!condition) {{
    fail(message);
  }}
}}

class FakeFragment {{
  constructor(children = []) {{
    this.children = children;
    for (const child of this.children) {{
      child.parent = this;
    }}
  }}

  get firstElementChild() {{
    return this.children[0] ?? null;
  }}
}}

class FakeTextNode {{
  constructor(parentElement) {{
    this.parentElement = parentElement;
  }}
}}

class FakeElement {{
  constructor(tagName, classNames = []) {{
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.parent = null;
    this.dataset = {{}};
    this._classNames = [...classNames];
    this.className = this._classNames.join(" ");
    this.open = false;
  }}

  get parentElement() {{
    return this.parent instanceof FakeElement ? this.parent : null;
  }}

  append(child) {{
    if (child instanceof FakeFragment) {{
      for (const fragmentChild of child.children) {{
        this.append(fragmentChild);
      }}
      return;
    }}
    child.parent = this;
    this.children.push(child);
  }}

  querySelector(selector) {{
    return this.querySelectorAll(selector)[0] ?? null;
  }}

  querySelectorAll(selector) {{
    const matches = [];
    for (const child of this.children) {{
      if (child.matches(selector)) {{
        matches.push(child);
      }}
      matches.push(...child.querySelectorAll(selector));
    }}
    return matches;
  }}

  closest(selector) {{
    let node = this;
    while (node instanceof FakeElement) {{
      if (node.matches(selector)) {{
        return node;
      }}
      node = node.parentElement;
    }}
    return null;
  }}

  matches(selector) {{
    if (selector.startsWith(".")) {{
      return this._classNames.includes(selector.slice(1));
    }}
    if (selector === "[data-lazy-id]") {{
      return Object.prototype.hasOwnProperty.call(this.dataset, "lazyId");
    }}
    return false;
  }}

  set innerHTML(value) {{
    this.children = [];
    const fragment = buildFragment(value);
    for (const child of fragment.children) {{
      this.append(child);
    }}
  }}
}}

class FakeHTMLElement extends FakeElement {{}}
class FakeHTMLDetailsElement extends FakeHTMLElement {{}}

class FakeTemplateElement extends FakeHTMLElement {{
  constructor() {{
    super("template");
    this.content = new FakeFragment();
  }}

  set innerHTML(value) {{
    this.content = buildFragment(value);
  }}
}}

class FakeHostElement extends FakeHTMLElement {{
  constructor() {{
    super("div");
    this._listeners = new Map();
  }}

  addEventListener(type, listener) {{
    const listeners = this._listeners.get(type) ?? [];
    listeners.push(listener);
    this._listeners.set(type, listeners);
  }}

  removeEventListener(type, listener) {{
    const listeners = this._listeners.get(type) ?? [];
    this._listeners.set(type, listeners.filter((candidate) => candidate !== listener));
  }}

  dispatchEvent(event) {{
    const listeners = this._listeners.get(event.type) ?? [];
    for (const listener of listeners) {{
      listener(event);
    }}
  }}

  set innerHTML(value) {{
    this.children = [];
    const root = buildRoot(value);
    if (root) {{
      this.append(root);
    }}
  }}
}}

function extractLazyId(htmlText) {{
  const match = htmlText.match(/data-lazy-id='([^']+)'/);
  return match ? match[1] : null;
}}

function buildRoot(htmlText) {{
  const root = new FakeHTMLDetailsElement("details", ["mammos-entity-collection", "root-node"]);
  root.dataset.lazyId = extractLazyId(htmlText);
  root.dataset.lazyPatch = "append-children";
  root.dataset.lazyCursor = "0";
  root.dataset.lazyLoading = "false";
  root.dataset.lazyLoaded = "false";
  root.dataset.lazyDone = "false";
  root.dataset.initialChildrenHtml = "";
  root.open = true;

  const summary = new FakeHTMLElement("summary");
  const children = new FakeHTMLElement("div", ["collection-children"]);
  const controls = new FakeHTMLElement("div", ["collection-footer"]);
  root.append(summary);
  root.append(children);
  root.append(controls);
  return root;
}}

function buildBranchNode(htmlText) {{
  const branch = new FakeHTMLDetailsElement("details", ["branch-item", "branch-node"]);
  branch.dataset.lazyId = extractLazyId(htmlText);
  branch.dataset.lazyPatch = "append-children";
  branch.dataset.lazyCursor = "0";
  branch.dataset.lazyLoading = "false";
  branch.dataset.lazyLoaded = "false";
  branch.dataset.lazyDone = "false";
  branch.dataset.initialChildrenHtml = "";
  branch.open = false;

  const summary = new FakeHTMLElement("summary");
  const children = new FakeHTMLElement("div", ["collection-children"]);
  const controls = new FakeHTMLElement("div", ["collection-footer"]);
  branch.append(summary);
  branch.append(children);
  branch.append(controls);
  return branch;
}}

function buildRows(htmlText) {{
  const count = (htmlText.match(/branch-item entity-row/g) ?? []).length;
  const rows = [];
  for (let index = 0; index < count; index += 1) {{
    rows.push(new FakeHTMLElement("div", ["branch-item", "entity-row"]));
  }}
  return rows;
}}

function buildControls(htmlText) {{
  if (!htmlText.includes("collection-controls")) {{
    return [];
  }}
  const controls = new FakeHTMLElement("div", ["collection-controls"]);
  const matches = htmlText.matchAll(/data-lazy-action='([^']+)' data-lazy-target-id='([^']+)'>([^<]+)/g);
  for (const match of matches) {{
    const button = new FakeHTMLElement("button", ["collection-control"]);
    button.dataset.lazyAction = match[1];
    button.dataset.lazyTargetId = match[2];
    controls.append(button);
  }}
  return [controls];
}}

function buildFragment(htmlText) {{
  if (htmlText.includes("branch-item branch-node")) {{
    return new FakeFragment([buildBranchNode(htmlText)]);
  }}
  return new FakeFragment([
    ...buildRows(htmlText),
    ...buildControls(htmlText),
  ]);
}}

globalThis.HTMLElement = FakeHTMLElement;
globalThis.HTMLDetailsElement = FakeHTMLDetailsElement;
globalThis.document = {{
  createElement(tagName) {{
    if (tagName === "template") {{
      return new FakeTemplateElement();
    }}
    return new FakeHTMLElement(tagName);
  }},
}};

const source = fs
  .readFileSync(JS_SOURCE_PATH, "utf8")
  .replace("export function render", "function render");
vm.runInThisContext(source + "\\nglobalThis.__treeRender = render;");

class FakeModel {{
  constructor() {{
    this.sent = [];
    this.listeners = new Map();
  }}

  get(name) {{
    if (name === "root_html") {{
      return ROOT_HTML;
    }}
    return null;
  }}

  send(message) {{
    this.sent.push(message);
  }}

  on(name, listener) {{
    this.listeners.set(name, listener);
  }}

  off(name) {{
    this.listeners.delete(name);
  }}

  emit(name, payload) {{
    const listener = this.listeners.get(name);
    if (listener) {{
      listener(payload);
    }}
  }}
}}

const model = new FakeModel();
const host = new FakeHostElement();
globalThis.__treeRender({{ model, el: host }});

assert(model.sent.length === 1, "root should request its first page");
model.emit("msg:custom", {{
  kind: "lazy-rendered",
  lazy_id: ROOT_LAZY_ID,
  patch: "append-children",
  html: ROOT_PAGE_HTML,
  controls_html: "",
  next_cursor: 1,
  done: true,
}});

const root = host.querySelector(".mammos-entity-collection");
const nestedNode = root.querySelector(".branch-node");
assert(nestedNode, "nested collection node should be rendered");

nestedNode.open = true;
host.dispatchEvent({{ type: "toggle", target: nestedNode }});

assert(model.sent.length === 2, "opening nested collection should request its first page");
assert(model.sent[1].lazy_id === NESTED_LAZY_ID, "nested request should target the collection node");
assert(model.sent[1].cursor === 0, "nested request should start at cursor 0");

model.emit("msg:custom", {{
  kind: "lazy-rendered",
  lazy_id: NESTED_LAZY_ID,
  patch: "append-children",
  html: NESTED_PAGE_HTML,
  controls_html: NESTED_CONTROLS_HTML,
  next_cursor: 50,
  done: false,
}});

const nestedChildren = nestedNode.querySelector(".collection-children");
const nestedControls = nestedNode.querySelector(".collection-footer");
assert(nestedChildren.children.length === 50, "nested first page should append 50 rows");
assert(nestedNode.dataset.hasControls === "true", "nested node should track controls");

const nextButton = nestedNode.querySelector(".collection-control");
assert(nextButton, "nested controls should render a next button");
host.dispatchEvent({{
  type: "click",
  target: new FakeTextNode(nextButton),
  preventDefault() {{}},
}});

assert(model.sent.length === 3, "clicking nested next should request another page");
assert(model.sent[2].lazy_id === NESTED_LAZY_ID, "nested next should keep targeting the nested collection");
assert(model.sent[2].cursor === 50, "nested next should continue from the current cursor");
assert(model.sent[2].load_all === false, "nested next should not request load_all");

model.emit("msg:custom", {{
  kind: "lazy-rendered",
  lazy_id: NESTED_LAZY_ID,
  patch: "append-children",
  html: NESTED_SECOND_HTML,
  controls_html: NESTED_SECOND_CONTROLS,
  next_cursor: 100,
  done: false,
}});

assert(nestedChildren.children.length === 100, "nested next page should append into the nested child container");
assert(nestedNode.dataset.hasControls === "true", "nested node should remain marked while more pages exist");
""",
        encoding="utf-8",
    )

    subprocess.run(["node", str(script_path)], check=True, cwd=Path.cwd())


def test_wide_collection_paging_shows_next_and_all_controls():
    collection = me.EntityCollection(**{f"k{i}": i for i in range(120)})
    session = EntityCollectionTreeSession(collection, page_size=50)

    first_page = session.render_lazy_node(session.root_node_id)
    second_page = session.render_lazy_node(session.root_node_id, cursor=50)
    remaining_page = session.render_lazy_node(session.root_node_id, cursor=50, load_all=True)

    assert "Load next 50" in first_page["controls_html"]
    assert "Load remaining 70" in first_page["controls_html"]
    assert first_page["done"] is False
    assert first_page["next_cursor"] == 50
    assert "Load next 20" in second_page["controls_html"]
    assert "Load remaining 20" in second_page["controls_html"]
    assert remaining_page["done"] is True
    assert remaining_page["controls_html"] == ""
    assert remaining_page["next_cursor"] == 120


def test_nested_collection_paging_shows_next_and_all_controls():
    nested = me.EntityCollection(**{f"k{i}": i for i in range(120)})
    session = EntityCollectionTreeSession(me.EntityCollection(group=nested), page_size=50)
    nested_id = _collection_child_id(session.root_node_id, 0)

    root_page = session.render_lazy_node(session.root_node_id, cursor=0)
    nested_page = session.render_lazy_node(nested_id)
    nested_remaining_page = session.render_lazy_node(nested_id, cursor=50, load_all=True)

    assert f"data-lazy-id='{nested_id}'" in root_page["html"]
    assert "Load next 50" in nested_page["controls_html"]
    assert "Load remaining 70" in nested_page["controls_html"]
    assert nested_page["done"] is False
    assert nested_page["next_cursor"] == 50
    assert nested_remaining_page["done"] is True
    assert nested_remaining_page["controls_html"] == ""
    assert nested_remaining_page["next_cursor"] == 120


def test_widget_handles_load_all_request(monkeypatch):
    widget = EntityCollectionTreeWidget(
        me.EntityCollection(**{f"k{i}": i for i in range(120)}),
        page_size=50,
    )
    sent_messages = []
    monkeypatch.setattr(widget, "send", lambda content, buffers=None: sent_messages.append(content))

    widget._handle_message(
        widget,
        {
            "kind": "render-lazy",
            "lazy_id": widget.root_node_id,
            "cursor": 50,
            "load_all": True,
        },
        [],
    )

    assert sent_messages[0]["kind"] == "lazy-rendered"
    assert sent_messages[0]["lazy_id"] == widget.root_node_id
    assert sent_messages[0]["done"] is True
    assert sent_messages[0]["next_cursor"] == 120
    assert sent_messages[0]["controls_html"] == ""


@pytest.mark.parametrize(("key", "value", "meta_fragment"), _structured_leaf_cases())
def test_static_tree_view_special_leaf_rendering_is_compact(key, value, meta_fragment):
    html = me.EntityCollection(**{key: value})._repr_html_()

    assert "mammos-compact-value" in html
    assert "branch-item entity-row leaf-row" in html
    assert meta_fragment in _normalized_html_text(html)


@pytest.mark.parametrize(("key", "value", "meta_fragment"), _structured_leaf_cases())
def test_widget_tree_view_special_leaf_loading_is_lazy(key, value, meta_fragment):
    session = EntityCollectionTreeSession(me.EntityCollection(**{key: value}), page_size=10)
    leaf_id = _leaf_child_id(session.root_node_id, 0)

    page = session.render_lazy_node(session.root_node_id, cursor=0)
    detail = session.render_lazy_node(leaf_id)

    assert f"data-lazy-id='{leaf_id}'" in page["html"]
    assert "branch-item entity-row leaf-row" in page["html"]
    assert "<summary class='lazy-leaf-summary'>" in page["html"]
    assert "entity-full-value" not in page["html"]
    assert detail["patch"] == "replace-self"
    assert "mammos-compact-value" in detail["html"]
    assert " open>" in detail["html"]
    assert "entity-full-value" in detail["html"]
    assert meta_fragment in _normalized_html_text(detail["html"])
