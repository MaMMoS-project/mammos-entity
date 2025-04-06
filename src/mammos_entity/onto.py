"""
Module: onto.py

Loads and provides access to the MaMMoS magnetic materials ontology via the
`EMMOntoPy` library. The ontology is loaded from a remote TTL (Turtle) file
containing definitions of relevant magnetic material concepts.
"""

from ontopy import ontology

mammos_ontology = ontology.get_ontology(
    "https://raw.githubusercontent.com/MaMMoS-project/MagneticMaterialsOntology/refs/heads/main/magnetic_material_mammos.ttl"
).load()
