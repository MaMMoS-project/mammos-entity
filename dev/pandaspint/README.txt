In the context of this issue: https://github.com/MaMMoS-project/mammos-entity/issues/77,

here is an attempt to see what pandas-pint can do for us.

Short summary:

- we create pandas dtype that carries units
- probably not as performant as floats but that doesn't matter here so much here.

Questions:

- Could we have entity objects in a pandas dataframe
  - probably not. If it that was possible, one should also be able to have pint-dtypes (and we woulnd'nt need an extra package called pint-pandas)
  - should we consider having an extension (something like entity-pandas)?


