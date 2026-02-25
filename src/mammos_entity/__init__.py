"""Entity (Quantity and EMMO ontology label).

Exposes the primary components of the MaMMoS entity package, including
the `Entity` class for ontology-linked physical quantities, pre-defined
factory methods for common magnetic entities (Ms, A, Ku, H), and the
loaded MaMMoS ontology object.
"""

import importlib.metadata

import mammos_units as units

from mammos_entity._decorators import convert_entity_likes
from mammos_entity._entity import Entity
from mammos_entity._entity_collection import EntityCollection
from mammos_entity._factory import (
    K1,
    K2,
    A,
    B,
    BHmax,
    H,
    Hc,
    J,
    Js,
    Ku,
    M,
    Mr,
    Ms,
    T,
    Tc,
)
from mammos_entity._ontology import mammos_ontology, search_labels
from mammos_entity._read_files import from_csv, from_hdf5, from_yaml

from . import operations, typing

__version__ = importlib.metadata.version(__package__)


__all__ = [
    "Entity",
    "EntityCollection",
    "convert_entity_likes",
    "A",
    "B",
    "BHmax",
    "H",
    "Hc",
    "J",
    "Js",
    "K1",
    "K2",
    "Ku",
    "M",
    "Mr",
    "Ms",
    "T",
    "Tc",
    "mammos_ontology",
    "operations",
    "typing",
    "search_labels",
    "units",
    "from_csv",
    "from_hdf5",
    "from_yaml",
]
