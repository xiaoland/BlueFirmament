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
    
    # Test dump_model_to_dict
    result = converter.dump_model_to_dict(user)
    assert result == {"id": 42, "name": "Bob", "email": "bob@example.com"}
    
    # Test dump_model_to_str
    result_str = converter.dump_model_to_str(user)
    assert "id=42" in result_str
    assert "name=Bob" in result_str
    assert "email=bob@example.com" in result_str


def test_model_converter_with_flags():
    """Test ModelConverter handles dump_flags correctly."""
    
    class Post(BaseModel):
        id: Field[int] = field(dump_flags={"read_only"})
        title: Field[str] = field(dump_flags={"user_editable"})
        content: Field[str] = field(dump_flags={"user_editable"})
        internal_note: Field[str] = field(dump_flags={"admin_only"})
    
    post = Post(id=1, title="Hello", content="World", internal_note="Secret")
    
    converter = ModelConverter(Post)
    
    # Exclude read_only fields
    result = converter.dump_model_to_dict(post, exclude_flags={"read_only"})
    assert "id" not in result
    assert "title" in result
    assert "content" in result
    assert "internal_note" in result
    
    # Include only user_editable fields
    result = converter.dump_model_to_dict(post, include_flags={"user_editable"})
    assert "id" not in result
    assert "title" in result
    assert "content" in result
    assert "internal_note" not in result


def test_backward_compatibility():
    """Test that BaseModel.dump_to_dict still works (delegates to ModelConverter)."""
    
    class Product(BaseModel):
        id: int = 1
        name: str = "Widget"
        price: float = 9.99
    
    product = Product(id=100, name="Gadget", price=19.99)
    
    # Old API should still work
    result = product.dump_to_dict()
    assert result == {"id": 100, "name": "Gadget", "price": 19.99}
    
    result_str = product.dump_to_str()
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
    result = converter.dump_model_to_dict(data)
    assert "field_a" in result
    assert "field_b" in result
    assert "field_c" not in result  # unset field excluded
    
    # Can explicitly include unset fields
    result = converter.dump_model_to_dict(data, exclude_unset=False)
    assert "field_a" in result
    assert "field_b" in result
    assert "field_c" in result  # unset field included
