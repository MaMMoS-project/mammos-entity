"""Test plotting submodule."""

import mammos_units as u
import numpy as np
import pytest
from matplotlib.units import ConversionError

import mammos_entity as me
import mammos_entity.pyplot as plt


@pytest.mark.parametrize(
    "x,y_1,y_2,expected_xlabel,expected_ylabel,expected_unit",
    [
        (
            # We expect that the second entity converts to the unit of the first
            me.Entity("ThermodynamicTemperature", [10, 20, 30], "K"),
            me.Entity("Magnetization", [300, 200, 100], "kA/m"),
            me.Entity("Magnetization", [0.4, 0.35, 0.3], "MA/m"),
            r"ThermodynamicTemperature ($\mathrm{K}$)",
            r"Magnetization ($\mathrm{kA\,m^{-1}}$)",
            "kA/m",
        ),
        (
            # Similar to first test but inverted order
            me.Entity("ThermodynamicTemperature", [10, 20, 30], "K"),
            me.Entity("Magnetization", [0.4, 0.35, 0.3], "MA/m"),
            me.Entity("Magnetization", [300, 200, 100], "kA/m"),
            r"ThermodynamicTemperature ($\mathrm{K}$)",
            r"Magnetization ($\mathrm{MA\,m^{-1}}$)",
            "MA/m",
        ),
        (
            # Dimensionless quantities
            me.Entity("ThermodynamicTemperature", [10, 20, 30], "K"),
            me.Entity("DemagnetizingFactor", [1 / 3, 1 / 3, 1 / 3]),
            me.Entity("DemagnetizingFactor", [1 / 400, 1 / 400, 1 / 400], "1e2"),
            r"ThermodynamicTemperature ($\mathrm{K}$)",
            r"DemagnetizingFactor",
            "",
        ),
        (
            # Dimensionless quantities always get unscaled
            me.Entity("ThermodynamicTemperature", [10, 20, 30], "K"),
            me.Entity("DemagnetizingFactor", [1 / 400, 1 / 400, 1 / 400], "1e2"),
            me.Entity("DemagnetizingFactor", [1 / 3, 1 / 3, 1 / 3]),
            r"ThermodynamicTemperature ($\mathrm{K}$)",
            r"DemagnetizingFactor",
            "",
        ),
    ],
)
def test_plot_conversion(x, y_1, y_2, expected_xlabel, expected_ylabel, expected_unit):
    fig, ax = plt.subplots()
    ax.plot(x, y_1)
    ax.plot(x, y_2)
    assert len(ax.lines) == 2
    # Test that the lines contain the data we defined
    assert ax.lines[0].get_xdata().item() == x
    assert ax.lines[0].get_ydata().item() == y_1
    assert ax.lines[1].get_xdata().item() == x
    assert ax.lines[1].get_ydata().item() == y_2
    # Test the axes labels
    assert ax.get_xlabel() == expected_xlabel
    assert ax.get_ylabel() == expected_ylabel
    # Test that conversion would work as expected
    np.testing.assert_allclose(ax.convert_yunits(ax.lines[0].get_ydata()), y_1.q.to(expected_unit).value)
    np.testing.assert_allclose(ax.convert_yunits(ax.lines[1].get_ydata()), y_2.q.to(expected_unit).value)


@pytest.mark.parametrize(
    "x_1,x_2,y_1,y_2,expected_xlabel,expected_ylabel,expected_unit",
    [
        (
            # Entity and Quantity
            me.Entity("ThermodynamicTemperature", [10, 20, 30], "K"),
            [10, 20, 30] * u.K,
            me.Entity("Magnetization", [300, 200, 100], "kA/m"),
            [0.4, 0.35, 0.3] * u.MA / u.m,
            r"ThermodynamicTemperature ($\mathrm{K}$)",
            r"Magnetization ($\mathrm{kA\,m^{-1}}$)",
            "kA/m",
        ),
        (
            # Quantity and Entity
            [10, 20, 30] * u.K,
            me.Entity("ThermodynamicTemperature", [10, 20, 30], "K"),
            [0.4, 0.35, 0.3] * u.MA / u.m,
            me.Entity("Magnetization", [300, 200, 100], "kA/m"),
            r"($\mathrm{K}$)",
            r"($\mathrm{MA\,m^{-1}}$)",
            "MA/m",
        ),
    ],
)
def test_plot_conversion_different_type(x_1, x_2, y_1, y_2, expected_xlabel, expected_ylabel, expected_unit):
    fig, ax = plt.subplots()
    ax.plot(x_1, y_1)
    ax.plot(x_2, y_2)
    assert len(ax.lines) == 2
    # Test that the lines contain the data we defined
    # quantities appear as array data, entities appear as `array([e])`.
    assert all(ax.lines[0].get_xdata() == ([x_1] if isinstance(x_1, me.Entity) else x_1))
    assert all(ax.lines[0].get_ydata() == ([y_1] if isinstance(y_1, me.Entity) else y_1))
    assert all(ax.lines[1].get_xdata() == ([x_2] if isinstance(x_2, me.Entity) else x_2))
    assert all(ax.lines[1].get_ydata() == ([y_2] if isinstance(y_2, me.Entity) else y_2))
    # Test the axes labels
    assert ax.get_xlabel() == expected_xlabel
    assert ax.get_ylabel() == expected_ylabel
    # Test that conversion would work as expected
    converted_y_1 = y_1.q.to(expected_unit).value if isinstance(y_1, me.Entity) else y_1.to(expected_unit).value
    converted_y_2 = y_2.q.to(expected_unit).value if isinstance(y_2, me.Entity) else y_2.to(expected_unit).value
    np.testing.assert_allclose(ax.convert_yunits(ax.lines[0].get_ydata()), converted_y_1)
    np.testing.assert_allclose(ax.convert_yunits(ax.lines[1].get_ydata()), converted_y_2)


def test_plot_conversion_error():
    T = (me.Entity("ThermodynamicTemperature", [10, 20, 30], "K"),)
    M = (me.Entity("Magnetization", [0.4, 0.35, 0.3], "MA/m"),)
    B = (me.Entity("MagneticFluxDensity", [300, 200, 100], "mT"),)
    with pytest.raises(ConversionError):
        fig, ax = plt.subplots()
        ax.plot(T, M)
        ax.plot(T, B)


def test_plot_conversion_with_extra_equivalency():
    """Test plotting of non-compatible entities with enabled equivalency layer."""
    T = (me.Entity("ThermodynamicTemperature", [10, 20, 30], "K"),)
    M = (me.Entity("Magnetization", [0.4, 0.35, 0.3], "MA/m"),)
    B = (me.Entity("MagneticFluxDensity", [300, 200, 100], "mT"),)
    fig, ax = plt.subplots()
    with u.set_enabled_equivalencies(u.magnetic_flux_field()):
        ax.plot(T, M)
        ax.plot(T, B)
    assert len(ax.lines) == 2
