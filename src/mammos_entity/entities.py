"""
Module: entities.py

Provides convenience factory functions for creating common physical property
entities (such as spontaneous magnetization or external magnetic field)
using the `Entity` class from `mammos_entity.base`.
"""

from numpy import typing

from mammos_entity.base import Entity


def Ms(value: int | float | typing.ArrayLike, unit: None | str = None) -> Entity:
    """
    Create an Entity representing the spontaneous magnetization (Ms).

    Parameters
    ----------
    value : float | int | typing.ArrayLike
        Numeric value corresponding to spontaneous magnetization. It can also be a Numpy
        array.
    unit : optional
        Unit of measure for the value (e.g., 'A/m'). If omitted, the SI unit
        from the ontology, i.e. A/m, will be inferred.

    Returns
    -------
    Entity
        An `Entity` object labeled "SpontaneousMagnetization".
    """
    return Entity("SpontaneousMagnetization", value, unit)


def A(value: int | float | typing.ArrayLike, unit: None | str = None) -> Entity:
    """
    Create an Entity representing the exchange stiffness constant (A).

    Parameters
    ----------
    value : float | int | typing.ArrayLike
        Numeric value corresponding to exchange stiffness. It can also be a Numpy array.
    unit : optional
        Unit of measure for the value (e.g., 'J/m'). If omitted, the SI unit
        from the ontology, i.e. J/m, will be inferred.

    Returns
    -------
    Entity
        An `Entity` object labeled "ExchangeStiffnessConstant".
    """
    return Entity("ExchangeStiffnessConstant", value, unit)


def Ku(value: int | float | typing.ArrayLike, unit: None | str = None) -> Entity:
    """
    Create an Entity representing the uniaxial anisotropy constant (Ku).

    Parameters
    ----------
    value : float | int | typing.ArrayLike
        Numeric value corresponding to the uniaxial anisotropy constant. It can also be
        a Numpy array.
    unit : optional
        Unit of measure for the value (e.g., 'J/m^3'). If omitted, the SI unit
        from the ontology, i.e. J/m^3 will be inferred.

    Returns
    -------
    Entity
        An `Entity` object labeled "UniaxialAnisotropyConstant".
    """
    return Entity("UniaxialAnisotropyConstant", value, unit)


def H(value: int | float | typing.ArrayLike, unit: None | str = None):
    """
    Create an Entity representing the external magnetic field (H).

    Parameters
    ----------
    value : float | int | typing.ArrayLike
        Numeric value corresponding to the external magnetic field. It can also be a
        Numpy array.
    unit : optional
        Unit of measure for the value (e.g., 'T' for Tesla). If omitted, the SI unit
        from the ontology, i.e. T, will be inferred.

    Returns
    -------
    Entity
        An `Entity` object labeled "ExternalMagneticField".
    """
    return Entity("ExternalMagneticField", value, unit)
