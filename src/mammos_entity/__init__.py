"""Entity (Quantity and EMMO ontology label).

Exposes the primary components of the MaMMoS entity package, including
the `Entity` class for ontology-linked physical quantities, pre-defined
factory methods for common magnetic entities (Ms, A, Ku, H), and the
loaded MaMMoS ontology object.
"""

import importlib.metadata

import mammos_units as units

from mammos_entity._entity import Entity
from mammos_entity._entity_collection import EntityCollection
from mammos_entity._factory import A, B, BHmax, H, Hc, J, Js, Ku, M, Mr, Ms, T, Tc
from mammos_entity._ontology import mammos_ontology

from . import io, operations

__version__ = importlib.metadata.version(__package__)


__all__ = [
    "Entity",
    "EntityCollection",
    "A",
    "B",
    "BHmax",
    "H",
    "Hc",
    "J",
    "Js",
    "Ku",
    "M",
    "Mr",
    "Ms",
    "T",
    "Tc",
    "io",
    "mammos_ontology",
    "operations",
    "units",
]
