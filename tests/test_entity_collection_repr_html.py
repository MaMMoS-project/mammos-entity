import html
import importlib.resources
import re

import mammos_units as u
import numpy as np

import mammos_entity as me
import mammos_entity._repr as repr_module
from mammos_entity._repr import _repr_css


def _strip_html_event_handlers(fragment: str) -> str:
    """Normalize inline event handlers in HTML repr snapshots."""
    return re.sub(r'(onclick|onkeydown)="[^"]*"', r'\1="..."', fragment)


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


class DerivedEntityCollection(me.EntityCollection):
    """Test helper subclass for nested collection HTML repr coverage."""


def test_repr_html_plain_collection_exact_snapshot(monkeypatch):
    """Freeze the plain collection HTML structure."""
    ec = me.EntityCollection("descr", M=me.M(1, "A/m"), a=[1, 2])

    expected_block = (
        "<div id='root' class='mammos-entity-collection-v2' "
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
        "<samp class='mammos-entity-inline-v2'>"
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
    assert ec._repr_html_() == (f"{_repr_css()}{ec._repr_html_block(root_id='mammos-entity-collection-v2-root')}")


def test_repr_html_details_script():
    """Check the expand/collapse-all script behavior without freezing formatting."""
    expanding = me.EntityCollection._repr_html_details_script("root", open_state=True)
    collapsing = me.EntityCollection._repr_html_details_script("root", open_state=False)

    for script in (expanding, collapsing):
        assert "const root = document.getElementById('root');" in script
        assert "if (!root || root.dataset.busy === 'true') return;" in script
        assert "const status = root.querySelector('.collection-status');" in script
        assert "const buttons = root.querySelectorAll('.collection-toolbar button');" in script
        assert "const details = Array.from(root.querySelectorAll('details.branch-item'));" in script
        assert "root.dataset.busy = 'true';" in script
        assert "root.setAttribute('aria-busy', 'true');" in script
        assert "buttons.forEach((button) => { button.disabled = true; });" in script
        assert "const batchSize = 50;" in script
        assert "if (index < details.length) { requestAnimationFrame(step); return; }" in script
        assert "requestAnimationFrame(() => { requestAnimationFrame(step); });" in script

    assert "if (status) status.textContent = 'Expanding...';" in expanding
    assert "element.open = true;" in expanding
    assert "if (status) status.textContent = 'Collapsing...';" in collapsing
    assert "element.open = false;" in collapsing


def test_repr_css_wraps_shared_stylesheet():
    css_file = importlib.resources.files("mammos_entity").joinpath("_entity_collection_repr.css")
    assert _repr_css() == f"<style>{css_file.read_text(encoding='utf-8')}</style>"


def test_repr_html_uses_value_repr_html_when_available():
    assert me.EntityCollection._repr_html_value("custom", HtmlValue()) == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>custom</div>"
        "<div class='entity-value'><span>custom html</span></div>"
        "</div>"
    )


def test_repr_html_falls_back_when_value_repr_html_raises():
    assert me.EntityCollection._repr_html_value("broken", BrokenHtmlValue()) == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>broken</div>"
        "<div class='entity-value'>BrokenHtmlValue()</div>"
        "</div>"
    )


def test_repr_html_falls_back_when_value_repr_html_returns_none():
    assert me.EntityCollection._repr_html_value("missing", NoneHtmlValue()) == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>missing</div>"
        "<div class='entity-value'>NoneHtmlValue()</div>"
        "</div>"
    )


def test_repr_html_value_toggle_script():
    """Lock the inline expand/collapse script for compact row values."""
    assert me.EntityCollection._repr_html_value_toggle_script(expanded=True) == (
        "const root = this.closest('.mammos-compact-value-v2');if (!root) return;root.dataset.expanded = 'true';"
    )
    assert me.EntityCollection._repr_html_value_toggle_script(expanded=False) == (
        "const root = this.closest('.mammos-compact-value-v2');if (!root) return;root.dataset.expanded = 'false';"
    )


