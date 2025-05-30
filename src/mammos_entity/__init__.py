"""Create quantity (a value and a unit) linked to MaMMoS ontology.

Exposes the primary components of the MaMMoS entity package, including
the `Entity` class for ontology-linked physical quantities, pre-defined
factory methods for common magnetic entities (Ms, A, Ku, H), and the
loaded MaMMoS ontology object.
"""

from mammos_entity._base import Entity
from mammos_entity._entities import A, BHmax, H, Hc, Ku, Mr, Ms, Tc
from mammos_entity._onto import mammos_ontology

__all__ = ["Entity", "A", "H", "Ku", "Ms", "Tc", "Hc", "Mr", "BHmax", "mammos_ontology"]
