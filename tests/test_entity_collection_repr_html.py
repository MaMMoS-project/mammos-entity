import html
import importlib.resources
import re
import reprlib

import mammos_units as u
import numpy as np
import pytest

import mammos_entity as me
import mammos_entity._repr as repr_module
from mammos_entity._repr import _repr_css


def _strip_html_event_handlers(fragment: str) -> str:
    """Normalize inline event handlers in HTML repr snapshots."""
    return re.sub(r'(onclick|onkeydown)="[^"]*"', r'\1="..."', fragment)


def _assert_row_wrapper(row_html: str, *, key: str) -> None:
    """Check the shared collection row wrapper around a rendered value."""
    assert row_html.startswith("<div class='branch-item entity-row'>")
    assert f"<div class='entity-key'>{key}</div>" in row_html
    assert "<div class='entity-value'>" in row_html
    assert row_html.endswith("</div></div>")


def _assert_compact_row_behavior(
    row_html: str,
    *,
    key: str,
    preview_html: str,
    meta_text_html: str,
    expanded_html: str,
) -> None:
    """Check the shared compact-preview behavior without freezing full markup."""
    _assert_row_wrapper(row_html, key=key)
    assert "class='mammos-entity-inline mammos-compact-value' data-expanded='false'" in row_html
    assert "aria-label='Expand value'" in row_html
    assert "aria-label='Collapse value'" in row_html
    assert preview_html in row_html
    assert meta_text_html in row_html
    assert f"<span class='entity-full-value'>{expanded_html}</span>" in row_html


class HtmlValue:
    """Test helper exposing a custom HTML repr."""

    def _repr_html_(self):
        return "<span>custom html</span>"


class BrokenHtmlValue:
    """Test helper whose HTML repr fails."""

    def _repr_html_(self):
        raise RuntimeError("broken html repr")

    def __repr__(self):
        """Return a stable repr for fallback assertions."""
        return "BrokenHtmlValue()"


class NoneHtmlValue:
    """Test helper whose HTML repr declines to render."""

    def _repr_html_(self):
        return None

    def __repr__(self):
        """Return a stable repr for fallback assertions."""
        return "NoneHtmlValue()"


class HtmlButBrokenRepr:
    """Test helper whose HTML repr works even though ``__repr__`` fails."""

    def _repr_html_(self):
        return "<span>working html</span>"

    def __repr__(self):
        """Broken repr."""
        raise RuntimeError("broken repr")


class DualHtmlValue:
    """Test helper exposing both full and fragment HTML repr methods."""

    def _repr_html_(self):
        return "<div>full html</div>"

    def _repr_html_fragment_(self):
        return "<span>fragment html</span>"


class NoneHtmlList(list):
    """Test helper list subclass whose HTML repr declines to render."""

    def _repr_html_(self):
        return None


class BrokenReprList(list):
    """Test helper list subclass whose ``__repr__`` fails."""

    def __repr__(self):
        """Broken repr."""
        raise RuntimeError("broken repr")


class BrokenReprTuple(tuple):
    """Test helper tuple subclass whose ``__repr__`` fails."""

    def __repr__(self):
        """Broken repr."""
        raise RuntimeError("broken repr")


class DerivedEntityCollection(me.EntityCollection):
    """Test helper subclass for nested collection HTML repr coverage."""


def test_repr_html_plain_collection_exact_snapshot(monkeypatch):
    """Freeze the plain collection HTML structure."""
    ec = me.EntityCollection("descr", M=me.M(1, "A/m"), a=[1, 2])

    expected_block = (
        "<div id='root' class='mammos-entity-collection' "
        "data-busy='false' aria-busy='false'>"
        "<div class='collection-header'>"
        "<div class='collection-title'><span>EntityCollection</span></div>"
        "</div>"
        "<div class='collection-body'>"
        "<div class='collection-children'>"
        "<div class='branch-item collection-description'>descr</div>"
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>M</div>"
        "<div class='entity-value'>"
        "<samp class='mammos-entity-inline'>"
        "<span class='entity-label'>Magnetization</span>"
        "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span>1.0&nbsp;A&nbsp;/&nbsp;m</span>"
        "</samp>"
        "</div>"
        "</div>"
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>a</div>"
        "<div class='entity-value'>[1,&nbsp;2]</div>"
        "</div>"
        "</div>"
        "</div>"
        "</div>"
    )

    assert ec._repr_html_block(root_id="root") == expected_block

    monkeypatch.setattr(
        repr_module.uuid,
        "uuid4",
        lambda: type("DummyUuid", (), {"hex": "root"})(),
    )
    assert ec._repr_html_() == (f"{_repr_css()}{ec._repr_html_block(root_id='mammos-entity-collection-root')}")


