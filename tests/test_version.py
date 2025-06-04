import mammos_entity


def test_version():
    """Check that __version__ exists and is a string."""
    assert isinstance(mammos_entity.__version__, str)
