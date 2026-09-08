r"""Reading function for csv v2.

The collection:

```python
EntityCollection(
    description="Test file description.\nTest second line.",
    Ms=Entity("SpontaneousMagnetization", [600, 650, 700], "kA/m"),
    T=Entity("ThermodynamicTemperature", [1, 2, 3], "K"),
    angle=[0, 0.5, 0.7] * u.rad,
    demag_factor=Entity("DemagnetizingFactor", [1/3, 1/3, 1/3]),
    comment=["Some comment", "Some other comment", "A third comment"],
)
```

would create the file:

```
#mammos csv v2
#----------------------------------------
# Test file description.
# Test second line.
#----------------------------------------
#SpontaneousMagnetization,ThermodynamicTemperature,,DemagnetizingFactor,
#https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25,https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f,,https://w3id.org/emmo/domain/magnetic_material#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e,
#kA / m,K,rad,,
Ms,T,angle,demag_factor,comment
600.0,1.0,0.0,0.3333333333333333,Some comment
650.0,2.0,0.5,0.3333333333333333,Some other comment
700.0,3.0,0.7,0.3333333333333333,A third comment
```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import mammos_units as u
import pandas as pd

import mammos_entity as me

if TYPE_CHECKING:
    import os

    import mammos_entity


def _from_csv_v2(csvfile):
    collection_description = []
    # read description
    position = csvfile.tell()
    if csvfile.readline().startswith("#--"):
        while True:
            line = csvfile.readline()
            if line == "":
                raise RuntimeError("CSV description block is not terminated by a closing dashed line.")
            if line.startswith("#--"):
                break
            else:
                collection_description.append(line.removeprefix("# ").rstrip("\r\n"))
    else:
        # reset the file position
        csvfile.seek(position)

    # read ontology metadata
    metadata_rows = [csvfile.readline() for _ in range(3)]
    if any(row == "" for row in metadata_rows):
        raise RuntimeError("CSV metadata is incomplete. Expected three metadata rows before the data table.")
    ontology_labels = metadata_rows[0].strip().removeprefix("#").split(",")
    # ignore IRIs: metadata_rows[1]
    units = metadata_rows[2].strip().removeprefix("#").split(",")
    descriptions = [""] * len(ontology_labels)

    try:
        data = pd.read_csv(csvfile)
    except pd.errors.EmptyDataError as exc:
        raise RuntimeError("CSV data table is empty.") from exc
    names = data.keys()
    scalar_data = len(data) == 1

    try:
        columns = list(zip(names, ontology_labels, descriptions, units, strict=True))
    except ValueError as exc:
        raise RuntimeError("CSV metadata columns and data columns do not match.") from exc

    collection = me.EntityCollection(description="\n".join(collection_description))
    for name, ontology_label, description, unit in columns:
        data_values = data[name].values if not scalar_data else data[name].values[0]
        if ontology_label:
            entity = me.Entity(
                ontology_label=ontology_label,
                value=data_values,
                unit=unit,
                description=description,
            )
            collection[name] = entity
        elif unit:
            collection[name] = u.Quantity(data_values, unit)
        else:
            collection[name] = data_values

    return collection


def _to_csv_v2(collection: mammos_entity.EntityCollection, filename: os.PathLike) -> None:
    """Write EntityCollection into mammos csv v2 format."""
    ontology_labels = []
    ontology_iris = []
    units = []
    data = {}
    if_scalar_list = []
    for name, element in collection:
        if isinstance(element, me.Entity):
            ontology_labels.append(element.ontology_label)
            ontology_iris.append(element.ontology.iri)
            units.append(str(element.unit))
            data[name] = element.value
            if_scalar_list.append(pd.api.types.is_scalar(element.value))
        elif isinstance(element, u.Quantity):
            ontology_labels.append("")
            ontology_iris.append("")
            units.append(str(element.unit))
            data[name] = element.value
            if_scalar_list.append(pd.api.types.is_scalar(element.value))
        else:
            ontology_labels.append("")
            ontology_iris.append("")
            units.append("")
            data[name] = element
            if_scalar_list.append(pd.api.types.is_scalar(element))

    if any(if_scalar_list) and not all(if_scalar_list):
        raise ValueError("All entities must have the same shape, either 0 or 1.")

    dataframe = pd.DataFrame(data, index=[0]) if all(if_scalar_list) else pd.DataFrame(data)
    with open(filename, "w", newline="") as f:
        # newline="" required for pandas to_csv
        f.write(f"#mammos csv v2{os.linesep}")
        if collection.description:
            f.write("#" + "-" * 40 + os.linesep)
            for d in collection.description.split("\n"):
                f.write(f"# {d}{os.linesep}")
            f.write("#" + "-" * 40 + os.linesep)
        f.write("#" + ",".join(ontology_labels) + os.linesep)
        f.write("#" + ",".join(ontology_iris) + os.linesep)
        f.write("#" + ",".join(units) + os.linesep)
        dataframe.to_csv(f, index=False)
