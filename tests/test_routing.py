import unittest
from blue_firmament.routing import RouteKey
from blue_firmament.transport import TransportOperationType
from blue_firmament.scheme.validator import BaseValidator
from blue_firmament.routing import RouteRecord, Router


class TestRouteKey(unittest.TestCase):
    """Tests for the RouteKey class in the routing module
    
    Pass means
    ^^^
    - RouteKey initialization
    - RouteKey equality
    - RouteKey segment matching
    - RouteKey string representation
    """

    def test_initialization(self):

        """Test initializing RouteKey with different parameters
        
        Pass means
        ^^^
        - RouteKey with no parameters
        - RouteKey with parameters
        - RouteKey with wildcard operation
        """

        # Simple route with no parameters
        route_key = RouteKey(TransportOperationType.GET, '/users')
        self.assertEqual(TransportOperationType.GET, route_key.operation)
        self.assertEqual('/users/', route_key.path)
        self.assertEqual(['users'], route_key.segments)
        self.assertFalse(route_key.has_parameters)

        # Route with parameters
        route_key = RouteKey(TransportOperationType.POST, '/users/{id}')
        self.assertEqual(TransportOperationType.POST, route_key.operation)
        self.assertEqual('/users/{id}/', route_key.path)
        self.assertEqual(['users', '{id}'], route_key.segments)
        self.assertTrue(route_key.has_parameters)

        # Route with wildcard operation
        route_key = RouteKey(None, '/posts')
        self.assertIsNone(route_key.operation)
        self.assertEqual('/posts/', route_key.path)

    def test_equality(self):

        """Test equality comparison between RouteKey instances"""

        # Same routes should be equal
        route1 = RouteKey(TransportOperationType.GET, '/users')
        route2 = RouteKey(TransportOperationType.GET, '/users')
        self.assertEqual(route1, route2)

        # Different operations make routes not equal
        route3 = RouteKey(TransportOperationType.POST, '/users')
        self.assertNotEqual(route1, route3)

        # Different paths make routes not equal
        route4 = RouteKey(TransportOperationType.GET, '/posts')
        self.assertNotEqual(route1, route4)

        # Wildcard operation matches any operation
        route5 = RouteKey(None, '/users')
        self.assertEqual(route5, route1)  # Wildcard should match GET
        self.assertEqual(route5, route3)  # Wildcard should match POST
        
        # Different number of segments shouldn't match
        route6 = RouteKey(TransportOperationType.GET, '/users/profile')
        self.assertNotEqual(route1, route6)
        
        # Test routes with parameters
        param_route1 = RouteKey(TransportOperationType.GET, '/users/{id}')
        param_route2 = RouteKey(TransportOperationType.GET, '/users/{id}')
        self.assertEqual(param_route1, param_route2)
        
        # Different parameter names but same position should still match
        param_route3 = RouteKey(TransportOperationType.GET, '/users/{user_id}')
        self.assertEqual(param_route1, param_route3)
        
        # Parameter position matters
        param_route4 = RouteKey(TransportOperationType.GET, '/{resource}/id')
        self.assertNotEqual(param_route1, param_route4)
        
        # Wildcard with parameters
        wildcard_param = RouteKey(None, '/users/{id}')
        self.assertEqual(wildcard_param, param_route1)

    def test_segment_matching(self):
        """Test matching of segments in routes"""
        # Route with static segments
        static_route = RouteKey(TransportOperationType.GET, '/api/users')
        
        # Test the private method __is_segment_match through direct comparison
        # Create a route with the same path for comparison
        same_route = RouteKey(TransportOperationType.GET, '/api/users')
        self.assertEqual(static_route, same_route)
        
        # Test with different segments
        different_route = RouteKey(TransportOperationType.GET, '/api/posts')
        self.assertNotEqual(static_route, different_route)

    def test_string_representation(self):
        """Test string representation of RouteKey"""
        route_key = RouteKey(TransportOperationType.GET, '/users')
        self.assertEqual(f"{TransportOperationType.GET} /users/", str(route_key))

    def test_hash(self):
        """Test hashing of RouteKey for use in dictionaries"""
        route_key = RouteKey(TransportOperationType.GET, '/users/list')
        # Hash should be based on operation and path
        expected_hash = hash((TransportOperationType.GET, 'users', 'list'))
        self.assertEqual(expected_hash, hash(route_key))

        # Same route keys should have the same hash
        route_key2 = RouteKey(TransportOperationType.GET, '/users/list/')
        self.assertEqual(hash(route_key), hash(route_key2))

        # Different route keys should have different hashes
        route_key3 = RouteKey(TransportOperationType.POST, '/users/list2')
        self.assertNotEqual(hash(route_key), hash(route_key3))

    def test_resolve_params(self):
        """Test resolving parameters from path segments
        
        Pass means:
        ^^^
        - Basic parameter resolution works
        - Parameters are validated according to their types
        - Missing parameters are handled correctly
        - Multiple parameters can be resolved
        """
        # Basic parameter resolution
        route_key = RouteKey(TransportOperationType.GET, '/users/{id}')
        params = route_key.resolve_params(['users', '123'])
        self.assertEqual({'id': '123'}, params)
        
        # Parameter validation with types
        route_key_with_types = RouteKey(
            TransportOperationType.GET, 
            '/users/{id}', 
            param_types={'id': int}
        )
        params = route_key_with_types.resolve_params(['users', '123'])
        self.assertEqual({'id': 123}, params)  # Should be converted to int
        
        # Invalid parameter type
        params = route_key_with_types.resolve_params(['users', 'abc'])
        self.assertIsNone(params['id'])  # Should be None since 'abc' is not a valid int
        
        # Missing parameter
        params = route_key.resolve_params(['users'])
        self.assertIsNone(params['id'])  # Should be None when parameter is missing
        
        # Multiple parameters
        multi_param_route = RouteKey(
            TransportOperationType.GET, 
            '/users/{user_id}/posts/{post_id}',
            param_types={'user_id': int, 'post_id': str}
        )
        params = multi_param_route.resolve_params(['users', '42', 'posts', 'trending'])
        self.assertEqual({'user_id': 42, 'post_id': 'trending'}, params)
        
        # Mixed valid and invalid parameters
        params = multi_param_route.resolve_params(['users', 'invalid', 'posts', 'trending'])
        self.assertIsNone(params['user_id'])
        self.assertEqual('trending', params['post_id'])

    def test_is_match(self):
        """Test the is_match method for comparing and extracting parameters from RouteKeys
        
        Pass means:
        ^^^
        - Basic matching works for non-parameterized routes
        - Parameter extraction works for parameterized routes
        - Type validation works during matching
        - Operation wildcards are properly handled
        - Non-RouteKey objects are rejected
        """
        # Static routes matching
        static_route1 = RouteKey(TransportOperationType.GET, '/users')
        static_route2 = RouteKey(TransportOperationType.GET, '/users')
        match_result, params = static_route1.is_match(static_route2)
        self.assertTrue(match_result)
        self.assertIsNone(params)
        
        # Different static routes don't match
        static_route3 = RouteKey(TransportOperationType.GET, '/posts')
        match_result, params = static_route1.is_match(static_route3)
        self.assertFalse(match_result)
        self.assertIsNone(params)
        
        # Parameterized route matching with parameter extraction
        param_route1 = RouteKey(TransportOperationType.GET, '/users/{id}')
        param_route2 = RouteKey(TransportOperationType.GET, '/users/123')
        match_result, params = param_route1.is_match(param_route2)
        self.assertTrue(match_result)
        self.assertEqual({'id': '123'}, params)
        
        # Parameterized route with type validation
        typed_param_route = RouteKey(
            TransportOperationType.GET, 
            '/users/{id}', 
            param_types={'id': int}
        )
        match_result, params = typed_param_route.is_match(param_route2)
        self.assertTrue(match_result)
        self.assertEqual({'id': 123}, params)  # Should be converted to int
        
        # Type validation failure
        invalid_route = RouteKey(TransportOperationType.GET, '/users/abc')
        match_result, params = typed_param_route.is_match(invalid_route)
        self.assertFalse(match_result)
        self.assertIsNone(params)
        
        # Operation wildcard matching
        wildcard_route = RouteKey(None, '/users')
        post_route = RouteKey(TransportOperationType.POST, '/users')
        match_result, params = wildcard_route.is_match(post_route)
        self.assertTrue(match_result)
        self.assertIsNone(params)
        
        # Multiple parameters
        multi_param_route = RouteKey(
            TransportOperationType.GET, 
            '/users/{user_id}/posts/{post_id}',
            param_types={'user_id': int, 'post_id': str}
        )
        target_route = RouteKey(TransportOperationType.GET, '/users/42/posts/trending')
        match_result, params = multi_param_route.is_match(target_route)
        self.assertTrue(match_result)
        self.assertEqual({'user_id': 42, 'post_id': 'trending'}, params)
        
        # Non-RouteKey object
        match_result, params = static_route1.is_match("not a route key")
        self.assertFalse(match_result)
        self.assertIsNone(params)




