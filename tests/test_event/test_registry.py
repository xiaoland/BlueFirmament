"""Tests of Event/Registry module.
"""

from blue_firmament.event.registry import listen_to
from blue_firmament.event.main import TaskID


def test_listen_to():

    @listen_to(
        "POST", "/path/to"
    )
    def default_event_source(a: str, b: int):
        return a, b

    @listen_to(
        "POST", "/path/to",
        transporters=("event_source_a", "event_source_b")
    )
    def multiple_event_sources(a: str, b: int):
        return a, b

    assert isinstance(default_event_source, tuple)
    assert len(default_event_source) == 2
    assert default_event_source[0] == ("default",)
    assert multiple_event_sources[0] == ("event_source_a", "event_source_b")
    assert default_event_source[1].id == TaskID("POST", "/path/to")
    # Note: Testing the function directly, not through TaskHandler.__call__
    assert default_event_source[1].handlers[0].function(1, 2) == (1, 2)
