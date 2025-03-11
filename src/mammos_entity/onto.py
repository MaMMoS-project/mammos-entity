"""
This module defines the `mammos_ontology`, which loads a magnetic materials ontology
from a remote mammos ontology TTL (Turtle) file. The ontology is used by entities to map
their properties to semantic concepts.
"""

from ontopy import ontology

mammos_ontology = ontology.get_ontology(
    "https://raw.githubusercontent.com/MaMMoS-project/MagneticMaterialsOntology/refs/heads/main/magnetic_material_mammos.ttl"
).load()
