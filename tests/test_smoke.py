import sys
sys.path.insert(0, "/content/Beld")

def test_imports():
    import beld
    import beld.rendering
    import beld.export
    import beld.pipeline
    import beld.models
    import beld.geometry
    import beld.openings
    import beld.validation
    import beld.walls

    assert beld is not None
    assert beld.rendering is not None
    assert beld.export is not None
    assert beld.pipeline is not None
    assert beld.models is not None
    assert beld.geometry is not None
    assert beld.openings is not None
    assert beld.validation is not None
    assert beld.walls is not None
