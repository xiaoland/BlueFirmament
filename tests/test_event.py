"""Tests of Event system."""

import asyncio
import pytest
from blue_firmament.event import (
    Event,
    EventID,
    EventBus,
    EventSource,
    BaseMiddleware,
)


class TestEventID:
    """Tests for EventID."""

    def test_create_event_id(self):
        """Test creating an EventID."""
        event_id = EventID(path="user.created")
        assert event_id.path == "user.created"
        assert event_id.separator == "."
        assert event_id.segments == ["user", "created"]

    def test_event_id_equality(self):
        """Test EventID equality."""
        id1 = EventID(path="user.created")
        id2 = EventID(path="user.created")
        id3 = EventID(path="user.deleted")

        assert id1 == id2
        assert id1 != id3
        assert id1 == "user.created"

    def test_event_id_hash(self):
        """Test EventID hashing."""
        id1 = EventID(path="user.created")
        id2 = EventID(path="user.created")

        assert hash(id1) == hash(id2)

        # Can be used in sets
        s = {id1, id2}
        assert len(s) == 1

    def test_event_id_matches_exact(self):
        """Test exact pattern matching."""
        event_id = EventID(path="user.created")

        assert event_id.matches("user.created") is True
        assert event_id.matches("user.deleted") is False

    def test_event_id_matches_wildcard(self):
        """Test single wildcard pattern matching."""
        event_id = EventID(path="user.created")

        assert event_id.matches("user.*") is True
        assert event_id.matches("*.created") is True
        assert event_id.matches("order.*") is False

    def test_event_id_matches_double_wildcard(self):
        """Test double wildcard pattern matching."""
        event_id = EventID(path="user.profile.updated")

        assert event_id.matches("user.**") is True
        assert event_id.matches("**") is True
        assert event_id.matches("user.profile.**") is True
        assert event_id.matches("order.**") is False


class TestEvent:
    """Tests for Event."""

    def test_create_event(self):
        """Test creating an Event."""
        event = Event.create(
            path="user.created",
            parameters={"user_id": 123},
            metadata={"source": "test"},
        )

        assert event.id.path == "user.created"
        assert event.parameters == {"user_id": 123}
        assert event.metadata == {"source": "test"}
        assert event.trace_id is not None

    def test_event_str(self):
        """Test Event string representation."""
        event = Event.create(path="user.created")
        s = str(event)

        assert "user.created" in s
        assert "trace=" in s


class TestEventBus:
    """Tests for EventBus."""

    @pytest.mark.asyncio
    async def test_emit_with_handler(self):
        """Test emitting an event with a registered handler."""
        bus = EventBus(name="test")
        received_events = []

        @bus.on(r"user\..*")
        async def handle_user_events(event: Event):
            received_events.append(event)

        event = Event.create(path="user.created", parameters={"id": 1})
        await bus.emit(event)

        assert len(received_events) == 1
        assert received_events[0].parameters == {"id": 1}

    @pytest.mark.asyncio
    async def test_emit_no_matching_handler(self):
        """Test emitting an event with no matching handlers."""
        bus = EventBus(name="test")
        received_events = []

        @bus.on(r"order\..*")
        async def handle_order_events(event: Event):
            received_events.append(event)

        event = Event.create(path="user.created", parameters={"id": 1})
        await bus.emit(event)

        assert len(received_events) == 0

    @pytest.mark.asyncio
    async def test_emit_multiple_handlers(self):
        """Test emitting an event to multiple handlers."""
        bus = EventBus(name="test")
        results = []

        @bus.on(r"user\.created")
        async def handler1(event: Event):
            results.append("handler1")

        @bus.on(r"user\..*")
        async def handler2(event: Event):
            results.append("handler2")

        event = Event.create(path="user.created")
        await bus.emit(event)

        assert len(results) == 2
        assert "handler1" in results
        assert "handler2" in results

    @pytest.mark.asyncio
    async def test_register_handler(self):
        """Test registering a handler."""
        bus = EventBus(name="test")

        async def my_handler(event: Event):
            pass

        handler = bus.register(r"test\..*", my_handler)

        assert len(bus.handlers) == 1
        assert handler.pattern == r"test\..*"


class TestMiddleware:
    """Tests for event middleware."""

    @pytest.mark.asyncio
    async def test_middleware_execution(self):
        """Test middleware is executed before handler."""
        bus = EventBus(name="test")
        execution_order = []

        class TestMiddleware(BaseMiddleware):
            def __init__(self):
                super().__init__(event_pattern=None)

            async def __call__(self, *, next_, event, context=None):
                execution_order.append("middleware_start")
                await next_()
                execution_order.append("middleware_end")

        bus.use(TestMiddleware())

        @bus.on(r"test\..*")
        async def handler(event: Event):
            execution_order.append("handler")

        event = Event.create(path="test.event")
        await bus.emit(event)

        assert execution_order == ["middleware_start", "handler", "middleware_end"]

    @pytest.mark.asyncio
    async def test_middleware_pattern_matching(self):
        """Test middleware only runs for matching events."""
        bus = EventBus(name="test")
        middleware_called = []

        class UserMiddleware(BaseMiddleware):
            def __init__(self):
                super().__init__(event_pattern=r"user\..*")

            async def __call__(self, *, next_, event, context=None):
                middleware_called.append("user_middleware")
                await next_()

        bus.use(UserMiddleware())

        @bus.on(r".*")
        async def handler(event: Event):
            pass

        # Should trigger middleware
        await bus.emit(Event.create(path="user.created"))
        assert "user_middleware" in middleware_called

        middleware_called.clear()

        # Should NOT trigger middleware
        await bus.emit(Event.create(path="order.created"))
        assert "user_middleware" not in middleware_called


class TestEventSource:
    """Tests for EventSource."""

    @pytest.mark.asyncio
    async def test_emit_event(self):
        """Test emitting events from a source."""
        bus = EventBus(name="test")
        received_events = []

        @bus.on(r"user\..*")
        async def handler(event: Event):
            received_events.append(event)

        source = EventSource(event_bus=bus, name="user_service")
        event = await source.emit("user.created", {"user_id": 123})

        assert len(received_events) == 1
        assert received_events[0].parameters == {"user_id": 123}
        assert received_events[0].metadata.get("source") == "user_service"

    @pytest.mark.asyncio
    async def test_emit_pre_constructed_event(self):
        """Test emitting a pre-constructed event."""
        bus = EventBus(name="test")
        received_events = []

        @bus.on(r"user\..*")
        async def handler(event: Event):
            received_events.append(event)

        source = EventSource(event_bus=bus, name="user_service")
        event = Event.create(path="user.deleted", parameters={"user_id": 456})
        await source.emit_event(event)

        assert len(received_events) == 1
        assert received_events[0].parameters == {"user_id": 456}
        # Note: emit_event doesn't mutate the original event's metadata
