import importlib.resources
import re

import mammos_units as u
import numpy as np
import pandas as pd
import pytest

import mammos_entity as me
import mammos_entity._entity_collection as entity_collection_module
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


def test_entity_collection_with_description():
    """Check that the description of an EntityCollection is well defined."""
    ec = me.EntityCollection("Magnetization on a grid.", x=[0, 0, 1, 1], y=[0, 1, 0, 1], M=me.M([1, 2, 3, 4]))
    assert ec.description == "Magnetization on a grid."
    assert [name for name, _entity in ec] == ["x", "y", "M"]

    ec.T = me.T(2)
    assert [name for name, _entity in ec] == ["x", "y", "M", "T"]

    # changing class elements does not change the entities
    ec.description = "A new description"
    assert [name for name, _entity in ec] == ["x", "y", "M", "T"]
    assert ec.description == "A new description"
    del ec.T
    assert [name for name, _entity in ec] == ["x", "y", "M"]


def test_entity_name_clash():
    ec = me.EntityCollection(to_dataframe=me.Ms())
    assert [name for name, _entity in ec] == ["to_dataframe"]
    assert callable(ec.to_dataframe)
    assert ec["to_dataframe"] == me.Ms()

    ec.to_dataframe = "missing"
    assert [name for name, _entity in ec] == ["to_dataframe"]
    assert ec.to_dataframe == "missing"
    assert ec["to_dataframe"] == me.Ms()

    # 'description' can be used as entity-like name if accessed via dict interface
    ec["description"] = me.T()
    assert isinstance(ec["description"], me.Entity)
    assert ec.description == ""


def test_entity_name_must_be_string():
    ec = me.EntityCollection()
    with pytest.raises(TypeError, match="Name must be a string"):
        ec[1] = me.Ms()


def test_add_remove_entities():
    ec = me.EntityCollection()
    assert [name for name, _entity in ec] == []

    ec.Ms = me.Ms()
    ec.A = me.A()
    ec["T center"] = me.T()

    assert [name for name, _entity in ec] == ["Ms", "A", "T center"]

    assert ec["Ms"] == me.Ms()
    assert me.A() == ec.A
    assert ec["T center"] == me.T()

    del ec.Ms
    del ec["A"]
    assert [name for name, _entity in ec] == ["T center"]

    del ec["T center"]
    assert [name for name, _entity in ec] == []


def test_iter():
    Ms = me.Ms([1, 2, 3])
    T = me.T(100)
    ec = me.EntityCollection(Ms=Ms, T=T)

    assert list(ec) == [("Ms", Ms), ("T", T)]


def test_contains():
    ec = me.EntityCollection(Ms=me.Ms())

    assert "Ms" in ec
    assert "Js" not in ec

    # checks only for entities, nothing else
    assert "description" not in ec
    assert "to_dataframe" not in ec


def test_dir():
    ec = me.EntityCollection(Ms=me.Ms())
    ec["T center"] = me.T()

    assert "Ms" in dir(ec)
    assert "T center" in dir(ec)


def test_bad_description():
    """Check bad type for description of an EntityCollection."""
    with pytest.raises(ValueError):
        me.EntityCollection(description=1)


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
        entity_collection_module.uuid,
        "uuid4",
        lambda: type("DummyUuid", (), {"hex": "root"})(),
    )
    assert ec._repr_html_() == (
        f"{_repr_css()}{ec._repr_html_block(root_id='mammos-entity-collection-v2-root')}"
    )


def test_repr_html_details_script():
    """Check the expand/collapse-all script behavior without freezing formatting."""
    expanding = me.EntityCollection._repr_html_details_script("root", open_state=True)
    collapsing = me.EntityCollection._repr_html_details_script("root", open_state=False)

    for script in (expanding, collapsing):
        assert "const root = document.getElementById('root');" in script
        assert "if (!root || root.dataset.busy === 'true') return;" in script
        assert "const status = root.querySelector('.collection-status');" in script
        assert (
            "const buttons = root.querySelectorAll('.collection-toolbar button');"
            in script
        )
        assert (
            "const details = Array.from(root.querySelectorAll('details.branch-item'));"
            in script
        )
        assert "root.dataset.busy = 'true';" in script
        assert "root.setAttribute('aria-busy', 'true');" in script
        assert "buttons.forEach((button) => { button.disabled = true; });" in script
        assert "const batchSize = 50;" in script
        assert (
            "if (index < details.length) { requestAnimationFrame(step); return; }"
            in script
        )
        assert (
            "requestAnimationFrame(() => { requestAnimationFrame(step); });" in script
        )

    assert "if (status) status.textContent = 'Expanding...';" in expanding
    assert "element.open = true;" in expanding
    assert "if (status) status.textContent = 'Collapsing...';" in collapsing
    assert "element.open = false;" in collapsing


