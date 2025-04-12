import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import typing

from blue_firmament.manager import BaseManager
from blue_firmament.main import BlueFirmamentApp
from blue_firmament.session import Session
from blue_firmament.scheme import BaseScheme


class TestScheme(BaseScheme):
    """Test scheme class for testing purposes."""
    pass


class TestSession(Session):
    """Test session class for testing purposes."""
    
    def __init__(self):
        self.dao = MagicMock()


class TestManager(BaseManager[TestScheme, TestSession]):
    """Test manager class for testing purposes."""
    
    __SCHEME_CLS__ = TestScheme
    __name__ = 'test_manager'


class TestBaseManager(unittest.TestCase):
    
    def setUp(self):
        self.session = TestSession()
        self.manager = TestManager(self.session)
        self.test_scheme = TestScheme()
        
    def test_init(self):
        """Test manager initialization."""
        self.assertEqual(self.manager.session, self.session)
        
    def test_set_scheme(self):
        """Test setting scheme."""
        self.manager.set_scheme(self.test_scheme)
        
    @patch('blue_firmament.manager.typing.cast', return_value=MagicMock())
    async def test_get_scheme_without_setter(self, mock_cast):
        """Test getting scheme when it's not set and no primary key provided."""
        with self.assertRaises(ValueError):
            await self.manager.get_scheme()
            
    @patch('blue_firmament.manager.typing.cast', return_value=MagicMock())
    async def test_get_scheme_with_primary_key(self, mock_cast):
        """Test getting scheme using primary key."""
        primary_key = "test_key"
        mock_dao = MagicMock()
        mock_cast.return_value = mock_dao
        mock_dao.select_a_scheme_from_primary_key = AsyncMock(return_value=self.test_scheme)
        
        result = await self.manager.get_scheme(from_primary_key=primary_key)
        
        mock_cast.assert_called_once()
        mock_dao.select_a_scheme_from_primary_key.assert_called_once_with(
            TestScheme, primary_key
        )
        self.assertEqual(result, self.test_scheme)
        
    async def test_get_scheme_after_setter(self):
        """Test getting scheme after it has been set."""
        self.manager.set_scheme(self.test_scheme)
        result = await self.manager.get_scheme()
        self.assertEqual(result, self.test_scheme)
        
    def test_get_route_record_register(self):
        """Test getting route record register."""
        app_mock = MagicMock(spec=BlueFirmamentApp)
        router_mock = MagicMock()
        app_mock.router = router_mock
        
        TestManager.get_route_record_register(app_mock)
        
        router_mock.get_manager_handler_route_record_register.assert_called_once_with(
            manager=TestManager, use_manager_name_as_prefix=True
        )


if __name__ == '__main__':
    unittest.main()