<!--
Canonical source: MaMMoS-project/mammos-devtools, CONTRIBUTING-MaMMoS.md.
Package copies are generated with `pixi run sync-contributing` from
the mammos-devtools repository. Do not edit package copies directly.
-->

# Shared MaMMoS Contribution Guide

This guide contains contribution standards that apply across MaMMoS package
repositories. Repository-specific setup, checks, and release instructions belong
in each repository's `CONTRIBUTING.md`.

## Code and repository conventions

- Use American spelling in documentation, comments, and public names.
- Use the `src` layout for Python packages.
- Keep tests outside the deployed package.
- Follow Ruff for style decisions.
- Use 120-character line length for notebooks.
- Use semantic versioning for all packages.
- Update the metapackage version according to the largest version change of any
  dependent package or of the metapackage itself.

## Naming

- Capitalization of physical quantities and the objects or functions that create
  them follows the natural domain capitalization, even where this differs from
  normal Python naming conventions.
- Other code should follow PEP 8 naming conventions: `snake_case` for functions,
  methods, and properties; `CamelCase` for classes.
- Prefer clear names over short names. For example, prefer `energy_density` over
  `w`.

## Type hints

- All code should have complete type hints.
- Type hints should use the full MaMMoS package names instead of abbreviations.
  Abbreviations are acceptable only for widely known packages, such as `np` for
  `numpy`, `pd` for `pandas`, or `mpl` for `matplotlib.pyplot`.
- Avoid `from` imports used only for type hints.
- Use `from __future__ import annotations` where useful.
- Use `if TYPE_CHECKING:` guards for imports needed only by type checkers.

## Return values and inputs

- When a function or method returns more than one MaMMoS value, prefer a custom
  composite object based on `mammos_entity.EntityCollection`.
- Attributes of such composite objects should be `mammos_entity.Entity` objects
  where possible. If that is not possible, prefer `astropy.units.Quantity`, then
  ordinary Python values.
- Where relevant, accept and validate inputs in this order:
  `mammos_entity.Entity`, compatible quantity objects, then raw Python values.
- When accepting raw numbers or arrays, document and apply the entity base unit.

## Documentation and examples

- Public APIs should have docstrings with examples where practical.
- Examples should use explicit units and should show the expected entity labels.
- Keep user-facing documentation in README files, `CONTRIBUTING.md`, package
  docs, or examples. Agent-only operational advice belongs in `AGENTS.md`.

### Validating inputs to a function

```python
from __future__ import annotations

from typing import TYPE_CHECKING

import mammos_entity as me

if TYPE_CHECKING:
    # Import with full names to keep annotations explicit.
    import mammos_entity
    import mammos_units
    import numpy.typing


def compute_speed(
    length: mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike,
    time: mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike,
) -> mammos_entity.Entity:
    """Compute travelling speed.

    Args:
        length: The travelled distance as :entity:`Length`.
            If no unit is provided, values are interpreted as `m`.
        time: The travel time as :entity:`Time`.
            If no unit is provided, values are interpreted as `s`.

    Returns:
        The travelling speed as :entity:`Speed`.

    Examples:
        Passing entities:

        >>> import mammos_entity as me
        >>> length = me.Entity("Length", 10, "mm")
        >>> time = me.Entity("Time", 2, "s")
        >>> compute_speed(length, time)
        Entity(ontology_label='Speed', value=0.005, unit='m / s')

        Passing an array of raw numbers:

        >>> compute_speed([10, 20], [2, 2])
        Entity(ontology_label='Speed', value=array([5., 10.]), unit='m / s')
    """
    length = me._entity.from_compatible("Length", "m", length=length)
    time = me.Entity.from_compatible("Time", "s", time=time)
    speed = length.q / time.q
    return me.Entity("Speed", speed)
```

### Subclassing `EntityCollection`

```python
from __future__ import annotations

from typing import TYPE_CHECKING

import mammos_entity as me

if TYPE_CHECKING:
    import mammos_entity


@me._entity_collection.frozen_collection
class IntrinsicProperties(me.EntityCollection):
    """Intrinsic properties of a ferromagnet."""

    def __init__(
        self,
        Ms: mammos_entity.Entity,
        A: mammos_entity.Entity,
        Tc: mammos_entity.Entity,
        extra_object: str,
        description: str = "",
    ) -> None:
        """Create a new instance.

        Args:
            Ms: :entity:`SpontaneousMagnetization`.
            A: :entity:`ExchangeStiffnessConstant`.
            Tc: :entity:`CurieTemperature`.
            extra_object: A custom object specific to this class.
            description: Description of the collection.
        """
        me._entity.ensure_entity("SpontaneousMagnetization", Ms=Ms)
        me._entity.ensure_entity("ExchangeStiffnessConstant", A=A)
        me._entity.ensure_entity("CurieTemperature", Tc=Tc)
        super().__init__(description=description, Ms=Ms, A=A, Tc=Tc)
        self._extra_object = extra_object

    @property
    def extra_object(self) -> str:
        """Custom subclass-specific object."""
        return self._extra_object
```

## Changelog fragments

- Follow the package repository's `changes/README.md` instructions.
- Most user-visible pull requests should include a Towncrier fragment.
- Internal-only changes can use the `misc` fragment type when the package allows
  it.

## AI-assisted contributions

Code generated with help from an AI assistant must be marked in the commit
message:

```text
Assisted-by: agent:model
```

For example:

```text
Assisted-by: OpenAI Codex:gpt-5.3-codex
```

The human submitter remains responsible for reviewing, testing, and maintaining
the contribution.
