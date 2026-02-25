"""Private type variable definitions shared across typing modules."""

from typing import TypeVar

#: Type variable bound to ontology labels represented as strings.
#:
#: This is the shared label parameter used by generic type hints such as
#: :py:class:`mammos_entity.Entity` and :py:data:`mammos_entity.typing.EntityLike`.
OntologyLabelT = TypeVar("OntologyLabelT", bound=str)
