r"""Reading function for csv v4.

The collection:

```python
EntityCollection(
    description="Test file description.\nTest second line.",
    Ms=Entity("SpontaneousMagnetization", [600, 650, 700], "kA/m", description="first line\nsecond line"),
    T=Entity("ThermodynamicTemperature", [1, 2, 3], "K", description="description, with a comma"),
    angle=[0, 0.5, 0.7] * u.rad,
    demag_factor=Entity("DemagnetizingFactor", [1/3, 1/3, 1/3]),
    comment=["Some comment", "Some other comment", "A third comment"],
)
```

would create the file:

```
#mammos csv v4
#----------------------------------------
# Test file description.
# Test second line.
#----------------------------------------
SpontaneousMagnetization,ThermodynamicTemperature,,DemagnetizingFactor,
"first line
second line","description, with a comma",,
https://w3id.org/emmo/domain/magnetic-materials/0.0.6,https://w3id.org/emmo/domain/magnetic-materials/0.0.6,,https://w3id.org/emmo/domain/magnetic-materials/0.0.6,
https://w3id.org/emmo/domain/magnetic-materials#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25,https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f,,https://w3id.org/emmo/domain/magnetic-materials#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e,
kA / m,K,rad,,
Ms,T,angle,demag_factor,comment
600.0,1.0,0.0,0.3333333333333333,Some comment
650.0,2.0,0.5,0.3333333333333333,Some other comment
700.0,3.0,0.7,0.3333333333333333,A third comment
```
"""

from __future__ import annotations

import csv
import os
from typing import TYPE_CHECKING

import mammos_units as u
import pandas as pd

import mammos_entity as me

if TYPE_CHECKING:
    import os

    import mammos_entity


def _from_csv_v4(csvfile):
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
    reader = csv.reader(
        csvfile,
        delimiter=",",
        quoting=csv.QUOTE_MINIMAL,
        lineterminator=os.linesep,
    )
    try:
        ontology_labels = next(reader)
        descriptions = next(reader)
        ontology_iris = next(reader)
        entity_iris = next(reader)
        units = next(reader)
    except StopIteration as exc:
        raise RuntimeError("CSV metadata is incomplete. Expected five metadata rows before the data table.") from exc

    try:
        data = pd.read_csv(csvfile)
    except pd.errors.EmptyDataError as exc:
        raise RuntimeError("CSV data table is empty.") from exc
    names = data.keys()
    scalar_data = len(data) == 1

    # load ontologies
    ontologies = {iri: me.Ontology(iris=[iri], initialize=True) for iri in set(ontology_iris) if iri}

    try:
        columns = list(zip(names, ontology_labels, descriptions, ontology_iris, entity_iris, units, strict=True))
    except ValueError as exc:
        raise RuntimeError("CSV metadata columns and data columns do not match.") from exc

    collection = me.EntityCollection(description="\n".join(collection_description))
    for name, ontology_label, description, ontology_iri, entity_iri, unit in columns:
        data_values = data[name].values if not scalar_data else data[name].values[0]
        if ontology_label:
            entity = me.Entity(
                ontology_label=ontology_label,
                value=data_values,
                unit=unit,
                iri=entity_iri,
                description=description,
                ontology=ontologies[ontology_iri],
            )
            collection[name] = entity
        elif unit:
            collection[name] = u.Quantity(data_values, unit)
        else:
            collection[name] = data_values

    return collection


def _to_csv_v4(collection: mammos_entity.EntityCollection, filename: os.PathLike) -> None:
    """Write EntityCollection into mammos csv v4 format.

    Args:
        collection: EntityCollection to write to file.
        filename: Path of the file to write.
    """
    if any(isinstance(element, me.EntityCollection) for _name, element in collection):
        raise ValueError("Nested collections cannot be saved to CSV.")
    if len(collection) == 0:
        raise ValueError("Empty collections cannot be saved to CSV.")

    # convert data first because that will catch incompatible shape
    dataframe = collection.to_dataframe()

    # Header rows written in CSV format.
    metadata_rows = [
        [getattr(elem, "ontology_label", "") for _, elem in collection],
        [getattr(elem, "description", "") for _, elem in collection],
        [getattr(elem, "ontology_iri", "") for _, elem in collection],
        [getattr(elem, "entity_iri", "") for _, elem in collection],
        [str(getattr(elem, "unit", "")) for _, elem in collection],
    ]

    with open(filename, "w", newline="") as csvfile:
        csvfile.write(f"# mammos csv v4{os.linesep}")
        if collection.description:
            csvfile.write("#" + "-" * 40 + os.linesep)
            for line in collection.description.splitlines():
                csvfile.write(f"# {line}{os.linesep}")
            csvfile.write("#" + "-" * 40 + os.linesep)

        writer = csv.writer(
            csvfile,
            delimiter=",",
            quoting=csv.QUOTE_MINIMAL,
            lineterminator=os.linesep,
        )
        writer.writerows(metadata_rows)

        dataframe.to_csv(csvfile, index=False)
