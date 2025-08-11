"""Tests of Task/Registry module.
"""

from blue_firmament.task.registry import listen_to
from blue_firmament.task.main import TaskID


def test_listen_to():

    @listen_to(
        "POST", "/path/to"
    )
    def default_transporter(a: str, b: int):
        return a, b

    @listen_to(
        "POST", "/path/to",
        transporters=("transporter_a", "transporter_b")
    )
    def multiple_transporters(a: str, b: int):
        return a, b

    assert isinstance(default_transporter, tuple)
    assert len(default_transporter) == 2
    assert default_transporter[0] == ("default",)
    assert multiple_transporters[0] == ("transporter_a", "transporter_b")
    assert default_transporter[1].id == TaskID("POST", "/path/to")
    assert default_transporter[1].handlers[0](1, 2) == (1, 2)
