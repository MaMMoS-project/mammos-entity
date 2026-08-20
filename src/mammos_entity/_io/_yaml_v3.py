"""Reading function for yaml v3.

The collection:

```python
EntityCollection(
    description="File description.",
    Ms=Entity("SpontaneousMagnetization", [600, 650, 700], "kA/m"),
    T=Entity("ThermodynamicTemperature", [1, 2, 3], "K", description="from experiment 1"),
    angle=[0, 0.5, 0.7] * u.rad,
    demag_factor=Entity("DemagnetizingFactor", [1/3, 1/3, 1/3]),
    comment=["Some comment", "Some other comment", "A third comment"],
)
```

would create the file:

```
# mammos yaml v3
metadata: null
description: |-
  File description.
data:
  Ms:
    ontology_label: SpontaneousMagnetization
    ontology_iri: https://w3id.org/emmo/domain/magnetic-materials/0.0.6
    entity_iri: https://w3id.org/emmo/domain/magnetic-materials#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25
    unit: kA / m
    value: [600.0, 650.0, 700.0]
    description: ''
  T:
    ontology_label: ThermodynamicTemperature
    ontology_iri: https://w3id.org/emmo/domain/magnetic-materials/0.0.6
    entity_iri: https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f
    unit: K
    value: [1.0, 2.0, 3.0]
    description: from experiment 1
  angle:
    unit: rad
    value: [0.0, 0.5, 0.7]
  demag_factor:
    ontology_label: DemagnetizingFactor
    ontology_iri: https://w3id.org/emmo/domain/magnetic-materials/0.0.6
    entity_iri: https://w3id.org/emmo/domain/magnetic-materials#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e
    unit: ''
    value: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333]
    description: ''
  comment:
    value: [Some comment, Some other comment, A third comment]
```
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import TYPE_CHECKING

import mammos_units as u
import numpy as np
import yaml

import mammos_entity as me

if TYPE_CHECKING:
    import mammos_units
    import numpy.typing

    import mammos_entity


def _from_yaml_v3(filename: str | os.PathLike) -> mammos_entity.EntityCollection:
    """Read MaMMoS YAML file v3."""
    with open(filename) as f:
        file_content = yaml.safe_load(f)

    if not isinstance(file_content, Mapping):
        raise RuntimeError("mammos yaml v3 files must contain a top-level mapping.")

    if set(file_content.keys()) != {"metadata", "description", "data"}:
        raise RuntimeError(
            "mammos yaml v3 files must have exactly three top-level keys, 'metadata', 'description' and 'data'."
        )
    root = {
        "description": file_content["description"],
        "data": file_content["data"],
    }
    return _parse_yaml_collection_v3(root, "")


def _parse_yaml_collection_v3(
    node: Mapping, key: str, ontologies: dict | None = None
) -> mammos_entity.EntityCollection:
    key_display = key or "top-level collection"
    if set(node.keys()) != {"description", "data"}:
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid collection in mammos yaml v3: '
            f"invalid keys {sorted(node.keys())}; expected ['data', 'description']."
        )

    description = node["description"]
    if not isinstance(description, str):
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid collection in mammos yaml v3: '
            f'key "description" must be a string, found {type(description).__name__}.'
        )

    if not isinstance(node["data"], Mapping):
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid collection in mammos yaml v3: '
            f'key "data" must be a mapping, found {type(node["data"]).__name__}.'
        )
    if key == "" and not node["data"]:
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid collection in mammos yaml v3: key "data" does not contain anything.'
        )

    if ontologies is None:
        ontologies = {}

    collection = me.EntityCollection(description=description)
    for name, item in node["data"].items():
        child_path = f"{key}.{name}" if key else name
        if isinstance(item, Mapping):
            item_keys = set(item.keys())
            leaf_hint_keys = {"ontology_label", "ontology_iri", "entity_iri", "unit", "value"}
            # Route ambiguous mappings with collection keys to collection parsing,
            # unless they clearly belong to an entity-like schema.
            if item_keys & leaf_hint_keys:
                collection[name] = _parse_yaml_leaf_v3(item, child_path, ontologies)
            elif "description" in item_keys or "data" in item_keys:
                collection[name] = _parse_yaml_collection_v3(item, child_path, ontologies)
            else:
                collection[name] = _parse_yaml_leaf_v3(item, child_path, ontologies)
        else:
            collection[name] = _parse_yaml_leaf_v3(item, child_path)
    return collection


def _parse_yaml_leaf_v3(item: Mapping, key: str, ontologies: dict):
    key_display = key or "top-level collection"
    if not isinstance(item, Mapping):
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid entity-like in mammos yaml v3: '
            f"expected a mapping, found {type(item).__name__}."
        )

    keys = set(item)
    entity_keys = {"ontology_label", "description", "ontology_iri", "entity_iri", "unit", "value"}
    quantity_keys = {"unit", "value"}
    value_keys = {"value"}

    if keys == entity_keys:
        if not isinstance(item["ontology_label"], str):
            raise RuntimeError(
                f'Entry "{key_display}" is an invalid entity-like in mammos yaml v3: '
                f'key "ontology_label" must be a string, found '
                f"{type(item['ontology_label']).__name__}."
            )
        if not isinstance(item["description"], str):
            raise RuntimeError(
                f'Entry "{key_display}" is an invalid entity-like in mammos yaml v3: '
                f'key "description" must be a string, found '
                f"{type(item['description']).__name__}."
            )
        if not isinstance(item["ontology_iri"], str):
            raise RuntimeError(
                f'Entry "{key_display}" is an invalid entity-like in mammos yaml v3: '
                f'key "ontology_iri" must be a string, found '
                f"{type(item['ontology_iri']).__name__}."
            )
        if not isinstance(item["entity_iri"], str):
            raise RuntimeError(
                f'Entry "{key_display}" is an invalid entity-like in mammos yaml v3: '
                f'key "entity_iri" must be a string, found '
                f"{type(item['entity_iri']).__name__}."
            )

        # if the entity belongs to an ontology used before, we use it from
        # the `ontologies` dictionary. Otherwise, we initialize an ontology
        # with such iri and we use it to define the entity.
        ontology_iri = item["ontology_iri"]
        ontology = ontologies.get(ontology_iri, me.Ontology([ontology_iri], initialize=True))

        entity = me.Entity(
            ontology_label=item["ontology_label"],
            value=item["value"],
            unit=item["unit"],
            iri=item["entity_iri"],
            description=item["description"],
            ontology=ontology,
        )
        return entity
    elif keys == quantity_keys:
        return u.Quantity(item["value"], item["unit"])
    elif keys == value_keys:
        return item["value"]
    else:
        expected = [sorted(entity_keys), sorted(quantity_keys), sorted(value_keys)]
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid entity-like in mammos yaml v3: '
            f"invalid keys {sorted(keys)}; expected one of {expected}."
        )


def _to_yaml_v3(collection: me.EntityCollection, filename: str | os.PathLike) -> None:
    """Write MaMMoS YAML file v3.

    Args:
        collection: EntityCollection to write.
        filename: Path of file to write.
    """
    if len(collection) == 0:
        raise ValueError("Empty collections cannot be saved to YAML.")

    entity_dict = {"metadata": None, **_serialize_collection(collection)}
    with open(filename, "w") as f:
        f.write("# mammos yaml v3\n")
        yaml.dump(
            entity_dict,
            stream=f,
            Dumper=get_dumper(),
            default_flow_style=False,
            sort_keys=False,
        )


def _serialize_entity_like(
    element: mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike,
) -> dict:
    if isinstance(element, me.Entity):
        return {
            "ontology_label": element.ontology_label,
            "description": element.description,
            "ontology_iri": element.ontology_iri,
            "entity_iri": element.entity_iri,
            "unit": str(element.unit),
            "value": element.value.tolist(),
        }
    elif isinstance(element, u.Quantity):
        return {
            "unit": str(element.unit),
            "value": element.value.tolist(),
        }
    else:
        return {"value": np.asanyarray(element).tolist()}


def _serialize_collection(collection: mammos_entity.EntityCollection) -> dict:
    result = {"description": collection.description, "data": {}}
    for name, element in collection:
        if isinstance(element, me.EntityCollection):
            result["data"][name] = _serialize_collection(element)
        else:
            result["data"][name] = _serialize_entity_like(element)
    return result


def get_dumper():
    # custom dumper to change style of lists, tuples and multi-line strings
    class _Dumper(yaml.SafeDumper):
        pass

    _Dumper.add_representer(list, _represent_sequence)
    _Dumper.add_representer(tuple, _represent_sequence)
    _Dumper.add_representer(str, _represent_string)
    return _Dumper


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
