import html
import math
import re

import astropy
import mammos_units as u
import numpy as np
import pytest
from numpy import array  # noqa: F401  # required for repr eval

import mammos_entity as me
from mammos_entity import Entity  # noqa: F401  # required for repr eval
from mammos_entity._repr import _repr_css


def _strip_html_event_handlers(fragment: str) -> str:
    """Normalize inline event handlers in HTML repr snapshots."""
    return re.sub(r'(onclick|onkeydown)="[^"]*"', r'\1="..."', fragment)


def test_init_float():
    """Initialize Entity instance with a float."""
    e = me.Entity("ExternalMagneticField", value=8e5)
    q = 8e5 * u.A / u.m
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 8e5)
    assert e.unit == u.A / u.m
    assert e.ontology_label == "ExternalMagneticField"


def test_init_list():
    """Initialize with Python lists."""
    val = [42, 42, 42]
    e = me.Entity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, val)
    val[0] = 1
    assert np.allclose(e.value, [42, 42, 42])


def test_init_tuple():
    """Initialize with Python tuples."""
    val = (42, 42, 42)
    e = me.Entity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, np.array(val))


def test_init_numpy():
    """Initialize with NumPy array."""
    val = np.array([42, 42, 42])
    e = me.Entity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, val)
    val[0] = 1
    assert np.allclose(e.value, [42, 42, 42])
    val = np.ones((42, 42, 42, 3))
    e = me.Entity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, val)


def test_init_quantity():
    """Initialize using mammos_units.Quantity.

    Test 1: an entity created from a quantity without specifying unit
    will take value and unit from the quantity. In this case the unit
    of the quantity is the default ontology quantity.
    Test 2: an entity created from a quantity specifying the unit
    will convert the quantity to the selected unit. In this case
    the unit is the same of the quantity, so there is actually no
    conversion involved.
    Test 3: Same as Test 1, but this time the unit of the quantity
    is not the default ontology quantity.
    Test 4: Same as Test 2, but there is an actually conversion involved.
    """
    q = 1 * u.A / u.m
    e = me.Entity("ExternalMagneticField", value=q)
    assert e.ontology_label == "ExternalMagneticField"
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.A / u.m
    q = 1 * u.kA / u.m
    e = me.Entity("ExternalMagneticField", value=q, unit="kA/m")
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.kA / u.m
    e = me.Entity("ExternalMagneticField", value=q)
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.kA / u.m
    e = me.Entity("ExternalMagneticField", value=q, unit="MA/m")
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1e-3)
    assert e.unit == u.MA / u.m


def test_init_entity():
    """Initialize from another Entity.

    Test 1: an Entity initialized from another Entity will define
    its Quantity (including unit) from it.
    Test 2: if we select a different unit, it gets converted.
    Test 3: if we initialize using an Entity with a different ontology label
    we get an error.
    """
    e_1 = me.Entity("ExternalMagneticField", value=1, unit="mA/m")
    e_2 = me.Entity("ExternalMagneticField", value=e_1)
    assert e_2.ontology_label == "ExternalMagneticField"
    assert u.allclose(e_1.quantity, e_2.quantity)
    assert np.allclose(e_1.value, e_2.value)
    assert e_1.unit == e_2.unit
    e_3 = me.Entity("ExternalMagneticField", value=e_1, unit="A/m")
    assert u.allclose(e_3.quantity, e_1.quantity)
    assert np.allclose(e_3.value, 1e-3)
    assert e_3.unit == u.A / u.m
    with pytest.raises(ValueError):
        me.Entity("CurieTemperature", value=e_1)


def test_unitless():
    """Test unitless Entity."""
    e_1 = me.Entity("DemagnetizingFactor", 0.3)
    assert e_1.ontology_label == "DemagnetizingFactor"
    assert math.isclose(e_1.value, 0.3)
    assert e_1.unit.is_equivalent("")
    e_2 = me.Entity("DemagnetizingFactor", [1, 2])
    assert np.allclose(e_2.value, [1, 2])
    assert e_2.unit.is_equivalent("")
    e_3 = me.Entity("DemagnetizingFactor", u.Quantity(0.3))
    assert math.isclose(e_3.value, 0.3)
    assert e_3.unit.is_equivalent("")
    e_4 = me.Entity("DemagnetizingFactor", e_3)
    assert math.isclose(e_4.value, 0.3)
    assert e_4.unit.is_equivalent("")


