"""Tests for model.main
"""

import datetime
from blue_firmament.model.main import BaseModel
from blue_firmament.model import field, Field


# Using Model prefix to avoid pytest collecting this as a test class
class ExampleModel(BaseModel):
    a: int = 1
    b: str = 'b'
    c: bool = False

def test_dump_to_str():
    """Test BaseModel.dump_to_str
    """
    dump_res = ExampleModel().dump_to_str()
    assert dump_res == 'a=1,b=b,c=False'

def test_dump_flags():
    """Test BaseModel.dump_* with flags options
    
    - exclude/include_flags
    - default_exclude/include_flags
    """
    class Post(BaseModel):
        _id: Field[int] = field(dump_flags={"read_only", })
        created_by: Field[datetime.datetime] = field(dump_flags={"read_only", })
        title: Field[str] = field(dump_flags={"user_editable", })
        content: Field[str] = field(dump_flags={"user_editable", })

    class PostEditable(Post,
                       default_include_dump_flags={"user_editable", },
                       default_exclude_dump_flags={"read_only", },
                       partial=True
                       ):
        extra_field: Field[int] = field(is_partial=False, dump_flags={"flag_a", })

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


def test_inheritance():

    # one inherit
    class A(BaseModel):
        a: int = 1

    class B(BaseModel):
        b: str = 'b'

    class C(A, B):
        c: bool = False
        b: str = "c's b"

    c = C()
    assert c.a == 1
    assert c.b == "c's b"
    assert c.c is False

    # multi inherit