class TestRouteRecord(unittest.TestCase):
    """Tests for the RouteRecord class in the routing module
    
    Pass means:
    - RouteRecord initialization
    - RouteRecord equality
    - RouteRecord is_key_match
    - RouteRecord is_mapping_to_router property
    """
    
    def test_initialization(self):
        """Test initializing RouteRecord with different targets"""
        # Handler function
        def dummy_handler(request, params):
            return {"status": "success"}
        
        route_key = RouteKey(TransportOperationType.GET, '/users')
        record = RouteRecord(route_key, dummy_handler)
        
        self.assertEqual(route_key, record.route_key)
        self.assertEqual(dummy_handler, record.target)
        self.assertFalse(record.is_mapping_to_router)
        
        # Router target
        router = Router()
        router_record = RouteRecord(route_key, router)
        
        self.assertEqual(route_key, router_record.route_key)
        self.assertEqual(router, router_record.target)
        self.assertTrue(router_record.is_mapping_to_router)
    
    def test_equality(self):
        """Test equality comparison between RouteRecord instances and RouteKeys"""
        def dummy_handler(request, params):
            return {"status": "success"}
        
        route_key1 = RouteKey(TransportOperationType.GET, '/users')
        route_key2 = RouteKey(TransportOperationType.GET, '/users')
        route_key3 = RouteKey(TransportOperationType.POST, '/users')
        
        record1 = RouteRecord(route_key1, dummy_handler)
        record2 = RouteRecord(route_key2, dummy_handler)
        record3 = RouteRecord(route_key3, dummy_handler)
        
        # Same route key should make records equal
        self.assertEqual(record1, record2)
        
        # Different route keys should make records not equal
        self.assertNotEqual(record1, record3)
        
        # RouteRecord equals RouteKey if keys match
        self.assertEqual(record1, route_key1)
        self.assertEqual(record1, route_key2)
        self.assertNotEqual(record1, route_key3)
        
        # Non-RouteKey and non-RouteRecord objects should not be equal
        self.assertNotEqual(record1, "not a route record")
    
    def test_is_key_match(self):
        """Test matching route keys against records"""
        def dummy_handler(request, params):
            return {"status": "success"}
        
        # Static routes
        static_key = RouteKey(TransportOperationType.GET, '/users')
        static_record = RouteRecord(static_key, dummy_handler)
        
        matching_key = RouteKey(TransportOperationType.GET, '/users')
        non_matching_key = RouteKey(TransportOperationType.POST, '/users')
        
        is_match, params = static_record.is_key_match(matching_key)
        self.assertTrue(is_match)
        self.assertIsNone(params)
        
        is_match, params = static_record.is_key_match(non_matching_key)
        self.assertFalse(is_match)
        self.assertIsNone(params)
        
        # Parameterized routes
        param_key = RouteKey(
            TransportOperationType.GET, 
            '/users/{id}',
            param_types={'id': int}
        )
        param_record = RouteRecord(param_key, dummy_handler)
        
        param_matching_key = RouteKey(TransportOperationType.GET, '/users/123')
        param_non_matching_key = RouteKey(TransportOperationType.GET, '/users/abc')
        
        is_match, params = param_record.is_key_match(param_matching_key)
        self.assertTrue(is_match)
        self.assertEqual({'id': 123}, params)
        
        is_match, params = param_record.is_key_match(param_non_matching_key)
        self.assertFalse(is_match)
        self.assertIsNone(params)
    
    def test_hash(self):
        """Test hashing of RouteRecord for use in sets and dictionaries"""
        def dummy_handler(request, params):
            return {"status": "success"}
        
        route_key = RouteKey(TransportOperationType.GET, '/users')
        record = RouteRecord(route_key, dummy_handler)
        
        # Hash should be based on route_key's hash
        self.assertEqual(hash(route_key), hash(record))
        
        # Same route records should have the same hash
        route_key2 = RouteKey(TransportOperationType.GET, '/users')
        record2 = RouteRecord(route_key2, dummy_handler)
        self.assertEqual(hash(record), hash(record2))
        
        # Different route records should have different hashes
        route_key3 = RouteKey(TransportOperationType.POST, '/users')
        record3 = RouteRecord(route_key3, dummy_handler)
        self.assertNotEqual(hash(record), hash(record3))