def test_repr_html_details_script():
    """Expand/collapse-all scripts set busy state and the requested open state."""
    expanding = me.EntityCollection._repr_html_details_script("root", open_state=True)
    collapsing = me.EntityCollection._repr_html_details_script("root", open_state=False)

    for script, label, state in [
        (expanding, "Expanding...", "true"),
        (collapsing, "Collapsing...", "false"),
    ]:
        assert "document.getElementById('root')" in script
        assert "root.dataset.busy = 'true'" in script
        assert "root.dataset.busy = 'false'" in script
        assert "root.setAttribute('aria-busy', 'true')" in script
        assert "root.setAttribute('aria-busy', 'false')" in script
        assert f"status.textContent = '{label}'" in script
        assert f"element.open = {state}" in script
        assert "buttons.forEach((button) => { button.disabled = true; });" in script
        assert "buttons.forEach((button) => { button.disabled = false; });" in script
        assert "requestAnimationFrame(() => { requestAnimationFrame(step); });" in script


def test_repr_css_wraps_shared_stylesheet():
    css_file = importlib.resources.files("mammos_entity").joinpath("_entity_collection_repr.css")
    assert _repr_css() == f"<style>{css_file.read_text(encoding='utf-8')}</style>"


def test_repr_html_uses_value_repr_html_when_available():
    row_html = me.EntityCollection._repr_html_value("custom", HtmlValue())

    _assert_row_wrapper(row_html, key="custom")
    assert "<span>custom html</span>" in row_html


@pytest.mark.parametrize(
    ("key", "value", "fallback_text"),
    [
        ("broken", BrokenHtmlValue(), "BrokenHtmlValue()"),
        ("missing", NoneHtmlValue(), "NoneHtmlValue()"),
    ],
)
def test_repr_html_falls_back_when_custom_html_is_unavailable(key, value, fallback_text):
    row_html = me.EntityCollection._repr_html_value(key, value)

    _assert_row_wrapper(row_html, key=key)
    assert fallback_text in row_html


def test_repr_html_uses_working_html_even_if_repr_is_broken():
    row_html = me.EntityCollection._repr_html_value("working", HtmlButBrokenRepr())

    _assert_row_wrapper(row_html, key="working")
    assert "<span>working html</span>" in row_html


def test_repr_html_prefers_full_html_for_generic_values():
    row_html = me.EntityCollection._repr_html_value("dual", DualHtmlValue())

    _assert_row_wrapper(row_html, key="dual")
    assert "<div>full html</div>" in row_html
    assert "<span>fragment html</span>" not in row_html


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("missing", NoneHtmlList(range(120))),
        ("broken", BrokenReprList(range(120))),
    ],
)
def test_repr_html_supported_long_container_subclasses_keep_compact_preview(key, value):
    row_html = _strip_html_event_handlers(me.EntityCollection._repr_html_value(key, value))
    expanded_html = html.escape(repr_module._format_sequence_repr_expanded(value))

    _assert_compact_row_behavior(
        row_html,
        key=key,
        preview_html="[0,&nbsp;1,&nbsp;2,&nbsp;...,&nbsp;117,&nbsp;118,&nbsp;119]",
        meta_text_html="len=120",
        expanded_html=expanded_html,
    )


@pytest.mark.parametrize(
    ("key", "value", "value_html"),
    [
        ("list", BrokenReprList([1, 2, 3]), "[1,&nbsp;2,&nbsp;3]"),
        ("tuple", BrokenReprTuple((1, 2, 3)), "(1,&nbsp;2,&nbsp;3)"),
    ],
)
def test_repr_html_short_supported_sequence_subclasses_with_broken_repr_stay_inline(key, value, value_html):
    row_html = me.EntityCollection._repr_html_value(key, value)

    _assert_row_wrapper(row_html, key=key)
    assert value_html in row_html
    assert "mammos-compact-value" not in row_html


def test_repr_html_value_toggle_script():
    """Compact row toggle scripts target the right root class and state."""
    expanding = repr_module._repr_html_toggle_script("mammos-compact-value", expanded=True)
    collapsing = repr_module._repr_html_toggle_script("mammos-compact-value", expanded=False)

    assert "closest('.mammos-compact-value')" in expanding
    assert "dataset.expanded = 'true'" in expanding
    assert "closest('.mammos-compact-value')" in collapsing
    assert "dataset.expanded = 'false'" in collapsing


