"""Tests for ModelConverter serialization features

These tests demonstrate that serialization logic has been moved to ModelConverter
while maintaining backward compatibility through BaseModel delegation.
"""

from blue_firmament.model import BaseModel, field, Field
from blue_firmament.model.converter import ModelConverter


def test_model_converter_direct_usage():
    """Test ModelConverter can be used directly for serialization."""
    
    class User(BaseModel):
        id: int = 1
        name: str = "Alice"
        email: str = "alice@example.com"
    
    user = User(id=42, name="Bob", email="bob@example.com")
    
    # Create a converter and use it directly
    converter = ModelConverter(User)
    
    # Test dump_to_dict
    result = converter.dump_to_dict(user)
    assert result == {"id": 42, "name": "Bob", "email": "bob@example.com"}
    
    # Test dump_to_str
    result_str = converter.dump_to_str(user)
    assert "id=42" in result_str
    assert "name=Bob" in result_str
    assert "email=bob@example.com" in result_str


def test_model_converter_with_flags():
    """Test ModelConverter handles field masks correctly."""
    
    class Post(BaseModel):
        id: int
        title: str
        content: str
        internal_note: str
    
    post = Post(id=1, title="Hello", content="World", internal_note="Secret")
    
    converter = ModelConverter(Post)
    
    # Register mask presets
    converter.register_mask_preset("public", (Post.id, Post.title, Post.content))
    converter.register_mask_preset("user_editable", (Post.title, Post.content))
    
    # Use preset to get only public fields
    result = converter.dump_to_dict(post, mask_preset="public")
    assert "id" in result
    assert "title" in result
    assert "content" in result
    assert "internal_note" not in result
    
    # Use preset to get only user_editable fields
    result = converter.dump_to_dict(post, mask_preset="user_editable")
    assert "id" not in result
    assert "title" in result
    assert "content" in result
    assert "internal_note" not in result
    
    # Use fields tuple directly
    result = converter.dump_to_dict(post, fields=(Post.title,))
    assert "id" not in result
    assert "title" in result
    assert "content" not in result
    assert "internal_note" not in result


def test_dict_and_str_conversion():
    """Test that dict(model) and str(model) work correctly."""
    
    class Product(BaseModel):
        id: int = 1
        name: str = "Widget"
        price: float = 9.99
    
    product = Product(id=100, name="Gadget", price=19.99)
    
    # dict(model) should work via __dict__
    result = dict(product)
    assert result == {"id": 100, "name": "Gadget", "price": 19.99}
    
    # str(model) should work via __str__
    result_str = str(product)
    assert "id=100" in result_str
    assert "name=Gadget" in result_str
    assert "price=19.99" in result_str


def test_model_converter_exclude_unset():
    """Test ModelConverter handles exclude_unset for partial models."""
    
    class PartialData(BaseModel, partial=True):
        field_a: int
        field_b: str
        field_c: bool
    
    # Only set field_a and field_b
    data = PartialData(field_a=42, field_b="test")
    
    converter = ModelConverter(PartialData)
    
    # By default, partial models exclude unset fields
    result = converter.dump_to_dict(data)
    assert "field_a" in result
    assert "field_b" in result
    assert "field_c" not in result  # unset field excluded
    
    # Can explicitly include unset fields
    result = converter.dump_to_dict(data, exclude_unset=False)
    assert "field_a" in result
    assert "field_b" in result
    assert "field_c" in result  # unset field included
