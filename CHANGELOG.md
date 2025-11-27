# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This project uses [towncrier](https://towncrier.readthedocs.io/) and the changes for the upcoming release can be found in [changes](changes).

<!-- towncrier release notes start -->

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
