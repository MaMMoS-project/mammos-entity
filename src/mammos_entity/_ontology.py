"""Loads and provides access to MaMMoS ontology which is part of EMMO.

Loads and provides access to the MaMMoS magnetic materials ontology, including
everything from the EMMO ontology, via the `EMMOntoPy` library. The ontology is loaded
from ``.ttl`` (Turtle) files distributed with mammos-entity.
"""

from logging import getLogger
from pathlib import Path

import ontopy

logger = getLogger(__name__)


def load_offline_ontology() -> ontopy.ontology.Ontology:
    """Load EMMO and MaMMoS ontology from 'ontology' directory.

    The returned ontology object contains all definitions from both ontologies, EMMO is
    in the attribute `.imported_ontologies` and accessible in other methods when using
    ``imported=True``.

    """
    w = ontopy.World()
    ontology_dir = (Path(__file__).parent / "ontology").resolve()
    # load EMMO
    # using pathlib.Path(...).as_uri() causes ontopy to fail on Windows, therefore
    # we construct the file uri manually in the form required for ontopy
    emmo_ttl = f"file://{ontology_dir / 'emmo.ttl'!s}"
    logger.debug("loading emmo ttl from '%s'", emmo_ttl)
    w.get_ontology(emmo_ttl).load()
    # now load MaMMoS ontology, which builds upon EMMO; with EMMO already loaded
    # no internet access is required to resolve 'owl:imports <https://w3id.org/emmo'
    mammos_ttl = f"file://{ontology_dir / 'magnetic_material_mammos.ttl'!s}"
    logger.debug("loading mammos ttl from '%s'", mammos_ttl)
    mammos_ontology = w.get_ontology(mammos_ttl).load()
    return mammos_ontology


def load_online_ontology() -> ontopy.ontology.Ontology:
    """Fetch EMMO and MaMMoS ontology from the internet."""
    # We need to only load the MaMMoS ontology explicitly. Ontopy will automatically
    # fetch EMMO as dependency of the MaMMoS ontology.
    return ontopy.ontology.get_ontology(
        "https://raw.githubusercontent.com/MaMMoS-project/MagneticMaterialsOntology/refs/heads/main/magnetic_material_mammos.ttl"
    ).load()


mammos_ontology = load_offline_ontology()


def search_labels(text: str, auto_wildcard: bool = True) -> list[str]:
    """Search entity labels by name.

    The string ``text`` is searched into ``label``, ``prefLabel``, and ``altLabel`` of
    all entities. The match is case sensitive. The returned label is always the
    ``prefLabel``.

    Args:
        text: String to match.
        auto_wildcard: If True, the wildcard ``*`` is added at the beginning
            and at the end of the string ``text``. This allows partial matches, finding
            labels containing ``text``. If False, only labels identical to ``text``
            are returned.

            Passing ``"text", auto_wildcard=True`` is identical to passing
            ``"*text*", auto_wildcard=False``.

    Examples:
        >>> import mammos_entity as me
        >>> me.search_labels("ShapeAnisotropy")
        ['ShapeAnisotropy', 'ShapeAnisotropyConstant']

        >>> me.search_labels("Magnetization")
        ['MagneticMomementPerUnitMass', 'Magnetization', 'SpontaneousMagnetization']

        ``'MagneticMomementPerUnitMass'`` appears because ``'MassMagnetization'`` is
        in its ``altLabel``.

        >>> me.search_labels("Magnetization", auto_wildcard=False)
        ['Magnetization']
    """
    label = f"*{text}*" if auto_wildcard else text
    thing_set = mammos_ontology.get_by_label_all(label)
    list_of_labels = sorted(str(thing.prefLabel[0]) for thing in thing_set)
    return list_of_labels
