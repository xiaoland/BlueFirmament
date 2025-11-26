"""Tests for model.main
"""

import datetime
from blue_firmament.model.main import BaseModel
from blue_firmament.model import field, Field
from blue_firmament.model.converter import ModelConverter


# Using Model prefix to avoid pytest collecting this as a test class
class ExampleModel(BaseModel):
    a: int = 1
    b: str = 'b'
    c: bool = False

def test_str_representation():
    """Test BaseModel.__str__ via str()
    """
    dump_res = str(ExampleModel())
    assert dump_res == 'a=1,b=b,c=False'


def test_dict_representation():
    """Test BaseModel.__dict__ via dict()
    """
    model = ExampleModel()
    dump_res = dict(model)
    assert dump_res == {'a': 1, 'b': 'b', 'c': False}

def test_dump_flags():
    """Test ModelConverter field masks
    
    - Using field masks instead of flags
    - Using mask presets
    """
    class Post(BaseModel):
        _id: Field[int] = field()
        created_by: Field[datetime.datetime] = field()
        title: Field[str] = field()
        content: Field[str] = field()

    pe = Post(_id=1, title="t", content="c", created_by=datetime.datetime.now())
    
    # Create a converter with mask presets
    from blue_firmament.model.converter import ModelConverter
    converter = ModelConverter(Post)
    
    # Register presets for different use cases
    converter.register_mask_preset("user_editable", (
        Post.title,
        Post.content
    ))
    converter.register_mask_preset("read_only", (
        Post._id,
        Post.created_by
    ))
    
    # Use preset to get only user_editable fields
    result = converter.dump_to_dict(pe, mask_preset="user_editable")
    assert "title" in result
    assert "content" in result
    assert "_id" not in result
    assert "created_by" not in result
    
    # Use preset to get only read_only fields
    result = converter.dump_to_dict(pe, mask_preset="read_only")
    assert "_id" in result
    assert "created_by" in result
    assert "title" not in result
    assert "content" not in result
    
    # Use fields tuple directly (no preset)
    result = converter.dump_to_dict(pe, fields=(Post.title,))
    assert "title" in result
    assert "content" not in result
    assert "_id" not in result


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