def test_check_units():
    """Test units of Entity.

    Test 1: Check that unit is immutable.
    Test 2: Check that Entity cannot be initialized with wrong unit.
    Even if we activate the necessary conversion equivalency, the initialization
    should reset all equivalencies.
    """
    # change unit (conversion/change unit after initialized entity)
    e = me.Entity("SpontaneousMagnetization", value=1, unit=u.A / u.m)
    e.quantity.to("kA/m")
    assert e.unit == u.A / u.m
    e.quantity.to("kA/m", copy=False)
    assert e.unit == u.A / u.m
    with pytest.raises(ValueError, match="incompatible with ontology. Allowed units"):
        me.Entity("SpontaneousMagnetization", value=1, unit="T")
    with (
        u.set_enabled_equivalencies(u.magnetic_flux_field()),
        pytest.raises(ValueError, match="incompatible with ontology. Allowed units"),
    ):
        me.Entity("SpontaneousMagnetization", value=1, unit="T")
    with (
        u.set_enabled_equivalencies(u.magnetic_flux_field()),
        pytest.raises(astropy.units.UnitConversionError),
    ):
        me.Entity("SpontaneousMagnetization", value=1 * u.T, unit="A/m")


def test_repr():
    """Test representation string.

    Test 1: Test repr for scalar value.
    Test 2: Test repr for vectorial value.
    Test 3: Test repr for unitless Entity.

    Note that the representation of floats will be slightly different for NumPy 1
    and for NumPy 2. In particular `zero_string` = `'0.0'` for NumPy 1,
    and = `'np.float64(0.0)'` for NumPy 2.
    """
    e = me.Entity("CurieTemperature")
    zero_string = f"{np.float64(0.0)!r}"  # differs for NumPy 1 and NumPy 2.
    assert e.__repr__() == f"Entity(ontology_label='CurieTemperature', value={zero_string}, unit='K')"
    assert eval(repr(e)) == e

    a = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    e = me.Entity("ExternalMagneticField", value=a)
    assert e.__repr__() == (
        "Entity(ontology_label='ExternalMagneticField', " + f"value={np.array(a, dtype=float)!r}, unit='A / m')"
    )
    assert eval(repr(e)) == e

    e = me.Entity("DemagnetizingFactor")
    assert e.__repr__() == f"Entity(ontology_label='DemagnetizingFactor', value={zero_string})"
    assert eval(repr(e)) == e


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
        "&nbsp;<span class='entity-meta'>·&nbsp;shape=(2,&nbsp;2)</span>"
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
    assert (
        me._entity._array_repr_expanded_edgeitems(np.arange(400).reshape(20, 20)) == 5
    )
    assert (
        me._entity._array_repr_expanded_edgeitems(
            np.arange(10 * 500 * 20).reshape(10, 500, 20)
        )
        == 2
    )


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
        "const root = this.closest('.mammos-entity-inline-v2');"
        "if (!root) return;"
        "root.dataset.expanded = 'true';"
    )
    assert me.Entity._repr_html_toggle_script(expanded=False) == (
        "const root = this.closest('.mammos-entity-inline-v2');"
        "if (!root) return;"
        "root.dataset.expanded = 'false';"
    )