def test_repr_html_long_numpy_array_compact_preview_snapshot():
    array = np.arange(24).reshape(4, 6)

    row_html = _strip_html_event_handlers(me.EntityCollection._repr_html_value("M", array))
    expanded_html = html.escape(me._repr._format_array_repr_expanded(array))

    assert row_html == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>M</div>"
        "<div class='entity-value'>"
        "<samp class='mammos-entity-inline mammos-compact-value' data-expanded='false'>"
        "<span class='entity-collapsed entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Expand value' "
        'onclick="..." onkeydown="...">[+]</span>'
        "<span class='entity-summary-content'>"
        "<span>0&nbsp;1&nbsp;2&nbsp;...&nbsp;21&nbsp;22&nbsp;23</span>"
        "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>shape=(4,&nbsp;6)</span>"
        "</span>"
        "</span>"
        "<span class='entity-expanded entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Collapse value' "
        'onclick="..." onkeydown="...">[−]</span>'
        "<span class='entity-summary-content'>"
        "<span>0&nbsp;1&nbsp;2&nbsp;...&nbsp;21&nbsp;22&nbsp;23</span>"
        "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>shape=(4,&nbsp;6)</span>"
        "</span>"
        "</span>"
        "<span class='entity-expanded-details'>"
        f"<span class='entity-full-value'>{expanded_html}</span>"
        "</span>"
        "</samp>"
        "</div>"
        "</div>"
    )


def test_repr_html_long_string_object_array_preserves_internal_spaces_in_preview():
    value = np.array(["a   b"] * 120, dtype=object)

    row_html = me.EntityCollection._repr_html_value("strings", value)

    _assert_row_wrapper(row_html, key="strings")
    assert "mammos-compact-value" in row_html
    assert "&#x27;a&nbsp;&nbsp;&nbsp;b&#x27;" in row_html
    assert "&#x27;a&nbsp;b&#x27;" not in row_html


@pytest.mark.parametrize(
    ("key", "value", "preview_html", "meta_text_html", "expanded_formatter"),
    [
        (
            "M_q",
            me.M(np.arange(24).reshape(4, 6), "A/m").quantity,
            "0.&nbsp;1.&nbsp;2.&nbsp;...&nbsp;21.&nbsp;22.&nbsp;23.<span>&nbsp;A&nbsp;/&nbsp;m</span>",
            "shape=(4,&nbsp;6)",
            repr_module._format_quantity_repr_expanded,
        ),
        (
            "L",
            list(range(120)),
            "[0,&nbsp;1,&nbsp;2,&nbsp;...,&nbsp;117,&nbsp;118,&nbsp;119]",
            "len=120",
            repr_module._format_sequence_repr_expanded,
        ),
        (
            "T",
            tuple(range(120)),
            "(0,&nbsp;1,&nbsp;2,&nbsp;...,&nbsp;117,&nbsp;118,&nbsp;119)",
            "len=120",
            repr_module._format_sequence_repr_expanded,
        ),
        (
            "D",
            {f"k{i}": i for i in range(120)},
            "{&#x27;k0&#x27;:&nbsp;0,&nbsp;&#x27;k1&#x27;:&nbsp;1,"
            "&nbsp;&#x27;k2&#x27;:&nbsp;2,&nbsp;...,&nbsp;&#x27;k117&#x27;:&nbsp;117,"
            "&nbsp;&#x27;k118&#x27;:&nbsp;118,&nbsp;&#x27;k119&#x27;:&nbsp;119}",
            "len=120",
            repr_module._format_dict_repr_expanded,
        ),
    ],
)
def test_repr_html_long_supported_values_use_compact_preview(
    key,
    value,
    preview_html,
    meta_text_html,
    expanded_formatter,
):
    row_html = _strip_html_event_handlers(me.EntityCollection._repr_html_value(key, value))
    expanded_html = html.escape(expanded_formatter(value))

    _assert_compact_row_behavior(
        row_html,
        key=key,
        preview_html=preview_html,
        meta_text_html=meta_text_html,
        expanded_html=expanded_html,
    )


@pytest.mark.parametrize(
    ("key", "value", "value_html"),
    [
        ("H_q", u.Quantity(3, "A/m"), "&lt;Quantity&nbsp;3.&nbsp;A&nbsp;/&nbsp;m&gt;"),
        ("short", [1, 2, 3], "[1,&nbsp;2,&nbsp;3]"),
        ("short_d", {"a": 1, "b": 2}, "{&#x27;a&#x27;:&nbsp;1,&nbsp;&#x27;b&#x27;:&nbsp;2}"),
    ],
)
def test_repr_html_short_supported_values_stay_inline(key, value, value_html):
    row_html = me.EntityCollection._repr_html_value(key, value)

    _assert_row_wrapper(row_html, key=key)
    assert value_html in row_html
    assert "mammos-compact-value" not in row_html
    assert "entity-collapsed entity-summary" not in row_html


