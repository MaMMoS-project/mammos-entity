import mammos_units as u
import pandas as pd
import pytest

import mammos_entity as me


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


def test_repr_html():
    ec = me.EntityCollection("descr", M=me.M(1, "A/m"), a=[1, 2])

    html = ec._repr_html_()

    assert html.startswith("<style>")
    assert html.count("<style>") == 1
    assert "class='mammos-entity-collection'" in html
    assert "data-busy='false'" in html
    assert "aria-busy='false'" in html
    assert "class='collection-header'" in html
    assert "class='collection-title'" in html
    assert "<span>EntityCollection</span>" in html
    assert "class='collection-body'" in html
    assert "class='collection-children'" in html
    assert "<div class='branch-item collection-description'>descr</div>" in html
    assert html.count("class='branch-item entity-row'") == 2
    assert "<div class='entity-key'>M</div>" in html
    assert "<div class='entity-value'><samp>Magnetization(" in html
    assert "&nbsp;unit=A&nbsp;/&nbsp;m)</samp></div>" in html
    assert "<div class='entity-key'>a</div>" in html
    assert "<div class='entity-value'>[1,&nbsp;2]</div>" in html
    assert "<details" not in html
    assert "EntityCollection(" not in html
    assert "EntityCollection)" not in html
    assert "Expand all" not in html
    assert "Collapse all" not in html


def test_repr_html_uses_value_repr_html_when_available():
    ec = me.EntityCollection(custom=HtmlValue())

    html = ec._repr_html_()

    assert "<div class='entity-key'>custom</div>" in html
    assert (
        "<div class='branch-item entity-row'><div class='entity-key'>custom</div>"
        "<div class='entity-value'><span>custom html</span></div></div>"
    ) in html


def test_repr_html_falls_back_when_value_repr_html_raises():
    ec = me.EntityCollection(custom=HtmlValue(), broken=BrokenHtmlValue())

    html = ec._repr_html_()

    assert (
        "<div class='branch-item entity-row'><div class='entity-key'>custom</div>"
        "<div class='entity-value'><span>custom html</span></div></div>"
    ) in html
    assert (
        "<div class='branch-item entity-row'><div class='entity-key'>broken</div>"
        "<div class='entity-value'>BrokenHtmlValue()</div></div>"
    ) in html


def test_repr_html_nested_collection_keeps_content_in_details():
    ec = me.EntityCollection(
        outer=1,
        inner=me.EntityCollection("inner descr", T=me.T(2)),
    )

    html = ec._repr_html_()

    assert html.count("<style>") == 1
    assert html.count("class='mammos-entity-collection'") == 1
    assert "<details class='branch-item'>" in html
    assert "class='collection-toolbar'" in html
    assert "ontoggle=" not in html
    assert "<template data-entity-collection-template>" not in html
    assert "title='Expand all'" in html
    assert "title='Collapse all'" in html
    assert "aria-label='Expand all'" in html
    assert "aria-label='Collapse all'" in html
    assert "class='collection-status' aria-live='polite'" in html
    assert ">▾</button>" in html
    assert ">▸</button>" in html
    assert html.index("title='Collapse all'") < html.index("title='Expand all'")
    assert html.count("<button type='button'") == 2
    assert html.count("onclick=") == 2
    assert "root.dataset.busy = 'true';" in html
    assert "root.dataset.busy = 'false';" in html
    assert "status.textContent = 'Expanding...';" in html
    assert "status.textContent = 'Collapsing...';" in html
    assert "button.disabled = true;" in html
    assert "button.disabled = false;" in html
    assert "requestAnimationFrame(() => { requestAnimationFrame(step); });" in html
    assert "<summary>" in html
    assert "<span class='summary-key'>inner</span>" in html
    assert (
        "<span class='summary-preview'>EntityCollection&nbsp;·&nbsp;"
        "1&nbsp;item&nbsp;·&nbsp;T</span>"
    ) in html
    assert "class='collection-children nested-children'" in html
    assert (
        "<div class='branch-item collection-description'>inner&nbsp;descr</div>"
    ) in html
    assert "description=&#x27;&#x27;" not in html
    assert "<div class='entity-key'>T</div>" in html
    assert "<div class='entity-value'><samp>ThermodynamicTemperature(" in html
    assert "&nbsp;unit=K)</samp></div>" in html
    assert "EntityCollection(" not in html


def test_repr_html_subclass_treats_base_collection_values_as_nested():
    ec = DerivedEntityCollection(inner=me.EntityCollection(T=me.T(2)))

    html = ec._repr_html_()

    assert "<span>DerivedEntityCollection</span>" in html
    assert "title='Expand all'" in html
    assert "title='Collapse all'" in html
    assert html.count("<style>") == 1
    assert html.count("id='mammos-entity-collection-") == 1
    assert (
        "<details class='branch-item'><summary><span class='summary-key'>inner</span>"
    ) in html
    assert (
        "<span class='summary-preview'>EntityCollection&nbsp;·&nbsp;"
        "1&nbsp;item&nbsp;·&nbsp;T</span>"
    ) in html


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
