"""
Package: mammos_entity

Exposes the primary components of the MaMMoS entity package, including
the `Entity` class for ontology-linked physical quantities, pre-defined
factory methods for common magnetic entities (Ms, A, Ku, H), and the
loaded MaMMoS ontology object.
"""

from mammos_entity.base import Entity
from mammos_entity.entities import A, H, Ku, Ms
from mammos_entity.onto import mammos_ontology