def test_repr_html_long_mixed_list_uses_compact_preview():
    value = [1, "a", {"k": 3}, [4, 5], (6, 7)] * 30

    row_html = _strip_html_event_handlers(me.EntityCollection._repr_html_value("mixed", value))

    _assert_row_wrapper(row_html, key="mixed")
    assert ("class='mammos-entity-inline mammos-compact-value' data-expanded='false'") in row_html
    assert (
        "[1,&nbsp;&#x27;a&#x27;,&nbsp;{&#x27;k&#x27;:&nbsp;3},"
        "&nbsp;...,&nbsp;{&#x27;k&#x27;:&nbsp;3},&nbsp;[4,&nbsp;5],"
        "&nbsp;(6,&nbsp;7)]"
    ) in row_html
    assert ("&nbsp;<span class='entity-meta'>·</span>&nbsp;<span class='entity-meta'>len=150</span>") in row_html
    assert "class='entity-full-value'>" in row_html


def test_format_dict_repr_summary_truncates_long_members():
    long_value = "x" * 200
    value = {
        "k0": 0,
        "k1": 1,
        "k2": long_value,
        "k3": 3,
        "k4": 4,
        "k5": 5,
        "k6": 6,
    }

    summary = repr_module._format_dict_repr_summary(value)

    assert f"'k2': {reprlib.repr(long_value)}" in summary
    assert f"'k2': {long_value!r}" not in summary


def test_format_sequence_repr_expanded_preserves_nested_dict_order():
    value = [{"b": 1, "a": 2}] * 120

    expanded = repr_module._format_sequence_repr_expanded(value)

    assert "{'b': 1, 'a': 2}" in expanded
    assert "{'a': 2, 'b': 1}" not in expanded


def test_repr_html_nested_collection_branch_exact_snapshot():
    """Freeze one nested collection branch as a regression snapshot."""
    inner = me.EntityCollection("inner descr", T=me.T(2))
    expected_nested = (
        "<details class='branch-item'>"
        "<summary>"
        "<span class='summary-key'>inner</span>"
        "<span class='summary-preview'>"
        "EntityCollection&nbsp;·&nbsp;1&nbsp;item&nbsp;·&nbsp;T"
        "</span>"
        "</summary>"
        "<div class='collection-children nested-children'>"
        "<div class='branch-item collection-description'>inner&nbsp;descr</div>"
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>T</div>"
        "<div class='entity-value'>"
        "<samp class='mammos-entity-inline'>"
        "<span class='entity-label'>ThermodynamicTemperature</span>"
        "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span>2.0&nbsp;K</span>"
        "</samp>"
        "</div>"
        "</div>"
        "</div>"
        "</details>"
    )

    assert inner._repr_html_nested("inner") == expected_nested


def test_repr_html_top_level_collection_with_nested_values_adds_controls():
    inner = me.EntityCollection("inner descr", T=me.T(2))
    ec = me.EntityCollection(outer=1, inner=inner)
    block_html = _strip_html_event_handlers(ec._repr_html_block(root_id="root"))

    assert block_html.startswith("<div id='root' class='mammos-entity-collection' ")
    assert "<span>EntityCollection</span>" in block_html
    assert "title='Collapse all'" in block_html
    assert "title='Expand all'" in block_html
    assert "<span class='collection-status' aria-live='polite'></span>" in block_html
    assert "<div class='entity-key'>outer</div>" in block_html
    assert "<div class='entity-value'>1</div>" in block_html
    assert inner._repr_html_nested("inner") in block_html


def test_repr_html_embeds_long_entity_value_preview():
    entity = me.M(np.arange(24).reshape(4, 6), "A/m")
    row_html = me.EntityCollection._repr_html_value("M", entity)

    _assert_row_wrapper(row_html, key="M")
    assert entity._repr_html_fragment_() in row_html


def test_repr_html_subclass_treats_base_collection_values_as_nested():
    inner = me.EntityCollection(T=me.T(2))
    ec = DerivedEntityCollection(inner=inner)
    block_html = ec._repr_html_block(root_id="root")

    assert block_html.startswith("<div id='root' class='mammos-entity-collection' ")
    assert "<span>DerivedEntityCollection</span>" in block_html
    assert DerivedEntityCollection._repr_html_controls("root") in block_html
    assert inner._repr_html_nested("inner") in block_html
