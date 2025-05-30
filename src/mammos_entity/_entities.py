"""Convenience factory functions for often used entities.

Provides convenience factory functions for creating common physical property
entities (such as spontaneous magnetization or external magnetic field)
using the `Entity` class from `mammos_entity.base`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import typing

from mammos_entity._base import Entity

if TYPE_CHECKING:
    import mammos_entity


def Ms(
    value: int | float | typing.ArrayLike = 0, unit: None | str = None
) -> mammos_entity.Entity:
    """Create an Entity representing the spontaneous magnetization (Ms).

    Args:
        value: Numeric value corresponding to spontaneous magnetization. It can also be
            a Numpy array.
        unit: Unit of measure for the value (e.g., 'A/m'). If omitted, the SI unit
            from the ontology, i.e. A/m, will be inferred.

    Returns:
        An `Entity` object labelled "SpontaneousMagnetization".

    """
    return Entity("SpontaneousMagnetization", value, unit)


def A(
    value: int | float | typing.ArrayLike = 0, unit: None | str = None
) -> mammos_entity.Entity:
    """Create an Entity representing the exchange stiffness constant (A).

    Args:
        value: Numeric value corresponding to exchange stiffness. It can also be a
            Numpy array.
        unit: Unit of measure for the value (e.g., 'J/m'). If omitted, the SI unit
            from the ontology, i.e. J/m, will be inferred.

    Returns:
        An `Entity` object labeled "ExchangeStiffnessConstant".

    """
    return Entity("ExchangeStiffnessConstant", value, unit)


def Ku(
    value: int | float | typing.ArrayLike = 0, unit: None | str = None
) -> mammos_entity.Entity:
    """Create an Entity representing the uniaxial anisotropy constant (Ku).

    Args:
        value: Numeric value corresponding to the uniaxial anisotropy constant. It can
            also be a Numpy array.
        unit: Unit of measure for the value (e.g., 'J/m^3'). If omitted, the SI unit
            from the ontology, i.e. J/m^3 will be inferred.

    Returns:
        An `Entity` object labeled "UniaxialAnisotropyConstant".

    """
    return Entity("UniaxialAnisotropyConstant", value, unit)


def H(
    value: int | float | typing.ArrayLike = 0, unit: None | str = None
) -> mammos_entity.Entity:
    """Create an Entity representing the external magnetic field (H).

    Args:
        value: Numeric value corresponding to the external magnetic field. It can also
            be a Numpy array.
        unit: Unit of measure for the value (e.g., 'T' for Tesla). If omitted, the SI
            unit from the ontology, i.e. T, will be inferred.

    Returns:
        Entity: An `Entity` object labeled "ExternalMagneticField".


    """
    return Entity("ExternalMagneticField", value, unit)


def Tc(
    value: int | float | typing.ArrayLike = 0, unit: None | str = None
) -> mammos_entity.Entity:
    """Create an Entity representing the Curie temperature (Tc).

    Args:
        value: Numeric value corresponding to the Curie temperature. It can also be a
            Numpy array.
        unit : Unit of measure for the value (e.g., 'K' for Kelvin). If omitted, the SI
            unit from the ontology, i.e. K, will be inferred.

    Returns:
        An `Entity` object labelled "CurieTemperature".

    """
    return Entity("CurieTemperature", value, unit)


def Hc(
    value: int | float | typing.ArrayLike = 0, unit: None | str = None
) -> mammos_entity.Entity:
    """Create an Entity representing the external coercive field (Hc).

    Args:
        value : Numeric value corresponding to the external coercive field. It can also
            be a Numpy array.
        unit : Unit of measure for the value (e.g., 'A/m'). If omitted, the SI unit
            from the ontology, i.e. A/m, will be inferred.

    Returns:
        Entity: An `Entity` object labelled "CoercivityHcExternal".

    """
    return Entity("CoercivityHcExternal", value, unit)


def Mr(
    value: int | float | typing.ArrayLike = 0, unit: None | str = None
) -> mammos_entity.Entity:
    """Create an Entity representing the remanent magnetisation (Mr).

    Args:
        value : Numeric value corresponding to the remanent magnetisation. It can also
            be a Numpy array.
        unit : Unit of measure for the value (e.g., 'A/m'). If omitted, the SI unit
            from the ontology, i.e. A/m, will be inferred.

    Returns:
        An `Entity` object labelled "Remanence".

    """
    return Entity("Remanence", value, unit)


def BHmax(
    value: int | float | typing.ArrayLike = 0, unit: None | str = None
) -> mammos_entity.Entity:
    """Create an Entity representing the maximum energy product of the hysteresis loop.

    Args:
        value : Numeric value corresponding to the maximum energy product. It can also
            be a Numpy array.
        unit : Unit of measure for the value (e.g., 'J/m3'). If omitted, the SI unit
            from the ontology, i.e. J/m3, will be inferred.

    Returns:
        An `Entity` object labelled "MaximumEnergyProduct".

    """
    return Entity("MaximumEnergyProduct", value, unit)
