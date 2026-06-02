from mammos_entity import search_labels
from mammos_entity._ontology import _search_metadata


def test_search_labels_multiple():
    """Search labels with multiple matches."""
    res = search_labels("Polarization")
    assert res == [
        "ElectricPolarization",
        "RemanentMagneticPolarization",
        "SaturationMagneticPolarization",
        "SpontaneousMagneticPolarization",
    ]


def test_search_labels_single():
    """Search labels with only one match."""
    assert search_labels("SpontaneousMagnetization") == ["SpontaneousMagnetization"]


def test_search_labels_no_matches():
    """Search labels with no matches."""
    assert search_labels("ThisLabelHasNoMatches") == []


def test_search_labels_whole_match():
    """Search labels with match to whole label activated.

    This search would give multiple results without the flag activated.
    """
    assert search_labels("Polarization", auto_wildcard=False) == []
    assert search_labels("*Polarization*", auto_wildcard=False) == search_labels(
        "*Polarization*"
    )


def test_problematic_labels():
    """Test problematic labels.

    On Windows the function `get_by_label_all` with input label "Status" would return
    the object `bibo.status`, but the string "Status" is not included in `label`,
    `altLabel`, `prefLabel`. The function `search_labels` should fix this behaviour.
    """
    assert search_labels("Status") == ["Status", "hasStatus"]


def test_empty_label():
    """Test querying for all possible entity labels.

    We test that the labels of some highly used entities appear when searching for
    all possible labels.
    """
    all_labels = search_labels("")
    assert "SpontaneousMagnetization" in all_labels
    assert "ExchangeStiffnessConstant" in all_labels
    assert "MaximumEnergyProduct" in all_labels
    assert "CurieTemperature" in all_labels


def test_search_metadata():
    """Test _search_metadata function.

    1. Querying for all entities containing the word 'anisotropy' in their
      elucidation or comment.
    2. Querying for all entities whose elucidation or comment is strictly
      the word 'anisotropy'.
    3. Querying for all entities containing the word 'Anisotropy' (capitalized)
      in their elucidation or comment.
    """
    assert _search_metadata("anisotropy") == [
        "AnisotropyField",
        "CubicMagnetocrystallineAnisotropy",  # only in elucidation
        "InducedMagneticAnisotropy",  # only in elucidation
        "MagneticAnisotropy",  # only in elucidation
        "MagnetocrystallineAnisotropy",  # only in elucidation
        "MagnetocrystallineAnisotropyConstantK1",  # only in comment
        "MagnetocrystallineAnisotropyConstantK1c",  # only in comment
        "MagnetocrystallineAnisotropyConstantK2",  # only in comment
        "MagnetocrystallineAnisotropyConstantK2c",  # only in comment
        "MagnetocrystallineAnisotropyEnergy",  # only in elucidation
        "ShapeAnisotropy",  # only in comment
        "UniaxialMagneticAnisotropy",  # only in elucidation
        "UniaxialAnisotropyConstant",  # only in elucidation
        "UniaxialMagnetocrystallineAnisotropy",  # only in elucidation
    ]
    assert _search_metadata("anisotropy", auto_wildcard=False) == []
    assert _search_metadata("Anisotropy") == []
