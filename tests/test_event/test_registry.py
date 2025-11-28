"""Tests of Event/Registry module.
"""

import pytest
from blue_firmament.event.registry import listen_to, EventBus, EventEntry
from blue_firmament.event.main import EventID, Event, Method
from blue_firmament.event.result import EventResult


def test_listen_to():

    @listen_to(
        "POST", "/path/to"
    )
    def default_event_source(a: str, b: int):
        return a, b

    @listen_to(
        "POST", "/path/to",
        event_sources=("event_source_a", "event_source_b")
    )
    def multiple_event_sources(a: str, b: int):
        return a, b

    assert isinstance(default_event_source, tuple)
    assert len(default_event_source) == 2
    assert default_event_source[0] == ("default",)
    assert multiple_event_sources[0] == ("event_source_a", "event_source_b")
    assert default_event_source[1].id == EventID("POST", "/path/to")
    # Note: Testing the function directly, not through EventHandler.__call__
    assert default_event_source[1].handlers[0].function(1, 2) == (1, 2)


def test_event_bus_creation():
    """Test EventBus creation and basic properties."""
    bus = EventBus(name="test_bus", path_prefix="/api")
    assert bus.name == "test_bus"
    assert len(bus.static_entries) == 0
    assert len(bus.dynamic_entries) == 0


def test_event_bus_add_entry():
    """Test adding entries to EventBus."""
    bus = EventBus(name="test_bus")
    
    def handler():
        return "test"
    
    entry = EventEntry(
        EventID(Method.GET, "/test"),
        handler
    )
    
    bus.add_entry(entry)
    assert len(bus.static_entries) == 1


def test_event_bus_lookup():
    """Test looking up entries in EventBus."""
    bus = EventBus(name="test_bus")
    
    def handler():
        return "test"
    
    entry = EventEntry(
        EventID(Method.GET, "/test"),
        handler
    )
    
    bus.add_entry(entry)
    
    found_entry = bus.lookup(EventID(Method.GET, "/test"))
    assert found_entry is not None
    assert found_entry.id == EventID(Method.GET, "/test")


def test_event_bus_merge():
    """Test merging two EventBus instances."""
    bus1 = EventBus(name="bus1")
    bus2 = EventBus(name="bus2")
    
    def handler1():
        return "handler1"
    
    def handler2():
        return "handler2"
    
    bus1.add_entry(EventEntry(EventID(Method.GET, "/test1"), handler1))
    bus2.add_entry(EventEntry(EventID(Method.POST, "/test2"), handler2))
    
    bus1.merge(bus2)
    
    assert len(bus1.static_entries) == 2


def test_event_registry_alias():
    """Test that EventRegistry is an alias for EventBus."""
    from blue_firmament.event.registry import EventRegistry
    assert EventRegistry is EventBus
