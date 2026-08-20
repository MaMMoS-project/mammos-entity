"""Reading function for yaml v1.

The collection:

```python
EntityCollection(
    Ms=Entity("SpontaneousMagnetization", [600, 650, 700], "kA/m"),
    T=Entity("ThermodynamicTemperature", [1, 2, 3], "K"),
    angle=[0, 0.5, 0.7] * u.rad,
    demag_factor=Entity("DemagnetizingFactor", [1/3, 1/3, 1/3]),
    comment=["Some comment", "Some other comment", "A third comment"],
)
```

would create the file:

```
metadata:
  version: v1
  description: null
data:
  Ms:
    ontology_label: SpontaneousMagnetization
    ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25
    unit: kA / m
    value: [600.0, 650.0, 700.0]
  T:
    ontology_label: ThermodynamicTemperature
    ontology_iri: https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f
    unit: K
    value: [1.0, 2.0, 3.0]
  angle:
    ontology_label: null
    ontology_iri: null
    unit: rad
    value: [0.0, 0.5, 0.7]
  demag_factor:
    ontology_label: DemagnetizingFactor
    ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e
    unit: ''
    value: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333]
  comment:
    ontology_label: null
    ontology_iri: null
    unit: null
    value: [Some comment, Some other comment, A third comment]
```
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING

import mammos_units as u
import numpy as np
import yaml

import mammos_entity as me

if TYPE_CHECKING:
    import os

    import mammos_entity


def _from_yaml_v1(filename: str | os.PathLike) -> mammos_entity.EntityCollection:
    """Read MaMMoS YAML file v1."""
    with open(filename) as f:
        file_content = yaml.safe_load(f)

    if not isinstance(file_content, Mapping):
        raise RuntimeError("mammos yaml v1 files must contain a top-level mapping.")

    if set(file_content.keys()) != {"metadata", "data"}:
        raise RuntimeError("mammos yaml v1 files must have exactly two top-level keys, 'metadata' and 'data'.")

    if not (
        "metadata" in file_content
        and isinstance(file_content["metadata"], Mapping)
        and "version" in file_content["metadata"]
        and file_content["metadata"]["version"] == "v1"
    ):
        raise RuntimeError("Wrong mammos yaml v1 syntax. Expected 'metadata' key with the 'version' equal to 'v1'.")

    collection_description = file_content["metadata"].get("description") or ""
    if not isinstance(file_content.get("data"), Mapping):
        raise RuntimeError("'data' must be a mapping.")
    if not file_content["data"]:
        raise RuntimeError("'data' does not contain anything.")
    collection = me.EntityCollection(description=collection_description)
    for key, item in file_content["data"].items():
        collection[key] = _parse_yaml_leaf_v1(item, key)
    return collection


def _parse_yaml_leaf_v1(item: Mapping, key: str):
    if not isinstance(item, Mapping):
        raise RuntimeError(f"Element '{key}' must be a mapping, found {type(item).__name__}.")

    keys = set(item)
    v1_keys = {"ontology_label", "ontology_iri", "unit", "value"}

    if keys != v1_keys:
        raise RuntimeError(f"Element '{key}' has invalid keys: {sorted(keys)}. Expected {sorted(v1_keys)}.")

    if item["ontology_label"] is not None:
        entity = me.Entity(
            ontology_label=item["ontology_label"],
            value=item["value"],
            unit=item["unit"],
        )
        return entity
    elif item["unit"] is not None:
        return u.Quantity(item["value"], item["unit"])
    else:
        return item["value"]


def _to_yaml_v1(collection: mammos_entity.EntityCollection, filename: os.PathLike) -> None:
    """Write EntityCollection into mammos csv v1 format."""

    def _preprocess_entity_args(entities: dict[str, str]) -> Iterator[tuple]:
        """Extract name, label, iri, unit and value for each item."""
        for name, element in entities.items():
            if isinstance(element, me.Entity):
                label = element.ontology_label
                iri = element.entity_iri
                unit = str(element.unit)
                value = element.value.tolist()
            elif isinstance(element, u.Quantity):
                label = None
                iri = None
                unit = str(element.unit)
                value = element.value.tolist()
            else:
                label = None
                iri = None
                unit = None
                value = np.asanyarray(element).tolist()
            yield name, label, iri, unit, value

    entity_dict = {
        "metadata": {
            "version": "v1",
            "description": collection.description if collection.description else None,
        },
        "data": {
            name: {
                "ontology_label": label,
                "ontology_iri": iri,
                "unit": unit,
                "value": value,
            }
            for name, label, iri, unit, value in _preprocess_entity_args(collection._entities)
        },
    }

    # custom dumper to change style of lists, tuples and multi-line strings
    class _Dumper(yaml.SafeDumper):
        pass

    def _represent_sequence(dumper, value):
        """Display sequence with flow style.

        A list [1, 2, 3] for key `value` is written to file as::

          value: [1, 2, 3]

        instead of::

          value:
            - 1
            - 2
            - 3

        """
        return dumper.represent_sequence("tag:yaml.org,2002:seq", value, flow_style=True)

    def _represent_string(dumper, value):
        """Control style of single-line and multi-line strings.

        Single-line strings are written as::

          some_key: Hello

        Multi-line strings are written as::

          some_key: |-
            I am multi-line,
            without a trailing new line.

        """
        style = "|" if "\n" in value else ""
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)

    _Dumper.add_representer(list, _represent_sequence)
    _Dumper.add_representer(tuple, _represent_sequence)
    _Dumper.add_representer(str, _represent_string)

    with open(filename, "w") as f:
        yaml.dump(
            entity_dict,
            stream=f,
            Dumper=_Dumper,
            default_flow_style=False,
            sort_keys=False,
        )
