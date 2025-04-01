"""
This package (`mammos_entity`) provides classes representing physical entities
representing magnetic material properties (like Mₛ, A, Kᵤ, and H) along with their
links to a magnetic materials ontology.
"""

from mammos_entity.base import Entity
from mammos_entity.entities import A, H, Ku, Ms
from mammos_entity.onto import mammos_ontology
