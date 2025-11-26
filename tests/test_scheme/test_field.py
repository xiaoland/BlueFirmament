"""Tests of model.field module
"""


from blue_firmament.model.field import field


def test_field_basic():
    """Test basic field functionality
    """
    f = field(default=42)
    assert f.default_value == 42

    f2 = f.fork(default=100)
    assert f2.default_value == 100
    
