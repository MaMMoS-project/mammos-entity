"""Entity (Quantity and EMMO ontology label).

Exposes the primary components of the MaMMoS entity package, including
the `Entity` class for ontology-linked physical quantities, pre-defined
factory methods for common magnetic entities (Ms, A, Ku, H), and the
loaded MaMMoS ontology object.
"""

import importlib.metadata

from mammos_entity._base import Entity
from mammos_entity._entities import A, B, BHmax, H, Hc, Ku, M, Mr, Ms, T, Tc
from mammos_entity._onto import mammos_ontology

__version__ = importlib.metadata.version(__package__)


__all__ = [
    "Entity",
    "A",
    "B",
    "BHmax",
    "H",
    "Hc",
    "Ku",
    "M",
    "Mr",
    "Ms",
    "T",
    "Tc",
    "mammos_ontology",
]