def test_repr_html_long_numpy_array_compact_preview_snapshot():
    array = np.arange(24).reshape(4, 6)

    row_html = _strip_html_event_handlers(me.EntityCollection._repr_html_value("M", array))
    expanded_html = html.escape(me._entity._format_array_repr_expanded(array))

    assert row_html == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>M</div>"
        "<div class='entity-value'>"
        "<samp class='mammos-entity-inline-v2 mammos-compact-value-v2' "
        "data-expanded='false'>"
        "<span class='entity-collapsed entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Expand value' "
        'onclick="..." onkeydown="...">[+]</span>'
        "<span class='entity-summary-content'>"
        "<span>"
        "0&nbsp;1&nbsp;2&nbsp;...&nbsp;21&nbsp;22&nbsp;23"
        "</span>&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>shape=(4,&nbsp;6)</span>"
        "</span>"
        "</span>"
        "<span class='entity-expanded entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Collapse value' "
        'onclick="..." onkeydown="...">[−]</span>'
        "<span class='entity-summary-content'>"
        "<span>"
        "0&nbsp;1&nbsp;2&nbsp;...&nbsp;21&nbsp;22&nbsp;23"
        "</span>&nbsp;<span class='entity-meta'>·</span>&nbsp;"
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


def test_repr_html_long_quantity_compact_preview_snapshot():
    quantity = me.M(np.arange(24).reshape(4, 6), "A/m").quantity

    row_html = _strip_html_event_handlers(me.EntityCollection._repr_html_value("M_q", quantity))
    expanded_html = html.escape(me.EntityCollection._format_quantity_repr_expanded(quantity))

    assert row_html == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>M_q</div>"
        "<div class='entity-value'>"
        "<samp class='mammos-entity-inline-v2 mammos-compact-value-v2' "
        "data-expanded='false'>"
        "<span class='entity-collapsed entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Expand value' "
        'onclick="..." onkeydown="...">[+]</span>'
        "<span class='entity-summary-content'>"
        "<span>"
        "0.&nbsp;1.&nbsp;2.&nbsp;...&nbsp;21.&nbsp;22.&nbsp;23."
        "<span>&nbsp;A&nbsp;/&nbsp;m</span></span>"
        "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>shape=(4,&nbsp;6)</span>"
        "</span>"
        "</span>"
        "<span class='entity-expanded entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Collapse value' "
        'onclick="..." onkeydown="...">[−]</span>'
        "<span class='entity-summary-content'>"
        "<span>"
        "0.&nbsp;1.&nbsp;2.&nbsp;...&nbsp;21.&nbsp;22.&nbsp;23."
        "<span>&nbsp;A&nbsp;/&nbsp;m</span></span>"
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


def test_repr_html_short_quantity_stays_inline():
    quantity = u.Quantity(3, "A/m")

    assert me.EntityCollection._repr_html_value("H_q", quantity) == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>H_q</div>"
        "<div class='entity-value'>&lt;Quantity&nbsp;3.&nbsp;A&nbsp;/&nbsp;m&gt;</div>"
        "</div>"
    )


def test_repr_html_long_list_compact_preview_snapshot():
    value = list(range(120))

    row_html = _strip_html_event_handlers(me.EntityCollection._repr_html_value("L", value))
    expanded_html = html.escape(me.EntityCollection._format_sequence_repr_expanded(value))

    assert row_html == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>L</div>"
        "<div class='entity-value'>"
        "<samp class='mammos-entity-inline-v2 mammos-compact-value-v2' "
        "data-expanded='false'>"
        "<span class='entity-collapsed entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Expand value' "
        'onclick="..." onkeydown="...">[+]</span>'
        "<span class='entity-summary-content'>"
        "<span>"
        "[0,&nbsp;1,&nbsp;2,&nbsp;...,&nbsp;117,&nbsp;118,&nbsp;119]"
        "</span>&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>len=120</span>"
        "</span>"
        "</span>"
        "<span class='entity-expanded entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Collapse value' "
        'onclick="..." onkeydown="...">[−]</span>'
        "<span class='entity-summary-content'>"
        "<span>"
        "[0,&nbsp;1,&nbsp;2,&nbsp;...,&nbsp;117,&nbsp;118,&nbsp;119]"
        "</span>&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>len=120</span>"
        "</span>"
        "</span>"
        "<span class='entity-expanded-details'>"
        f"<span class='entity-full-value'>{expanded_html}</span>"
        "</span>"
        "</samp>"
        "</div>"
        "</div>"
    )