def test_repr_html_long_value_exact_snapshot():
    """Freeze the long-value HTML structure while ignoring JS formatting details."""
    e = me.Entity("ExternalMagneticField", np.arange(24).reshape(4, 6), "A/m")

    fragment = _strip_html_event_handlers(e._repr_html_fragment_())
    expanded_html = html.escape(me._entity._format_array_repr_expanded(e.value))

    assert fragment == (
        "<samp class='mammos-entity-inline-v2' data-expanded='false'>"
        "<span class='entity-label'>ExternalMagneticField</span>"
        "&nbsp;<span class='entity-meta'>·&nbsp;shape=(4,&nbsp;6)</span>"
        "<br>"
        "<span class='entity-collapsed entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Expand value' "
        'onclick="..." onkeydown="...">[+]</span>'
        "<span class='entity-summary-preview'>"
        "0.&nbsp;1.&nbsp;2.&nbsp;...&nbsp;21.&nbsp;22.&nbsp;23."
        "</span><span>&nbsp;A&nbsp;/&nbsp;m</span>"
        "</span>"
        "<span class='entity-expanded entity-summary'>"
        "<span role='button' tabindex='0' class='entity-toggle' "
        "aria-label='Collapse value' "
        'onclick="..." onkeydown="...">[−]</span>'
        "<span class='entity-summary-preview'>"
        "0.&nbsp;1.&nbsp;2.&nbsp;...&nbsp;21.&nbsp;22.&nbsp;23."
        "</span><span>&nbsp;A&nbsp;/&nbsp;m</span>"
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

    assert "class='entity-meta'>·&nbsp;shape=(1001,)</span>" in fragment
    assert (
        "<span class='entity-summary-preview'>"
        "0.&nbsp;1.&nbsp;2.&nbsp;...&nbsp;998.&nbsp;999.&nbsp;1000."
        "</span><span>&nbsp;A&nbsp;/&nbsp;m</span>"
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


def test_axis_labels():
    """Test different axis_label examples."""
    e_1 = me.Entity("ExternalMagneticField")
    assert e_1.axis_label == "External Magnetic Field (A / m)"
    e_2 = me.Entity("AffinityOfAChemicalReaction")
    assert e_2.axis_label == "Affinity Of A Chemical Reaction (J / mol)"
    e_3 = me.Entity("DemagnetizingFactor")
    assert e_3.axis_label == "Demagnetizing Factor"
    e_4 = me.Entity("Entropy")
    assert e_4.axis_label == "Entropy (J / K)"
    e_5 = me.Entity("PlanckConstant")
    assert e_5.axis_label == "Planck Constant (J s)"


@pytest.mark.parametrize("ontology_element", me.mammos_ontology.classes(imported=True))
def test_all_labels_ontology(ontology_element):
    """Test all labels in the ontology.

    This test creates one Entity instance for each label in the ontology.

    Entities `Person` and `Organization` do not have a `prefLabel`.
    These are extreme, unfixable cases and we ignore them.
    """
    if ontology_element.prefLabel:
        prefLabel = str(ontology_element.prefLabel[0])
        if prefLabel in [
            "Electron",
            "ElementaryCharge",
            "Grain",
            "Point",
            "RelativePermeability",
            "RelativePermittivity",
        ]:
            pytest.xfail(f"{prefLabel=} is ambiguous")
        me.Entity(prefLabel, 42)


def test_default_unit():
    """Test default unit for different entities."""
    assert me.Entity("MaximumEnergyProduct").unit == u.J / u.m**3
    assert me.Entity("SpontaneousMagneticPolarisation").unit == u.T


def test_label_without_concrete_units():
    """Test the ontology entries without concrete units.

    This test checks that entries with an abstract unit but no concrete units (i.e. the
    subclasses of abstract units) are initialized with units given from their dimension
    strings.

    For example, ``MagneticMoment`` has the abstract unit ``ElectricCurrentAreaUnit``.
    This abstract unit is not tied to any concrete unit, i.e. it has no subclasses.
    However, it has the attribute ``hasDimensionString`` is equal to
    ``'T0 L+2 M0 I+1 Θ0 N0 J0'`` and we read this instead.
    """
    assert me.Entity("MagneticMoment").unit == u.A * u.m**2
    assert me.Entity("DiffusionCoefficient").unit == u.m**2 / u.s
    assert me.Entity("DiffusionCoefficientForParticleNumberDensity").unit == u.m**2 / u.s
    assert me.Entity("EffectiveDiffusionCoefficient").unit == u.m**2 / u.s
    assert me.Entity("ElectricDipoleMoment").unit == u.A * u.m * u.s
    assert me.Entity("EnergyDensityOfStates").unit == u.s**2 / u.m**5 / u.kg
    assert me.Entity("JouleThomsonCoefficient").unit == u.K * u.s**2 * u.m / u.kg
    assert me.Entity("LorenzCoefficient").unit == u.m**4 * u.kg**2 / u.A**2 / u.s**6
    assert me.Entity("MagneticMomentPerUnitMass").unit == u.m**2 * u.A / u.kg
    assert me.Entity("Mobility").unit == u.A * u.s**2 / u.kg


def test_switch_to_pref_label():
    """Test the switch to prefLabel instead of given one."""
    assert me.Entity("Ms").ontology_label == "SpontaneousMagnetization"
    assert me.Entity("K1").ontology_label == "MagnetocrystallineAnisotropyConstantK1"
    assert me.Entity("A").ontology_label == "ExchangeStiffnessConstant"
    assert me.Entity("Js").ontology_label == "SpontaneousMagneticPolarization"


def test_ontology_information_mammos():
    """Test ontology label and IRI for an Entity in the MaMMoS ontology."""
    e = me.Entity("ExternalMagneticField")
    assert e.ontology_label == "ExternalMagneticField"
    assert e.ontology_iri == "https://w3id.org/emmo/domain/magnetic-materials#EMMO_da08f0d3-fe19-58bc-8fb6-ecc8992d5eb3"
    assert (
        e.ontology_label_with_iri
        == "ExternalMagneticField https://w3id.org/emmo/domain/magnetic-materials#EMMO_da08f0d3-fe19-58bc-8fb6-ecc8992d5eb3"
    )
    assert e.ontology_label_with_iri == f"{e.ontology.prefLabel[0]} {e.ontology.iri}"
    assert e.ontology_label in me.mammos_ontology
    H = me.mammos_ontology.get_by_label(e.ontology_label)
    assert e.ontology_label_with_iri == f"{H.prefLabel[0]} {H.iri}"


def test_ontology_information_EMMO():
    """Test ontology label and IRI for an Entity in the EMMO."""
    e = me.Entity("AngularVelocity")
    assert e.ontology_label == "AngularVelocity"
    assert e.ontology_iri == "https://w3id.org/emmo#EMMO_bd325ef5_4127_420c_83d3_207b3e2184fd"
    assert (
        e.ontology_label_with_iri == "AngularVelocity https://w3id.org/emmo#EMMO_bd325ef5_4127_420c_83d3_207b3e2184fd"
    )
    assert e.ontology_label_with_iri == f"{e.ontology.prefLabel[0]} {e.ontology.iri}"
    assert e.ontology_label in me.mammos_ontology
    omega = me.mammos_ontology.get_by_label(e.ontology_label)
    assert e.ontology_label_with_iri == f"{omega.prefLabel[0]} {omega.iri}"


def test_equality():
    """Test equality.

    We expect two entities to be equal if the ontology_label is the same
    and the values are close enough.
    Equality fails when the right hand term is not an Entity.
    """
    e_1 = me.Entity("SpontaneousMagnetization", value=1)
    e_2 = me.Entity("SpontaneousMagnetization", value=1)
    assert e_1 == e_2
    e_3 = me.Entity("SpontaneousMagnetization", value=2)
    assert e_1 != e_3
    e_4 = me.Entity("ExternalMagneticField", value=1)
    assert e_1 != e_4
    e_5 = me.Entity("SpontaneousMagnetization", value=1000, unit=u.mA / u.m)
    assert e_1 == e_5
    e_6 = me.Entity("SpontaneousMagnetization", value=[[1, 1]])
    assert e_1 != e_6
    e_7 = me.Entity("SpontaneousMagnetization", value=[[1], [1]])
    assert e_6 != e_7

    # Other objects
    assert e_1 != 1 * u.A / u.m
    assert e_1 != 1
    assert e_1 != e_2.quantity

    # Other objects can implement __eq__ in a way that is compatible with Entity

    class A:
        def __eq__(self, o):
            return True

    assert e_1 == A()


@pytest.mark.parametrize(
    "function, expected_label",
    (
        (me.A, "ExchangeStiffnessConstant"),
        (me.BHmax, "MaximumEnergyProduct"),
        (me.B, "MagneticFluxDensity"),
        (me.H, "ExternalMagneticField"),
        (me.Hc, "CoercivityHcExternal"),
        (me.J, "MagneticPolarisation"),
        (me.Js, "SpontaneousMagneticPolarization"),
        (me.K1, "MagnetocrystallineAnisotropyConstantK1"),
        (me.K2, "MagnetocrystallineAnisotropyConstantK2"),
        (me.Ku, "UniaxialAnisotropyConstant"),
        (me.M, "Magnetization"),
        (me.Mr, "Remanence"),
        (me.Ms, "SpontaneousMagnetization"),
        (me.T, "ThermodynamicTemperature"),
        (me.Tc, "CurieTemperature"),
    ),
)
def test_known_labels(function, expected_label):
    """Check predefined entities."""
    assert function().ontology_label == expected_label


def test_bad_description():
    """Check bad type for description."""
    with pytest.raises(ValueError):
        me.Ms(1, description=1)


@pytest.mark.parametrize(
    "value, expected_value, expected_unit",
    [
        (me.Entity("ThermodynamicTemperature", 300.0 * u.K), 300.0, u.K),
        (300.0 * u.K, 300.0, u.K),
        (300.0, 300.0, u.deg_C),
        (
            me.Entity("ThermodynamicTemperature", [100.0, 200.0, 300.0] * u.K),
            [100.0, 200.0, 300.0],
            u.K,
        ),
        ([100.0, 200.0, 300.0] * u.K, [100.0, 200.0, 300.0], u.K),
        ([100.0, 200.0, 300.0], [100.0, 200.0, 300.0], u.deg_C),
    ],
)
def test_from_compatible(value, expected_value, expected_unit):
    """Test from_compatible with valid inputs."""
    out = me._entity.from_compatible(
        "ThermodynamicTemperature",
        "deg_C",
        temperature=value,
    )
    assert out.ontology_label == "ThermodynamicTemperature"
    assert np.allclose(out.value, expected_value)
    assert out.unit == expected_unit


@pytest.mark.parametrize(
    "value",
    [
        me.Entity("CurieTemperature", 300.0 * u.K),
        me.Entity("NeelTemperature", 300.0 * u.K),
        me.Entity("ThermodynamicTemperature", 300.0 * u.K),
        300.0 * u.K,
        300.0,
    ],
)
def test_from_compatible_compatible_entity(value):
    """Test from_compatible with a compatible entity."""
    out = me._entity.from_compatible(
        "ThermodynamicTemperature",
        "K",
        compatible_entities=("CurieTemperature", "NeelTemperature"),
        temperature=value,
    )
    assert out.ontology_label == "ThermodynamicTemperature"
    assert np.allclose(out.value, 300.0)
    assert out.unit == u.K


def test_from_compatible_enforce_unit():
    """Test from_compatible with enforce_unit=True."""
    out = me._entity.from_compatible(
        "ThermodynamicTemperature",
        "deg_C",
        enforce_unit=True,
        temperature=300 * u.K,
    )
    assert out.ontology_label == "ThermodynamicTemperature"
    assert np.allclose(out.value, 26.85)
    assert out.unit == u.deg_C


@pytest.mark.parametrize(
    "value, expected_error",
    [
        (me.Entity("ExternalMagneticField", 1), ValueError),
        (1 * u.m, ValueError),
        ("String", TypeError),
        ([1, 2, "String"], TypeError),
        (
            [
                me.Entity("ThermodynamicTemperature", [100.0] * u.K),
                me.Entity("ThermodynamicTemperature", [200.0] * u.K),
                me.Entity("ThermodynamicTemperature", [300.0] * u.K),
            ],
            TypeError,
        ),
    ],
)
def test_from_compatible_errors(value, expected_error):
    """Test from_compatible raises on incompatible inputs."""
    with pytest.raises(expected_error):
        me._entity.from_compatible(
            "ThermodynamicTemperature",
            "deg_C",
            temperature=value,
        )


def test_from_compatible_wrong_kwarg():
    """Test from_compatible raises with wrong number of kwargs."""
    with pytest.raises(RuntimeError):
        me._entity.from_compatible("ThermodynamicTemperature", "deg_C")

    with pytest.raises(RuntimeError):
        me._entity.from_compatible(
            "ThermodynamicTemperature",
            "deg_C",
            temperature=5,
            tc=5,
        )
