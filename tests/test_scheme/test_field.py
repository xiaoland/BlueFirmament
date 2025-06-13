"""Tests of scheme.field module
"""


from blue_firmament.scheme.field import field


def test_dump_flags():
    """Test field dump flags
    """
    f = field(dump_flags={"flag_a", "flag_b"})
    assert f.dump_flags == {"flag_a", "flag_b"}

    f2 = f.fork(dump_flags={"flag_c",})
    assert f2.dump_flags == {"flag_c",}
    
