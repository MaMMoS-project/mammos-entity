import mammos_units as u
import pandas as pd
import pytest

import mammos_entity as me


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


def test_metadata():
    onto_1 = me.Ontology(
        iris=[
            "https://w3id.org/emmo/domain/magnetic-materials/0.0.5",
        ],
        initialize=True,
    )
    onto_2 = me.Ontology(
        iris=[
            "https://w3id.org/emmo/1.0.3/inferred",
        ],
        initialize=True,
    )
    onto_3 = me.Ontology(
        iris=[
            "https://w3id.org/emmo/1.0.2/inferred",
        ],
        initialize=True,
    )
    onto_4 = me.Ontology(
        iris=[
            "https://w3id.org/emmo/domain/electrochemistry/0.37.2/",
        ],
        initialize=True,
    )
    ec = me.EntityCollection(
        "descr",
        Ms=onto_1.Entity("SpontaneousMagnetization", 1, "kA / m"),
        T=onto_2.Entity("ThermodynamicTemperature", 2, "mK", description="low"),
        T_old=onto_3.Entity("ThermodynamicTemperature", 2.55, "mK", description="low"),
        DisCa=onto_4.Entity("DischargingCapacity", 3, "mA s"),
        T_q=me.T(1, "K").q,
        V=1,
    )
    reference = {
        "Ms": {
            "ontology_label": "SpontaneousMagnetization",
            "ontology_iri": "https://w3id.org/emmo/domain/magnetic-materials/0.0.5",
            "entity_iri": "https://w3id.org/emmo/domain/magnetic-materials#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25",
            "unit": "kA / m",
            "description": "",
        },
        "T": {
            "ontology_label": "ThermodynamicTemperature",
            "ontology_iri": "https://w3id.org/1.0.3/emmo",
            "entity_iri": "https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f",
            "unit": "mK",
            "description": "low",
        },
        "T_old": {
            "ontology_label": "ThermodynamicTemperature",
            "ontology_iri": "https://w3id.org/emmo/1.0.2/emmo",
            "entity_iri": "https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f",
            "unit": "mK",
            "description": "low",
        },
        "DisCa": {
            "ontology_label": "DischargingCapacity",
            "ontology_iri": "https://w3id.org/emmo/domain/electrochemistry/0.37.2/electrochemistry",
            "entity_iri": "https://w3id.org/emmo/domain/electrochemistry#electrochemistry_0141b5c2_9f15_46f4_82e6_92a104faa476",
            "unit": "mA s",
            "description": "",
        },
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
    data = pd.DataFrame(
        {"Ms": [1, 2], "T": [3, 4], "T_old": [3.5, 4.5], "DisCa": [10, 15], "T_q": [300, 400], "V": [7, 8]}
    )
    metadata = {
        "Ms": {
            "ontology_label": "SpontaneousMagnetization",
            "ontology_iri": "https://w3id.org/emmo/domain/magnetic-materials/0.0.5",
            "entity_iri": "https://w3id.org/emmo/domain/magnetic-materials#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25",
            "unit": "kA / m",
            "description": "abc",
        },
        "T": {
            "ontology_label": "ThermodynamicTemperature",
            "ontology_iri": "https://w3id.org/1.0.3/emmo",
            "entity_iri": "https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f",
            "unit": "mK",
            "description": "low",
        },
        "T_old": {
            "ontology_label": "ThermodynamicTemperature",
            "ontology_iri": "https://w3id.org/emmo/1.0.2/emmo",
            "entity_iri": "https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f",
            "unit": "mK",
            "description": "low",
        },
        "DisCa": {
            "ontology_label": "DischargingCapacity",
            "ontology_iri": "https://w3id.org/emmo/domain/electrochemistry/0.37.2/electrochemistry",
            "entity_iri": "https://w3id.org/emmo/domain/electrochemistry#electrochemistry_0141b5c2_9f15_46f4_82e6_92a104faa476",
            "unit": "mA s",
            "description": "",
        },
        "T_q": {"unit": "K"},
        "V": {},
    }
    collection = me.EntityCollection.from_dataframe(data, metadata, description="desc")
    assert collection.description == "desc"
    assert u.allclose(collection.Ms.q, [1, 2] * u.kA / u.m)
    assert collection.Ms.ontology_label == "SpontaneousMagnetization"
    assert collection.Ms.ontology_iri == "https://w3id.org/emmo/domain/magnetic-materials/0.0.5"
    assert (
        collection.Ms.entity_iri
        == "https://w3id.org/emmo/domain/magnetic-materials#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25"
    )
    assert collection.Ms.description == "abc"
    assert u.allclose(collection.T.q, [3, 4] * u.mK)
    assert collection.T.ontology_label == "ThermodynamicTemperature"
    assert collection.T.ontology_iri == "https://w3id.org/1.0.3/emmo"
    assert collection.T.entity_iri == "https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f"
    assert collection.T.description == "low"
    assert u.allclose(collection.T_old.q, [3.5, 4.5] * u.mK)
    assert collection.T_old.ontology_label == "ThermodynamicTemperature"
    assert collection.T_old.ontology_iri == "https://w3id.org/emmo/1.0.2/emmo"
    assert collection.T_old.entity_iri == "https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f"
    assert collection.T_old.description == "low"
    assert u.allclose(collection.DisCa.q, [10, 15] * u.mA * u.s)
    assert collection.DisCa.ontology_label == "DischargingCapacity"
    assert collection.DisCa.ontology_iri == "https://w3id.org/emmo/domain/electrochemistry/0.37.2/electrochemistry"
    assert (
        collection.DisCa.entity_iri
        == "https://w3id.org/emmo/domain/electrochemistry#electrochemistry_0141b5c2_9f15_46f4_82e6_92a104faa476"
    )
    assert collection.DisCa.description == ""
    assert u.allclose([300, 400] * u.K, collection.T_q)
    assert all(collection.V == [7, 8])
    assert [name for name, _entity in collection] == ["Ms", "T", "T_old", "DisCa", "T_q", "V"]


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


def test_ipython_key_completions_():
    col = me.EntityCollection()
    assert col._ipython_key_completions_() == []

    col = me.EntityCollection(a=1, b=2)
    assert col._ipython_key_completions_() == ["a", "b"]

    col["another key"] = 3
    assert col._ipython_key_completions_() == ["a", "b", "another key"]