def test_repr_html_long_tuple_compact_preview_snapshot():
    value = tuple(range(120))

    row_html = _strip_html_event_handlers(me.EntityCollection._repr_html_value("T", value))
    expanded_html = html.escape(me.EntityCollection._format_sequence_repr_expanded(value))

    assert row_html == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>T</div>"
        "<div class='entity-value'>"
        "<samp class='mammos-entity-inline-v2 mammos-compact-value-v2' "
        "data-expanded='false'>"
        "<span class='entity-collapsed entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Expand value' "
        'onclick="..." onkeydown="...">[+]</span>'
        "<span class='entity-summary-content'>"
        "<span>"
        "(0,&nbsp;1,&nbsp;2,&nbsp;...,&nbsp;117,&nbsp;118,&nbsp;119)"
        "</span>&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>len=120</span>"
        "</span>"
        "</span>"
        "<span class='entity-expanded entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Collapse value' "
        'onclick="..." onkeydown="...">[−]</span>'
        "<span class='entity-summary-content'>"
        "<span>"
        "(0,&nbsp;1,&nbsp;2,&nbsp;...,&nbsp;117,&nbsp;118,&nbsp;119)"
        "</span>&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>len=120</span>"
        "</span>"
        "</span>"
        "<span class='entity-expanded-details'>"
        f"<span class='entity-full-value'>{expanded_html}</span>"
        "</span>"
        "</samp>"
        "</div>"
        "</div>"
    )


def test_repr_html_short_list_stays_inline():
    assert me.EntityCollection._repr_html_value("short", [1, 2, 3]) == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>short</div>"
        "<div class='entity-value'>[1,&nbsp;2,&nbsp;3]</div>"
        "</div>"
    )


def test_repr_html_long_mixed_list_uses_compact_preview():
    value = [1, "a", {"k": 3}, [4, 5], (6, 7)] * 30

    row_html = _strip_html_event_handlers(me.EntityCollection._repr_html_value("mixed", value))

    assert ("class='mammos-entity-inline-v2 mammos-compact-value-v2' data-expanded='false'") in row_html
    assert (
        "[1,&nbsp;&#x27;a&#x27;,&nbsp;{&#x27;k&#x27;:&nbsp;3},"
        "&nbsp;...,&nbsp;{&#x27;k&#x27;:&nbsp;3},&nbsp;[4,&nbsp;5],"
        "&nbsp;(6,&nbsp;7)]"
    ) in row_html
    assert ("&nbsp;<span class='entity-meta'>·</span>&nbsp;<span class='entity-meta'>len=150</span>") in row_html
    assert "class='entity-full-value'>" in row_html


