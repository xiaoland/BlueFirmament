"""Tests for LoggedModel
"""

from blue_firmament.log import LoggedModel


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
    assert user.__logger__ is not None


def test_logged_model_custom_logger_factory():
    """Test LoggedModel with custom logger factory"""
    
    # Create a custom logger factory
    def custom_factory(name):
        from blue_firmament.log import get_logger
        logger = get_logger(name)
        return logger.bind(custom_field="test_value")
    
    class Admin(LoggedModel, logger_factory=custom_factory):
        username: str = "admin"
        role: str = "administrator"
    
    admin = Admin(username="root", role="superadmin")
    assert admin.username == "root"
    assert admin.role == "superadmin"
    
    # Should have logger
    assert admin.__logger__ is not None
