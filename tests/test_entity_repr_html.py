import html
import re

import numpy as np

import mammos_entity as me
import mammos_entity._repr as repr_module
from mammos_entity._repr import _repr_css


def _strip_html_event_handlers(fragment: str) -> str:
    """Normalize inline event handlers in HTML repr snapshots."""
    return re.sub(r'(onclick|onkeydown)="[^"]*"', r'\1="..."', fragment)


def _expected_inline_entity_fragment(
    label: str,
    value_html: str,
    *,
    description_html: str = "",
    meta_html: str = "",
) -> str:
    """Render the expected HTML for a non-collapsible entity repr."""
    description_suffix = f"<br>{description_html}" if description_html else ""
    return (
        "<samp class='mammos-entity-inline'>"
        f"<span class='entity-label'>{label}</span>"
        "&nbsp;<span class='entity-meta'>·</span>&nbsp;"
        f"<span>{value_html}</span>"
        f"{meta_html}"
        f"{description_suffix}"
        "</samp>"
    )


def _expected_entity_collapsible_html(summary_inner_html: str, expanded_html: str) -> str:
    """Render the shared expected HTML shell for long entity values."""
    summary_content_html = f"<span class='entity-summary-content'><span>{summary_inner_html}</span></span>"
    return (
        "<span class='entity-collapsed entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Expand value' "
        'onclick="..." onkeydown="...">[+]</span>'
        f"{summary_content_html}"
        "</span>"
        "<span class='entity-expanded entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Collapse value' "
        'onclick="..." onkeydown="...">[−]</span>'
        f"{summary_content_html}"
        "</span>"
        "<span class='entity-expanded-details'>"
        f"<span class='entity-full-value'>{expanded_html}</span>"
        "</span>"
    )


def _expected_collapsible_entity_fragment(
    label: str,
    summary_inner_html: str,
    expanded_html: str,
    *,
    description_html: str = "",
    meta_html: str = "",
) -> str:
    """Render the expected HTML for a collapsible entity repr."""
    description_prefix = f"{description_html}<br>" if description_html else ""
    return (
        "<samp class='mammos-entity-inline' data-expanded='false'>"
        f"<span class='entity-label'>{label}</span>"
        f"{meta_html}"
        "<br>"
        f"{description_prefix}"
        f"{_expected_entity_collapsible_html(summary_inner_html, expanded_html)}"
        "</samp>"
    )


def test_repr_html_short_entity_exact_snapshot():
    """Freeze the short-entity HTML structure."""
    e = me.Entity("CurieTemperature", 300, description="measured <carefully>")

    fragment = e._repr_html_fragment_()

    assert fragment == _expected_inline_entity_fragment(
        "CurieTemperature",
        "300.0&nbsp;K",
        description_html="<em>measured &lt;carefully&gt;</em>",
    )
    assert e._repr_html_() == f"{_repr_css()}{fragment}"


def test_repr_html_dimensionless():
    """Dimensionless entities stay inline and omit a unit suffix."""
    e = me.Entity("DemagnetizingFactor", 0.3)
    fragment = e._repr_html_fragment_()

    assert "DemagnetizingFactor" in fragment
    assert "<span>0.3</span>" in fragment
    assert "entity-collapsed" not in fragment
    assert "&nbsp;K" not in fragment


def test_repr_html_small_array_stays_single_line():
    """Small arrays stay inline and still expose shape metadata."""
    e = me.Entity("ThermodynamicTemperature", [[1, 2], [3, 4]], "K")
    fragment = e._repr_html_fragment_()

    assert "ThermodynamicTemperature" in fragment
    assert "[[1.&nbsp;2.]&nbsp;[3.&nbsp;4.]]&nbsp;K" in fragment
    assert "shape=(2,&nbsp;2)" in fragment
    assert "data-expanded='false'" not in fragment


def test_format_array_repr_summary_flattens_preview():
    e = me.Entity("ExternalMagneticField", np.arange(24).reshape(4, 6), "A/m")

    assert me._repr._format_array_repr_summary(e.value) == "0. 1. 2. ... 21. 22. 23."


def test_format_array_repr_expanded_uses_numpy_repr_with_threshold():
    e = me.Entity("ExternalMagneticField", np.arange(1001), "A/m")

    with np.printoptions(
        threshold=100,
        edgeitems=me._repr._array_repr_expanded_edgeitems(e.value),
    ):
        expected = repr(np.asarray(e.value))

    assert me._repr._format_array_repr_expanded(e.value) == expected


def test_array_repr_expanded_edgeitems_scale_with_rank():
    assert me._repr._array_repr_expanded_edgeitems(np.arange(300)) == 50
    assert me._repr._array_repr_expanded_edgeitems(np.arange(400).reshape(20, 20)) == 5
    assert me._repr._array_repr_expanded_edgeitems(np.arange(10 * 500 * 20).reshape(10, 500, 20)) == 2


def test_format_array_repr_expanded_shows_large_1d_context():
    e = me.Entity("ExternalMagneticField", np.arange(300), "A/m")

    expanded = me._repr._format_array_repr_expanded(e.value)
    head, tail = expanded.split("...", maxsplit=1)

    assert "49." in head
    assert "50." not in head
    assert "249." not in tail
    assert "250." in tail


def test_repr_html_toggle_script():
    """Toggle scripts target the right root class and expanded state."""
    expanding = repr_module._repr_html_toggle_script("mammos-entity-inline", expanded=True)
    collapsing = repr_module._repr_html_toggle_script("mammos-entity-inline", expanded=False)

    assert "closest('.mammos-entity-inline')" in expanding
    assert "dataset.expanded = 'true'" in expanding
    assert "closest('.mammos-entity-inline')" in collapsing
    assert "dataset.expanded = 'false'" in collapsing


def test_repr_html_long_value_exact_snapshot():
    """Freeze the long-value HTML structure while ignoring JS formatting details."""
    e = me.Entity("ExternalMagneticField", np.arange(24).reshape(4, 6), "A/m")

    fragment = _strip_html_event_handlers(e._repr_html_fragment_())
    expanded_html = html.escape(me._repr._format_array_repr_expanded(e.value))

    assert fragment == _expected_collapsible_entity_fragment(
        "ExternalMagneticField",
        "0.&nbsp;1.&nbsp;2.&nbsp;...&nbsp;21.&nbsp;22.&nbsp;23.<span>&nbsp;A&nbsp;/&nbsp;m</span>",
        expanded_html,
        meta_html="&nbsp;<span class='entity-meta'>·</span>&nbsp;<span class='entity-meta'>shape=(4,&nbsp;6)</span>",
    )


def test_repr_html_large_1d_array_uses_summary_and_bounded_numpy_expansion():
    e = me.Entity("ExternalMagneticField", np.arange(1001), "A/m")

    fragment = e._repr_html_fragment_()
    expanded_html = html.escape(me._repr._format_array_repr_expanded(e.value))

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
