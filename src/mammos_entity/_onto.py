"""Loads and provides access to MaMMoS ontology which is part of EMMO.

Loads and provides access to the MaMMoS magnetic materials ontology via the
`EMMOntoPy` library. The ontology is loaded from a TTL (Turtle) file distributed
with the mammos_entity.
"""

from pathlib import Path

from ontopy import ontology

HAVE_INTERNET = True

mammos_ontology = ontology.get_ontology(
    (Path(__file__).parent / "ontology" / "mammos-ontology.ttl").resolve().as_uri()
).load()