def test_repr_html_long_dict_compact_preview_snapshot():
    value = {f"k{i}": i for i in range(120)}

    row_html = _strip_html_event_handlers(me.EntityCollection._repr_html_value("D", value))
    expanded_html = html.escape(me.EntityCollection._format_dict_repr_expanded(value))

    assert row_html == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>D</div>"
        "<div class='entity-value'>"
        "<samp class='mammos-entity-inline-v2 mammos-compact-value-v2' "
        "data-expanded='false'>"
        "<span class='entity-collapsed entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Expand value' "
        'onclick="..." onkeydown="...">[+]</span>'
        "<span class='entity-summary-content'>"
        "<span>"
        "{&#x27;k0&#x27;:&nbsp;0,&nbsp;&#x27;k1&#x27;:&nbsp;1,"
        "&nbsp;&#x27;k2&#x27;:&nbsp;2,&nbsp;...,&nbsp;&#x27;k117&#x27;:&nbsp;117,"
        "&nbsp;&#x27;k118&#x27;:&nbsp;118,&nbsp;&#x27;k119&#x27;:&nbsp;119}"
        "</span>&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>len=120</span>"
        "</span>"
        "</span>"
        "<span class='entity-expanded entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Collapse value' "
        'onclick="..." onkeydown="...">[−]</span>'
        "<span class='entity-summary-content'>"
        "<span>"
        "{&#x27;k0&#x27;:&nbsp;0,&nbsp;&#x27;k1&#x27;:&nbsp;1,"
        "&nbsp;&#x27;k2&#x27;:&nbsp;2,&nbsp;...,&nbsp;&#x27;k117&#x27;:&nbsp;117,"
        "&nbsp;&#x27;k118&#x27;:&nbsp;118,&nbsp;&#x27;k119&#x27;:&nbsp;119}"
        "</span>&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>len=120</span>"
        "</span>"
        "</span>"
        "<span class='entity-expanded-details'>"
        f"<span class='entity-full-value'>{expanded_html}</span>"
        "</span>"
        "</samp>"
        "</div>"
        "</div>"
    )


def test_repr_html_short_dict_stays_inline():
    assert me.EntityCollection._repr_html_value("short_d", {"a": 1, "b": 2}) == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>short_d</div>"
        "<div class='entity-value'>"
        "{&#x27;a&#x27;:&nbsp;1,&nbsp;&#x27;b&#x27;:&nbsp;2}"
        "</div>"
        "</div>"
    )


def test_repr_html_nested_collection_exact_snapshot():
    """Freeze the nested collection HTML structure while ignoring JS formatting."""
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
        "<samp class='mammos-entity-inline-v2'>"
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

    ec = me.EntityCollection(outer=1, inner=inner)
    assert _strip_html_event_handlers(ec._repr_html_block(root_id="root")) == (
        "<div id='root' class='mammos-entity-collection-v2' "
        "data-busy='false' aria-busy='false'>"
        "<div class='collection-header'>"
        "<div class='collection-title'><span>EntityCollection</span></div>"
        "<div class='collection-toolbar'>"
        "<button type='button' title='Collapse all' aria-label='Collapse all' "
        'onclick="...">▸</button>'
        "<button type='button' title='Expand all' aria-label='Expand all' "
        'onclick="...">▾</button>'
        "<span class='collection-status' aria-live='polite'></span>"
        "</div>"
        "</div>"
        "<div class='collection-body'>"
        "<div class='collection-children'>"
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>outer</div>"
        "<div class='entity-value'>1</div>"
        "</div>"
        f"{expected_nested}"
        "</div>"
        "</div>"
        "</div>"
    )


def test_repr_html_embeds_long_entity_value_preview():
    entity = me.M(np.arange(24).reshape(4, 6), "A/m")
    row_html = me.EntityCollection._repr_html_value("M", entity)

    assert row_html == (
        "<div class='branch-item entity-row'>"
        "<div class='entity-key'>M</div>"
        f"<div class='entity-value'>{entity._repr_html_fragment_()}</div>"
        "</div>"
    )


def test_repr_html_subclass_treats_base_collection_values_as_nested():
    inner = me.EntityCollection(T=me.T(2))
    ec = DerivedEntityCollection(inner=inner)

    assert ec._repr_html_block(root_id="root") == (
        "<div id='root' class='mammos-entity-collection-v2' "
        "data-busy='false' aria-busy='false'>"
        "<div class='collection-header'>"
        "<div class='collection-title'><span>DerivedEntityCollection</span></div>"
        f"{DerivedEntityCollection._repr_html_controls('root')}"
        "</div>"
        "<div class='collection-body'>"
        "<div class='collection-children'>"
        f"{inner._repr_html_nested('inner')}"
        "</div>"
        "</div>"
        "</div>"
    )
