"""Tests for scheme.main
"""

import datetime
from blue_firmament.scheme.main import BaseScheme
from blue_firmament.scheme import field, FieldT


class AS(BaseScheme):
    a: int = 1
    b: str = 'b'
    c: bool = False


def test_dump_to_str():
    """Test BaseScheme.dump_to_str
    """
    dump_res = AS().dump_to_str()
    assert dump_res == 'a=1,b=b,c=False'


class Post(BaseScheme):
    _id: FieldT[int] = field(dump_flags={"read_only",})
    created_by: FieldT[datetime.datetime] = field(dump_flags={"read_only",})
    title: FieldT[str] = field(dump_flags={"user_editable",})
    content: FieldT[str] = field(dump_flags={"user_editable",})

class PostEditable(Post,
    default_include_dump_flags={"user_editable",},
    default_exclude_dump_flags={"read_only",},
    partial=True
):
    extra_field: FieldT[int] = field(is_partial=False, dump_flags={"flag_a",})


def test_dump_flags():
    """Test BaseScheme.dump_* with flags options
    
    - exclude/include_flags
    - default_exclude/include_flags
    """
    pe = PostEditable(title="t", content="c", extra_field=0)
    
    # default exclude
    assert pe.dump_to_dict() == {
        "title": "t",
        "content": "c",
        "extra_field": 0
    }

    # default include
    assert pe.dump_to_dict(
        exclude_flags=set(),
    ) == {
        "title": "t",
        "content": "c",
    }

    # manually include
    assert pe.dump_to_dict(
        exclude_flags=set(),
        include_flags={"flag_a",}
    ) == {
        "extra_field": 0
    }

    # manually exclude
    assert pe.dump_to_dict(
        exclude_flags={"flag_a",}
    ) == {
        "title": "t",
        "content": "c"
        # created_by are partial
    }

    
