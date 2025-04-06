[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/MaMMoS-project/mammos-entity/main?urlpath=%2Fdoc%2Ftree%2Fdocs%2Fexample.ipynb)

# Installation
To install `mammos-entity` locally (in editable mode) using `pip`:
```console
~> git clone https://github.com/MaMMoS-project/mammos-entity.git
~> cd mammos-entity
~> pip install -e .
```

> [!TIP]
> If you want to install the package how the god wanted it to be :pray:, install `pixi`(https://pixi.sh/latest/#installation) and run :raised_hands:
> ```console
> pixi install --frozen
> ```

# MaMMoS Entities

## Definitions

- a **quantity** is an object that carries a value and units.

- an **entity** is a quantity, which in addition links the entity to its definition in the [ontology](https://mammos-project.github.io/MagneticMaterialsOntology/doc/magnetic_material_mammos.html).

This package provides entities.

## Recommended `import`

```python
>>> import mammos_entity as me  # MaMMoS Entities. Or later Magnetic Entities
```

For entities that are important in MaMMoS, there are (or there will be) short cut definitions. For example for the saturation magnetisation we have:

```python
>>> Ms = me.Ms(800e3)  # defines Ms = 8e5 A/m  (default units are SI, i.e. A/m here)
>>> Ms
SpontaneousMagnetization(value=800000.0, unit=A / m)
```

## Entities behaves like Quantity

Each entities has all the attributes and methods that are available for Quantities (in AstroPy or MaMMosUnits). See [unit examples](https://github.com/MaMMoS-project/mammos-units/blob/main/docs/example.ipynb) for details.
Important attributes:

```python
>>> Ms.value
np.float64(800000.0)
>>> Ms.unit
Unit('A/m')
```
## Access to Ontology
Each entity object knows about its role in the Ontology:

```python
>>> Ms.label
'SpontaneousMagnetization'
>>> Ms.ontology
magnetic_material_mammos.SpontaneousMagnetization
>>> Ms_ontology = Ms.ontology  # retrieves a ThingClass from owlready2
>>> Ms_ontology.get_annotations()  # behaves like a normal Thing
{'prefLabel': [locstr('SpontaneousMagnetization', 'en')],
'elucidation': [locstr('The spontaneous magnetization, Ms, of a ferromagnet is the result\nof alignment of the magnetic moments of individual atoms. Ms exists\nwithin a domain of a ferromagnet.', 'en')],
'altLabel': [locstr('Ms', '')],
'wikipediaReference': [locstr('https://en.wikipedia.org/wiki/Spontaneous_magnetization', '')],
'IECEntry': [locstr('https://www.electropedia.org/iev/iev.nsf/display?openform&ievref=221-02-41', '')]}
```

## Initialising entities conveniently

If no options are provided, SI units are chosen:
```python
>>> m1 = me.Ms(8e5)
```
If units are provided as a string (and understood), these can be used:
```python
>>> m2 = me.Ms(8e5, "A/m")  # no change as A/m are the default SI units
>>> m3 = me.Ms(800, "kA/m")  # use KilloAmp / m 
>>> print(m1)
SpontaneousMagnetization(value=800000.0, unit=A / m)
>>> print(m2)
SpontaneousMagnetization(value=800000.0, unit=A / m)
>>> print(m3)
SpontaneousMagnetization(value=800.0, unit=kA / m)
```

It is not allowed to initialise an entity with wrong units.
```python
>>> m4 = me.Ms(1.2, "T")
...
TypeError: The unit T does not match the units of SpontaneousMagnetization
```

## Entity operations

The `Quantity` object (which is the AstroPy unit object) [supports many operations](https://astro-docs.readthedocs.io/en/latest/units/) that act on the numbers as normal and carries along the units silently. For example:

```python
>>> m2**2
$6.4 \times 10^{11} \; \mathrm{\frac{A^{2}}{m^{2}}}$
```

However, since the units do not correspond to the right ontology object, the `ontology` property is dropped.
```python
>>> m2**2.ontology
...
AttributeError: 'Quantity' object has no 'ontology' member
```

## Direct conversion of units


```python
>>> print(m2)  # 8e5 A/m
SpontaneousMagnetization(value=800000.0, unit=A / m)
>>> print(m2.to("mA/m"))  # prefactor change only, leads to 8e8 mA/m
SpontaneousMagnetization(value=800000000.0, unit=mA / m)
```

## Indirect conversion

Where the conversion needs conversion factors with units (here called "indirect"), we need to be explicit that this is what we want:

```python
>>> import astropy.units as u
>>> print(m3)
SpontaneousMagnetization(value=800.0, unit=kA / m)
>>> m4 = m3.quantity.to("T", equivalencies=u.magnetic_flux_field())
>>> print(m4)
1.005309649696 T
```

## Defining vector entities (Example Zeeman field)

It is possible to pass a collection as a value to the entity.

```python
>>> H = me.H([1e4, 1e4, 1e4], "A/m")
>>> H
ExternalMagneticField(value=[10000. 10000. 10000.], unit=A / m)
>>> H.ontology
magnetic_material_mammos.ExternalMagneticField
>>> H.ontology.get_class_properties()
{emmo.elucidation, core.prefLabel, emmo.hasMeasurementUnit, core.altLabel}
>>> H.ontology.elucidation
[locstr('The external field H′, acting on a sample that is produced by\nelectric currents or the stray field of magnets outside the sample\nvolume, is often called the applied field.', 'en')]
```

## Does `mammos_entity` not provide your preferred entity?

You can create any entity defined in the MaMMoS ontology on the fly


```python
>>> list(me.mammos_ontology.classes())
[magnetic_material_mammos.EulerAngles,
 magnetic_material_mammos.CoercivityHcExternal,
 magnetic_material_mammos.DemagnetizingFactor,
 ...
 magnetic_material_mammos.MagneticMomementPerUnitMass,
 magnetic_material_mammos.EasyAxisDistributionSigma,
 magnetic_material_mammos.CellVolume]
>>> rem = me.Entity("Remanence", value=1e5)
>>> rem
Remanence(value=100000.0, unit=A / m)
>>> rem.value
np.float64(100000.0)
>>> rem.unit
Unit('A/m')
>>> rem.ontology
magnetic_material_mammos.Remanence
```

Once again, if the units of the initialised entity do not match the ontology, the entity will not be created.

```python
>>> me.Entity("Remanence", value=1.7e4, unit="m")
...
TypeError: The unit m does not match the units of Remanence
```
