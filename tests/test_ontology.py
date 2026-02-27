from mammos_entity import search_labels


def test_search_labels_multiple():
    """Search labels with multiple matches."""
    res = search_labels("Polarization")
    assert res == ["ElectricPolarization", "RemanentMagneticPolarization"]


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
