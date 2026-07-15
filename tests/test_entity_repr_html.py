import html
import re

import numpy as np

import mammos_entity as me
from mammos_entity._repr import _repr_css


def _strip_html_event_handlers(fragment: str) -> str:
    """Normalize inline event handlers in HTML repr snapshots."""
    return re.sub(r'(onclick|onkeydown)="[^"]*"', r'\1="..."', fragment)


def test_repr_html_short_entity_exact_snapshot():
    """Freeze the short-entity HTML structure."""
    e = me.Entity("CurieTemperature", 300, description="measured <carefully>")

    fragment = e._repr_html_fragment_()

    assert fragment == (
        "<samp class='mammos-entity-inline-v2'>"
        "<span class='entity-label'>CurieTemperature</span>"
        "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span>300.0&nbsp;K</span>"
        "<br><em>measured &lt;carefully&gt;</em>"
        "</samp>"
    )
    assert e._repr_html_() == f"{_repr_css()}{fragment}"


def test_repr_html_dimensionless():
    """Test HTML repr for dimensionless entities."""
    e = me.Entity("DemagnetizingFactor", 0.3)

    assert e._repr_html_fragment_() == (
        "<samp class='mammos-entity-inline-v2'>"
        "<span class='entity-label'>DemagnetizingFactor</span>"
        "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span>0.3</span>"
        "</samp>"
    )


def test_repr_html_small_array_stays_single_line():
    """Test that compact arrays stay on one line."""
    e = me.Entity("ThermodynamicTemperature", [[1, 2], [3, 4]], "K")

    assert e._repr_html_fragment_() == (
        "<samp class='mammos-entity-inline-v2'>"
        "<span class='entity-label'>ThermodynamicTemperature</span>"
        "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span>[[1.&nbsp;2.]&nbsp;[3.&nbsp;4.]]&nbsp;K</span>"
        "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>shape=(2,&nbsp;2)</span>"
        "</samp>"
    )


def test_format_array_repr_summary_flattens_preview():
    e = me.Entity("ExternalMagneticField", np.arange(24).reshape(4, 6), "A/m")

    assert me._entity._format_array_repr_summary(e.value) == "0. 1. 2. ... 21. 22. 23."


def test_format_array_repr_expanded_uses_numpy_repr_with_threshold():
    e = me.Entity("ExternalMagneticField", np.arange(1001), "A/m")

    with np.printoptions(
        threshold=100,
        edgeitems=me._entity._array_repr_expanded_edgeitems(e.value),
    ):
        expected = repr(np.asarray(e.value))

    assert me._entity._format_array_repr_expanded(e.value) == expected


def test_array_repr_expanded_edgeitems_scale_with_rank():
    assert me._entity._array_repr_expanded_edgeitems(np.arange(300)) == 50
    assert me._entity._array_repr_expanded_edgeitems(np.arange(400).reshape(20, 20)) == 5
    assert me._entity._array_repr_expanded_edgeitems(np.arange(10 * 500 * 20).reshape(10, 500, 20)) == 2


def test_format_array_repr_expanded_shows_large_1d_context():
    e = me.Entity("ExternalMagneticField", np.arange(300), "A/m")

    expanded = me._entity._format_array_repr_expanded(e.value)
    head, tail = expanded.split("...", maxsplit=1)

    assert "49." in head
    assert "50." not in head
    assert "249." not in tail
    assert "250." in tail


def test_repr_html_toggle_script():
    """Lock the inline expand/collapse script separately from the HTML snapshot."""
    assert me.Entity._repr_html_toggle_script(expanded=True) == (
        "const root = this.closest('.mammos-entity-inline-v2');if (!root) return;root.dataset.expanded = 'true';"
    )
    assert me.Entity._repr_html_toggle_script(expanded=False) == (
        "const root = this.closest('.mammos-entity-inline-v2');if (!root) return;root.dataset.expanded = 'false';"
    )


def test_repr_html_long_value_exact_snapshot():
    """Freeze the long-value HTML structure while ignoring JS formatting details."""
    e = me.Entity("ExternalMagneticField", np.arange(24).reshape(4, 6), "A/m")

    fragment = _strip_html_event_handlers(e._repr_html_fragment_())
    expanded_html = html.escape(me._entity._format_array_repr_expanded(e.value))

    assert fragment == (
        "<samp class='mammos-entity-inline-v2' data-expanded='false'>"
        "<span class='entity-label'>ExternalMagneticField</span>"
        "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        "<span class='entity-meta'>shape=(4,&nbsp;6)</span>"
        "<br>"
        "<span class='entity-collapsed entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Expand value' "
        'onclick="..." onkeydown="...">[+]</span>'
        "<span class='entity-summary-content'>"
        "<span>"
        "0.&nbsp;1.&nbsp;2.&nbsp;...&nbsp;21.&nbsp;22.&nbsp;23."
        "<span>&nbsp;A&nbsp;/&nbsp;m</span></span>"
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
        "</span>"
        "</span>"
        "<span class='entity-expanded-details'>"
        f"<span class='entity-full-value'>{expanded_html}</span>"
        "</span>"
        "</samp>"
    )


def test_repr_html_large_1d_array_uses_summary_and_bounded_numpy_expansion():
    e = me.Entity("ExternalMagneticField", np.arange(1001), "A/m")

    fragment = e._repr_html_fragment_()
    expanded_html = html.escape(me._entity._format_array_repr_expanded(e.value))

    assert ("&nbsp;<span class='entity-meta'>·</span>&nbsp;<span class='entity-meta'>shape=(1001,)</span>") in fragment
    assert (
        "<span class='entity-summary-content'>"
        "<span>"
        "0.&nbsp;1.&nbsp;2.&nbsp;...&nbsp;998.&nbsp;999.&nbsp;1000."
        "<span>&nbsp;A&nbsp;/&nbsp;m</span></span>"
        "</span>"
    ) in fragment
    assert f"<span class='entity-full-value'>{expanded_html}</span>" in fragment


def test_repr_html_long_value_places_description_above_preview():
    e = me.Entity(
        "ExternalMagneticField",
        np.arange(24).reshape(4, 6),
        "A/m",
        description="measured <carefully>",
    )

    fragment = e._repr_html_fragment_()

    assert "<em>measured &lt;carefully&gt;</em>" in fragment
    assert fragment.index("<em>measured &lt;carefully&gt;</em>") < fragment.index(
        "class='entity-collapsed entity-summary'"
    )
