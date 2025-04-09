import unittest
import os
from unittest.mock import MagicMock, patch
import asyncio

from blue_firmament.main import BlueFirmamentApp
from blue_firmament.scheme import BaseScheme, Field
from blue_firmament.transport import TransportType, TransportOperationType
from blue_firmament.routing import Router
from blue_firmament.transport.request import CommonSesstionRequest, Request
from blue_firmament.transport.response import Response, JsonResponseBody
from blue_firmament.dal.filters import EqFilter
from blue_firmament.middleware import BaseMiddleware
from blue_firmament.session.common import CommonSession

# Test database configuration for PostgreSQL
TEST_POSTGRES_URL = os.environ.get('TEST_POSTGRES_URL', 'postgresql://test_user:test_password@localhost:5432/test_db')

# Define a test scheme for CRUD operations
class TestScheme(BaseScheme):
    _table_name = 'test_table'
    
    _id: int = Field(0, is_primary_key=True)
    name: str = 'default_name'
    description: str = ''
    
    @classmethod
    def get_primary_key(cls):
        return '_id'

class TestBlueFirmamentApp(unittest.TestCase):
    def setUp(self):
        """Set up before each test"""
        self.mock_router = MagicMock(spec=Router)
        patcher = patch('blue_firmament.transport.http.HTTPTransport')
        self.addCleanup(patcher.stop)
        patcher.start()
        self.app = BlueFirmamentApp(TransportType.HTTP, 'localhost', 8000, self.mock_router)

    def test_provide_crud_over_scheme_registers_routes(self):
        """Test that the decorator registers all CRUD routes"""
        # Apply decorator
        decorated_scheme = self.app.provide_crud_over_scheme('test')(TestScheme)
        
        # Verify that the decorated scheme is the same as the original
        self.assertIs(decorated_scheme, TestScheme)
        
        # Verify routes are registered
        self.assertEqual(self.mock_router.add_route_record.call_count, 5)  # All CRUD operations
        
        # Check for specific routes being registered
        route_calls = self.mock_router.add_route_record.call_args_list
        registered_routes = [(call[0][0], call[0][1]) for call in route_calls]
        
        expected_routes = [
            (TransportOperationType.GET, '/test/{id}'),
            (TransportOperationType.POST, '/test'),
            (TransportOperationType.PUT, '/test/{id}'),
            (TransportOperationType.PATCH, '/test/{id}'),
            (TransportOperationType.DELETE, '/test/{id}')
        ]
        
        for operation, route in expected_routes:
            self.assertTrue(any(op == operation and route in r for op, r in registered_routes))

    def test_provide_crud_with_disabled_operations(self):
        """Test that disabled operations don't get registered"""
        # Apply decorator with disabled operations
        disabled_ops = [TransportOperationType.GET, TransportOperationType.DELETE]
        decorated_scheme = self.app.provide_crud_over_scheme('test', disabled_operations=disabled_ops)(TestScheme)
        
        # Verify only non-disabled routes are registered (should be 3: POST, PUT, PATCH)
        self.assertEqual(self.mock_router.add_route_record.call_count, 3)
        
        # Check specific routes
        route_calls = self.mock_router.add_route_record.call_args_list
        registered_routes = [(call[0][0], call[0][1]) for call in route_calls]
        
        # These should be registered
        expected_routes = [
            (TransportOperationType.POST, '/test'),
            (TransportOperationType.PUT, '/test/{id}'),
            (TransportOperationType.PATCH, '/test/{id}')
        ]
        
        # These should NOT be registered
        not_expected_routes = [
            (TransportOperationType.GET, '/test/{id}'),
            (TransportOperationType.DELETE, '/test/{id}')
        ]
        
        for operation, route in expected_routes:
            self.assertTrue(any(op == operation and route in r for op, r in registered_routes))
            
        for operation, route in not_expected_routes:
            self.assertFalse(any(op == operation and route in r for op, r in registered_routes))


