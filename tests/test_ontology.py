"""Test MagMO ontology."""


def test_search_labels_multiple(magmo):
    """Search labels with multiple matches."""
    res = magmo.search_labels("Polarization")
    assert res == [
        "ElectricPolarization",
        "RemanentMagneticPolarization",
        "SaturationMagneticPolarization",
        "SpontaneousMagneticPolarization",
    ]


def test_search_labels_single(magmo):
    """Search labels with only one match."""
    assert magmo.search_labels("SpontaneousMagnetization") == ["SpontaneousMagnetization"]


def test_search_labels_no_matches(magmo):
    """Search labels with no matches."""
    assert magmo.search_labels("ThisLabelHasNoMatches") == []


def test_search_labels_whole_match(magmo):
    """Search labels with match to whole label activated.

    This search would give multiple results without the flag activated.
    """
    assert magmo.search_labels("Polarization", auto_wildcard=False) == []
    assert magmo.search_labels("*Polarization*", auto_wildcard=False) == magmo.search_labels("*Polarization*")


def test_problematic_labels(magmo):
    """Test problematic labels.

    On Windows the function `get_by_label_all` with input label "Status" would return
    the object `bibo.status`, but the string "Status" is not included in `label`,
    `altLabel`, `prefLabel`. The function `search_labels` should fix this behaviour.
    """
    assert magmo.search_labels("Status") == ["Status", "hasStatus"]


def test_empty_label(magmo):
    """Test querying for all possible entity labels.

    We test that the labels of some highly used entities appear when searching for
    all possible labels.
    """
    all_labels = magmo.search_labels("")
    assert "SpontaneousMagnetization" in all_labels
    assert "ExchangeStiffnessConstant" in all_labels
    assert "MaximumEnergyProduct" in all_labels
    assert "CurieTemperature" in all_labels
