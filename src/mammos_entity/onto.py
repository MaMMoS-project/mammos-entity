"""
Module: onto.py

Loads and provides access to the MaMMoS magnetic materials ontology via the
`EMMOntoPy` library. The ontology is loaded from a remote TTL (Turtle) file
containing definitions of relevant magnetic material concepts.
"""

import warnings

from ontopy import ontology, utils

HAVE_INTERNET = False

try:
    mammos_ontology = ontology.get_ontology(
        "https://raw.githubusercontent.com/MaMMoS-project/MagneticMaterialsOntology/refs/heads/main/magnetic_material_mammos.ttl"
    ).load()
except utils.EMMOntoPyException:
    warnings.warn(
        message="Failed to load ontology from the internet.",
        category=RuntimeWarning,
        stacklevel=2,
    )
    mammos_ontology = None
    HAVE_INTERNET = False