class TestHandlerFunctionality(unittest.TestCase):
    def test_get_handler_functionality(self):
        """Test the GET handler's functionality"""
        app = BlueFirmamentApp(TransportType.HTTP, 'localhost', 8000)
        handler = app.get_common_get_handler(TestScheme)
        
        # Create mock request with session
        request = MagicMock(spec=CommonSesstionRequest)
        request.session = MagicMock()  # Add mock for session
        request.session.dao = MagicMock()
        
        # Set up mock return value
        expected_result = TestScheme(_id=1, name="Test Item")
        request.session.dao.select_a_scheme_from_primary_key.return_value = expected_result
        
        # Call handler
        result = handler(request, 1)
        
        # Verify
        request.session.dao.select_a_scheme_from_primary_key.assert_called_once_with(TestScheme, 1)
        self.assertIs(result, expected_result)

    def test_post_handler_functionality(self):
        """Test the POST handler's functionality"""
        app = BlueFirmamentApp(TransportType.HTTP, 'localhost', 8000)
        handler = app.get_common_post_handler(TestScheme)
        
        # Create mock request with session
        request = MagicMock(spec=CommonSesstionRequest)
        request.session = MagicMock()  # Add mock for session
        request.session.dao = MagicMock()
        
        # Test data
        body = {"name": "New Item", "description": "Test description"}
        
        # Set up mock return value
        expected_result = TestScheme(_id=1, name="New Item", description="Test description")
        request.session.dao.insert.return_value = expected_result
        
        # Call handler
        result = handler(request, body)
        
        # Verify
        request.session.dao.insert.assert_called_once()
        self.assertIs(result, expected_result)

    def test_put_handler_functionality(self):
        """Test the PUT handler's functionality"""
        app = BlueFirmamentApp(TransportType.HTTP, 'localhost', 8000)
        handler = app.get_common_put_handler(TestScheme)
        
        # Create mock request with session
        request = MagicMock(spec=CommonSesstionRequest)
        request.session = MagicMock()  # Add mock for session
        request.session.dao = MagicMock()
        
        # Test data
        body = {"_id": 1, "name": "Updated Item", "description": "Updated description"}
        
        # Set up mock return value
        expected_result = TestScheme(**body)
        request.session.dao.update.return_value = expected_result
        
        # Call handler
        result = handler(request, 1, body)
        
        # Verify
        request.session.dao.update.assert_called_once()
        # Check that an EqFilter was used with the correct primary key
        filter_arg = request.session.dao.update.call_args[0][2]
        self.assertIsInstance(filter_arg, EqFilter)
        self.assertEqual(filter_arg.field, "_id")  # Primary key field
        self.assertEqual(filter_arg.value, 1)

    def test_patch_handler_functionality(self):
        """Test the PATCH handler's functionality"""
        app = BlueFirmamentApp(TransportType.HTTP, 'localhost', 8000)
        handler = app.get_common_patch_handler(TestScheme)
        
        # Create mock request with session
        request = MagicMock(spec=CommonSesstionRequest)
        request.session = MagicMock()  # Add mock for session
        request.session.dao = MagicMock()
        
        # Test partial update data
        body = {"name": "Partially Updated"}
        
        # Set up mock return value
        expected_result = TestScheme(_id=1, name="Partially Updated", description="")
        request.session.dao.update.return_value = expected_result
        
        # Call handler
        result = handler(request, 1, body)
        
        # Verify
        request.session.dao.update.assert_called_once()
        # Check that an EqFilter was used with the correct primary key
        filter_arg = request.session.dao.update.call_args[0][2]
        self.assertIsInstance(filter_arg, EqFilter)
        self.assertEqual(filter_arg.field, "_id")
        self.assertEqual(filter_arg.value, 1)

    def test_delete_handler_functionality(self):
        """Test the DELETE handler's functionality"""
        app = BlueFirmamentApp(TransportType.HTTP, 'localhost', 8000)
        handler = app.get_common_delete_handler(TestScheme)
        
        # Create mock request with session
        request = MagicMock(spec=CommonSesstionRequest)
        request.session = MagicMock()  # Add mock for session
        request.session.dao = MagicMock()
        
        # Set up mock return value
        expected_result = {"deleted": True}
        request.session.dao.delete_a_scheme.return_value = expected_result
        
        # Call handler
        result = handler(request, 1)
        
        # Verify
        request.session.dao.delete_a_scheme.assert_called_once_with(TestScheme, 1)
        self.assertIs(result, expected_result)


class TestAsyncFunctionality(unittest.TestCase):
    def test_handle_request(self):
        """Test the handle_request method"""
        # Create app with mock router
        mock_router = MagicMock()
        app = BlueFirmamentApp(TransportType.HTTP, 'localhost', 8000, mock_router)
        
        # Create mock request and response
        mock_request = MagicMock(spec=Request)
        mock_request.route_key = "/test/1"
        mock_response = MagicMock(spec=Response)
        
        # Mock route record and middleware behavior
        mock_route_record = MagicMock(spec=BaseMiddleware)
        mock_route_record.__call__ = MagicMock()
        
        # Setup router to return our mock record
        mock_router.routing.return_value = (mock_route_record, {"id": "1"})
        
        # Patch the BaseMiddleware.get_next to avoid complex middleware chain
        with patch('blue_firmament.middleware.BaseMiddleware.get_next') as mock_get_next:
            mock_next = MagicMock()
            mock_get_next.return_value = mock_next
            
            # Use asyncio to run the coroutine
            asyncio.run(app.handle_request(mock_request, mock_response))
            
            # Verify
            mock_router.routing.assert_called_once_with(mock_request.route_key)
            mock_get_next.assert_called_once()
            
            # Verify correct parameters were passed to the middleware
            mock_route_record.assert_called_once()
            call_kwargs = mock_route_record.call_args[1]
            self.assertEqual(call_kwargs['request'], mock_request)
            self.assertEqual(call_kwargs['response'], mock_response)
            self.assertEqual(call_kwargs['path_params'], {"id": "1"})
            self.assertEqual(call_kwargs['next'], mock_next)


class TestIntegration(unittest.TestCase):
    @unittest.skipIf(not TEST_POSTGRES_URL, "TEST_POSTGRES_URL not configured")
    def test_postgres_configuration(self):
        """Test the PostgreSQL configuration for the testing environment"""
        # Ensure the test PostgreSQL URL is configured
        self.assertTrue(TEST_POSTGRES_URL, "TEST_POSTGRES_URL environment variable should be set")
        
        # For a real integration test, you would:
        # 1. Create a test database connection
        # 2. Set up test tables
        # 3. Register a scheme with the app
        # 4. Test actual CRUD operations
        
        # This is a placeholder to verify the URL is available
        self.assertIn("postgresql://", TEST_POSTGRES_URL)


if __name__ == '__main__':
    unittest.main()
