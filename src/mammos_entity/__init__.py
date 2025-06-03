"""Entity (Quantity and EMMO ontology label).

Exposes the primary components of the MaMMoS entity package, including
the `Entity` class for ontology-linked physical quantities, pre-defined
factory methods for common magnetic entities (Ms, A, Ku, H), and the
loaded MaMMoS ontology object.
"""

from mammos_entity._base import Entity as Entity
from mammos_entity._entities import A as A
from mammos_entity._entities import B as B
from mammos_entity._entities import BHmax as BHmax
from mammos_entity._entities import H as H
from mammos_entity._entities import Hc as Hc
from mammos_entity._entities import Ku as Ku
from mammos_entity._entities import M as M
from mammos_entity._entities import Mr as Mr
from mammos_entity._entities import Ms as Ms
from mammos_entity._entities import T as T
from mammos_entity._entities import Tc as Tc
from mammos_entity._onto import mammos_ontology as mammos_ontology
