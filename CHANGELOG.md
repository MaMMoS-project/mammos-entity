# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This project uses [towncrier](https://towncrier.readthedocs.io/) and the changes for the upcoming release can be found in [changes](changes).

<!-- towncrier release notes start -->

## [mammos-entity 0.13.0](https://github.com/MaMMoS-project/mammos-entity/tree/0.13.0) – 2026-04-22

### Changed

- Updated versions of shipped ontologies: Magnetic Materials domain Ontology (MagMO) to 0.0.5. ([#215](https://github.com/MaMMoS-project/mammos-entity/pull/215))


## [mammos-entity 0.12.0](https://github.com/MaMMoS-project/mammos-entity/tree/0.12.0) – 2026-03-06

### Added

- Now `Entity` instances have a `description` attribute, containing a string with user-defined information (empty by default). ([#102](https://github.com/MaMMoS-project/mammos-entity/pull/102))
- `EntityCollection` instances have a `description` attribute, containing a string with user-defined information (empty by default). ([#103](https://github.com/MaMMoS-project/mammos-entity/pull/103))
- Added i/o functionalities to preserve `description` attribute for `Entity` and `EntityCollection` instances. This results in an extra metadata line (in csv format v3) or key (in yaml format v2) for files.
  Furthermore, in csv format v3 ontology and unit information are no longer commented. ([#105](https://github.com/MaMMoS-project/mammos-entity/pull/105))
- Added function `mammos_entity.search_labels` to search for matches in the ontology to a specific label. ([#117](https://github.com/MaMMoS-project/mammos-entity/pull/117))
- New methods `EntityCollection.metadata` to extract metadata for all entities in a collection (as dictionary) and `EntityCollection.from_dataframe` to convert a `pandas.DataFrame` + metadata dictionary into an `EntityCollection`. ([#123](https://github.com/MaMMoS-project/mammos-entity/pull/123))
- Dictionary-like interface for `EntityCollection`: support for element access with `["name"]` notation, iterating over entities in collection and member-checks with `in`. ([#130](https://github.com/MaMMoS-project/mammos-entity/pull/130))
- Added functions to create anisotropy constants `mammos_entity.K1`, `mammos_entity.K2`. ([#141](https://github.com/MaMMoS-project/mammos-entity/pull/141))
- Support for reading and writing HDF5 files. ([#147](https://github.com/MaMMoS-project/mammos-entity/pull/147))
- A new property `Entity.ontology_iri` that returns the IRI of the corresponding element in the ontology. ([#161](https://github.com/MaMMoS-project/mammos-entity/pull/161))
- Mammos yaml v2: description is now a top-level key; non-entity elements in a collection no longer have keys with null values (ontology_label, ontology_iri, descripiton, [unit]) in the yaml representation. ([#173](https://github.com/MaMMoS-project/mammos-entity/pull/173))
- Mammos yaml v2: support for nested entity collections. ([#174](https://github.com/MaMMoS-project/mammos-entity/pull/174))
- Mammos yaml v2: empty entity collections can not be saved to yaml (empty nested collections are allowed). ([#176](https://github.com/MaMMoS-project/mammos-entity/pull/176))

### Changed

- Class `EntityCollection` can now be accessed with `mammos_entity.EntityCollection`. Operations are moved into the `mammos_entity.operations` submodules and are no longer accessible from the `mammos_entity` namespace. (Internally, some private submodules were renamed: `_base` -> `_entity`, `_entities` -> `_factory`, and `_onto` -> `_ontology`. The code for `EntityCollection` has been moved to `mammos_entity._entity_collection`.) ([#115](https://github.com/MaMMoS-project/mammos-entity/pull/115))
- The method `to_dataframe` of class `EntityCollection` now has default value `include_units=False`. ([#116](https://github.com/MaMMoS-project/mammos-entity/pull/116))
- Definition and methods of `Entity` now rely on a list of set equivalencies, called `mammos_equivalencies`. For the moment, they only include equivalencies between different temperature units. ([#118](https://github.com/MaMMoS-project/mammos-entity/pull/118))
- The API for writing and reading files has been changed in a backward incompatible way. Writing is now done via methods `EntityCollection.to_csv`, `EntityCollection.to_hdf5` and `EntityCollection.to_yaml`. Reading with the functions `mammos_entity.from_csv`, `mammos_entity.from_hdf5`, and `mammos_entity.from_yaml`. The `io` submodule has been removed. ([#154](https://github.com/MaMMoS-project/mammos-entity/pull/154))
- Saving an empty EntityCollection to csv is no longer allowed. ([#160](https://github.com/MaMMoS-project/mammos-entity/pull/160))
- All elements in an EntityCollection must have names of type str. ([#172](https://github.com/MaMMoS-project/mammos-entity/pull/172))
- Updated versions of shipped ontologies: Magnetic Materials domain Ontology (MagMO) to 0.0.4, EMMO to 1.0.3. ([#177](https://github.com/MaMMoS-project/mammos-entity/pull/177))

### Fixed

- Conversion to dataframe failed for entity collections containing only scalar entities. ([#157](https://github.com/MaMMoS-project/mammos-entity/pull/157))
- Conversion of nested entity collection to dataframe is now prohibited. Before, the elements of the inner collection were added as dataframe rows. ([#158](https://github.com/MaMMoS-project/mammos-entity/pull/158))
- Fixed unit definition logic after update to MagMO 0.0.4. If the user provides a unit, it is accepted if it is equivalent to any of the ontology defined units. ([#169](https://github.com/MaMMoS-project/mammos-entity/pull/169))
- Creating entities with secondary labels will from now on produce entities with the `prefLabel` as their `ontology_label`. ([#170](https://github.com/MaMMoS-project/mammos-entity/pull/170))

### Misc

- Use of `csv` Python module for i/o in csv format. ([#104](https://github.com/MaMMoS-project/mammos-entity/pull/104))
- IRI is not checked for consistency when reading a file anymore. ([#187](https://github.com/MaMMoS-project/mammos-entity/pull/187))
- Changed selection process of ontology label in the initialization of an Entity. First, the given label is matched for `prefLabel` in the ontology. If no match is found, the given label is matched for all alternative labels. If any of the previous steps finds more than one match, an error is raised. If no matches are found after the previous steps, an error is raised. ([#191](https://github.com/MaMMoS-project/mammos-entity/pull/191))
- An internal helper function to convert an entity-like to the desired entity. ([#201](https://github.com/MaMMoS-project/mammos-entity/pull/201))


## [mammos-entity 0.11.1](https://github.com/MaMMoS-project/mammos-entity/tree/0.11.1) – 2025-12-11

### Fixed

- Fixed logic to establish ontology-preferred units. ([#98](https://github.com/MaMMoS-project/mammos-entity/pull/98))


## [mammos-entity 0.11.0](https://github.com/MaMMoS-project/mammos-entity/tree/0.11.0) – 2025-11-27

### Changed

- Improved `mammos_entity.io` notebook. Use cases for working with `EntityCollection` objects are added. ([#83](https://github.com/MaMMoS-project/mammos-entity/pull/83))

### Misc

- Fix dependencies: remove upper limit for `emmontopy` and add `pandas>2`. ([#93](https://github.com/MaMMoS-project/mammos-entity/pull/93))


## [mammos-entity 0.10.0](https://github.com/MaMMoS-project/mammos-entity/tree/0.10.0) – 2025-08-07

### Added

- Add `description` optional argument to `mammos_entity.io.entities_to_csv`. ([#52](https://github.com/MaMMoS-project/mammos-entity/pull/52))
- Add `mammos_entity.concat_flat` function to concatenate entities (with same ontology label), quantities (with compatible units) and Python types into a single entity. ([#56](https://github.com/MaMMoS-project/mammos-entity/pull/56))
- Two new functions `mammos_entity.io.entities_from_file` and `mammos_entity.io.entities_to_file` to read and write entity files. The file type is inferred from the file extension. ([#57](https://github.com/MaMMoS-project/mammos-entity/pull/57))
- Support for YAML as additional file format in `mammos_entity.io`. ([#59](https://github.com/MaMMoS-project/mammos-entity/pull/59))

### Changed

- Structure of mammos CSV format documentation. ([#55](https://github.com/MaMMoS-project/mammos-entity/pull/55))
- IRIs are checked when reading a file with `mammos_entity.io`. If IRI and ontology label do not match the reading fails. ([#68](https://github.com/MaMMoS-project/mammos-entity/pull/68))

### Deprecated

- Functions `mammos_entity.io.entities_to_csv` and `mammos_entity.io.entities_from_csv` have been deprecated. Use the generic `mammos_entitiy.io.entities_to_file` and `mammos_entity.io.entities_from_file` instead. ([#58](https://github.com/MaMMoS-project/mammos-entity/pull/58))

### Fixed

- Wrong newline separation of data lines in CSV files written with `mammos_entity.io.entities_to_csv` on Windows. ([#66](https://github.com/MaMMoS-project/mammos-entity/pull/66))
- Mixed 0 dimensional and 1 dimensional entities written to csv, which were not round-trip safe, are no longer allowed. ([#67](https://github.com/MaMMoS-project/mammos-entity/pull/67))

### Misc

- Use [towncrier](https://towncrier.readthedocs.io) to generate changelog from fragments. Each new PR must include a changelog fragment. ([#50](https://github.com/MaMMoS-project/mammos-entity/pull/50))
