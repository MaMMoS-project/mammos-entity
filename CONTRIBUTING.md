# Installation development
## Clone the repository

To get started clone the `mammos-entity` repository via `ssh`:

```shell
git clone git@github.com:MaMMoS-project/mammos-entity.git
```
or `https` if you don't have an `ssh` key:

```shell
git clone https://github.com/MaMMoS-project/mammos-entity.git
```

Then enter into the repository:

```shell
cd mammos-entity
```

## Install dependencies with pixi

- install [pixi](https://pixi.sh)

- activate pre-commits by running `pre-commit install`

- run `pixi shell` to create and activate an environment in which `mammos-entity` is installed (this will install python as well)

- the following pixi tasks are provided:

  - `pixi run test-unittest`: Run unittests with pytest (reading tests/)
  - `pixi run test-docstrings`: Run doctests with pytest (reading src/mammos_entity)
  - `pixi run test-notebooks`: Run nbval with pytest on notebooks (reading examples/)
  - `pixi run test-all`: run `unittest`, `doctest` and `notebooktest`
  - `pixi run examples`: start jupyter lab in examples/ directory
  - `pixi run style`: style checks on all files using `pre-commit run --all-files`


## Updating shipped ontologies
This Python packages ship the ontologies EMMO and MagMO to allow offline use. When these ontologies change, it is necessary to manually change them.

- **EMMO**: this can be downloaded from https://w3id.org/emmo/<version>/inferred by specifying the desired `<version>`.

- **MagMO**: Download the turtle file `magnetic-materials.ttl` from the [MagneticMaterialsOntology Releases](https://github.com/MaMMoS-project/MagneticMaterialsOntology/releases) and put it in the `src/mammos-entity/ontology` repository (overwriting the previous file). No further changes are necessary.
