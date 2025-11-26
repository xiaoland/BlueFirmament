"""Tests for LoggedModel
"""

from blue_firmament.model import LoggedModel, field


def test_logged_model_basic():
    """Test LoggedModel basic functionality"""
    
    class User(LoggedModel):
        name: str = "test"
        email: str = "test@example.com"
    
    # Should instantiate without errors and log
    user = User(name="John", email="john@example.com")
    assert user.name == "John"
    assert user.email == "john@example.com"
    
    # Should have logger
    assert user._logger is not None


def test_logged_model_disable_log():
    """Test LoggedModel with disable_log"""
    
    class Admin(LoggedModel, disable_log=True):
        username: str = "admin"
        role: str = "administrator"
    
    admin = Admin(username="root", role="superadmin")
    assert admin.username == "root"
    assert admin.role == "superadmin"
    
    # Should still have logger even if disabled
    assert admin._logger is not None