def test_repr_css_wraps_shared_stylesheet():
    css_file = importlib.resources.files("mammos_entity").joinpath(
        "_entity_collection_repr.css"
    )
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


def test_metadata():
    ec = me.EntityCollection(
        "descr",
        M=me.M(1, "A/m"),
        Tc=me.Tc(1, "K", description="low"),
        T_q=me.T(1, "K").q,
        V=1,
    )
    reference = {
        "M": {"ontology_label": "Magnetization", "unit": "A / m", "description": ""},
        "Tc": {"ontology_label": "CurieTemperature", "unit": "K", "description": "low"},
        "T_q": {"unit": "K"},
        "V": {},
    }
    assert ec.metadata() == reference


def test_to_dataframe():
    """Check that the conversion to DataFrame works as intended."""
    ec = me.EntityCollection(
        "Magnetization on a grid.",
        x=[0, 0, 1, 1],
        M=me.M([1, 2, 3, 4]),
        T=me.T([100, 200, 300, 400], "mK"),
    )
    df = pd.DataFrame(
        {
            "x": [0, 0, 1, 1],
            "M": [1.0, 2.0, 3.0, 4.0],
            "T": [100.0, 200.0, 300.0, 400.0],
        }
    )
    assert df.equals(ec.to_dataframe())
    df_with_units = pd.DataFrame(
        {
            "x": [0, 0, 1, 1],
            "M (A / m)": [1.0, 2.0, 3.0, 4.0],
            "T (mK)": [100.0, 200.0, 300.0, 400.0],
        }
    )
    assert df_with_units.equals(ec.to_dataframe(include_units=True))


def test_to_dataframe_scalar():
    ec = me.EntityCollection(Ms=me.Ms(0), Tc=me.Tc(0))
    df = pd.DataFrame({"Ms": 0.0, "Tc": 0.0}, index=[0])
    assert df.equals(ec.to_dataframe())


def test_to_dataframe_unsupported():
    col1 = me.EntityCollection(Ms=me.Ms([[1, 2], [3, 4]]))
    with pytest.raises(ValueError):
        col1.to_dataframe()

    col2 = me.EntityCollection(Ms=me.Ms(), sub=me.EntityCollection())
    with pytest.raises(ValueError, match="Nested collection"):
        col2.to_dataframe()


def test_from_dataframe():
    data = pd.DataFrame({"M": [1, 2], "T": [3, 4], "l_q": [5, 6], "x": [7, 8]})
    metadata = {
        "M": {"ontology_label": "Magnetization", "unit": "kA/m", "description": "abc"},
        "T": {"ontology_label": "ThermodynamicTemperature"},
        "l_q": {"unit": "m"},
        "x": {},
    }
    collection = me.EntityCollection.from_dataframe(data, metadata, description="desc")
    assert collection.description == "desc"
    assert me.M([1, 2], "kA/m") == collection.M
    assert collection.M.description == "abc"
    assert me.T([3, 4], "K") == collection.T
    assert all([5, 6] * u.m == collection.l_q)
    assert all(collection.x == [7, 8])
    assert [name for name, _entity in collection] == ["M", "T", "l_q", "x"]


def test_dataframe_roundtrip():
    M = me.M([1, 2])
    Tq = me.T([3, 4]).q
    V = [5, 6]
    col = me.EntityCollection("descr", M=M, Tq=Tq, V=V)
    col["name with spaces"] = [0, 0]
    col["description"] = [1, 1]
    col_new = me.EntityCollection.from_dataframe(col.to_dataframe(), col.metadata(), col.description)
    assert col_new.M == M
    assert all(col_new.Tq == Tq)
    assert all(col_new.V == V)
    assert col_new.description == "descr"
    assert [name for name, _entity in col_new] == [
        "M",
        "Tq",
        "V",
        "name with spaces",
        "description",
    ]