class TestRouter(unittest.TestCase):
    """Tests for the Router class in the routing module
    
    Pass means:
    - Router initialization
    - Adding route records
    - Routing requests to handlers
    - Routing requests to nested routers
    - Handling parameter extraction
    - Leave_node functionality
    """
    
    def setUp(self):
        """Set up common test fixtures"""
        self.router = Router()
        
        # Define handlers for testing
        self.users_handler = lambda request, params: {"resource": "users"}
        self.user_detail_handler = lambda request, params: {"resource": "user", "id": params.get("id")}
        self.posts_handler = lambda request, params: {"resource": "posts"}
        
        # Add some routes
        self.router.add_route_record(TransportOperationType.GET, '/users', self.users_handler)
        self.router.add_route_record(
            TransportOperationType.GET, 
            '/users/{id}', 
            self.user_detail_handler
        )
        self.router.add_route_record(TransportOperationType.GET, '/posts', self.posts_handler)
    
    def test_initialization(self):
        """Test initializing a Router"""
        router = Router()
        # Newly initialized router should have empty records
        self.assertEqual(0, len(router._Router__records))
    
    def test_add_route_record(self):
        """Test adding route records to a router"""
        router = Router()
        
        # Add a route record
        handler = lambda request, params: {"status": "success"}
        router.add_route_record(TransportOperationType.GET, '/test', handler)
        
        # Router should have one record
        self.assertEqual(1, len(router._Router__records))
        
        # The record should have the correct key and target
        record = router._Router__records[0]
        self.assertEqual(TransportOperationType.GET, record.route_key.operation)
        self.assertEqual('/test/', record.route_key.path)
        self.assertEqual(handler, record.target)
    
    def test_routing_basic(self):
        """Test basic routing to handlers"""
        # Route to users handler
        route_key = RouteKey(TransportOperationType.GET, '/users')
        record, params = self.router.routing(route_key)
        
        self.assertIsNotNone(record)
        self.assertEqual(self.users_handler, record.target)
        self.assertIsNone(params)  # No parameters for this route
        
        # Route to posts handler
        route_key = RouteKey(TransportOperationType.GET, '/posts')
        record, params = self.router.routing(route_key)
        
        self.assertIsNotNone(record)
        self.assertEqual(self.posts_handler, record.target)
        self.assertIsNone(params)
    
    def test_routing_with_parameters(self):
        """Test routing with parameter extraction"""
        # Route to user detail handler with parameter
        route_key = RouteKey(TransportOperationType.GET, '/users/123')
        record, params = self.router.routing(route_key)
        
        self.assertIsNotNone(record)
        self.assertEqual(self.user_detail_handler, record.target)
        self.assertEqual({'id': '123'}, params)
        
        # Invoke the handler with extracted parameters
        result = self.user_detail_handler(None, params)
        self.assertEqual({'resource': 'user', 'id': '123'}, result)
    
    def test_routing_no_match(self):
        """Test routing with no matching route"""
        # Non-existent route
        route_key = RouteKey(TransportOperationType.GET, '/nonexistent')
        with self.assertRaises(KeyError):
            self.router.routing(route_key)
        
        # Wrong HTTP method
        route_key = RouteKey(TransportOperationType.POST, '/users')
        with self.assertRaises(KeyError):
            self.router.routing(route_key)
    
    def test_routing_to_nested_router(self):
        """Test routing to a nested router"""
        # Create a nested router
        nested_router = Router()
        nested_handler = lambda request, params: 'here'
        
        nested_router.add_route_record(
            TransportOperationType.GET, 
            '/profile', 
            nested_handler
        )
        
        # Add the nested router to the main router
        self.router.add_route_record(
            TransportOperationType.GET, 
            '/users/{id}/details', 
            nested_router
        )
        
        # Route to the nested handler through the parent router
        route_key = RouteKey(TransportOperationType.GET, '/users/42/details/profile')
        record, params = self.router.routing(route_key)
        
        self.assertIsNotNone(record)
        self.assertEqual({'id': '42'}, params)
        self.assertEqual(record.target(None, params), 'here')
    
    def test_routing_leave_node_false(self):
        """Test routing with leave_node=False"""
        # Create a nested router
        nested_router = Router()
        nested_handler = lambda request, params: {"nested": True}
        
        nested_router.add_route_record(
            TransportOperationType.GET, 
            '/resource', 
            nested_handler
        )
        
        # Add the nested router to the main router
        self.router.add_route_record(
            TransportOperationType.GET, 
            '/api', 
            nested_router
        )
        
        # With leave_node=True (default), we should get the nested handler
        route_key = RouteKey(TransportOperationType.GET, '/api/resource')
        record, params = self.router.routing(route_key, leaf_node=True)
        
        self.assertIsNotNone(record)
        self.assertEqual(nested_handler, record.target)
        
        # With leave_node=False, we should get the router record
        record, params = self.router.routing(route_key, leaf_node=False)
        
        self.assertIsNotNone(record)
        self.assertTrue(record.is_mapping_to_router)
        self.assertEqual(nested_router, record.target)
        
        # Test non-existent route with leaf_node=False
        route_key = RouteKey(TransportOperationType.GET, '/nonexistent')
        with self.assertRaises(KeyError):
            self.router.routing(route_key, leaf_node=False)


if __name__ == '__main__':
    unittest.main()
