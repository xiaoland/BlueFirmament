"""Tests Of Manager/Base module"""

from blue_firmament.manager.base import BaseManager
from blue_firmament.task import listen_to, TaskID, TaskRegistry


def test_task_registries():

    class AManager(BaseManager, path_prefix="a"):
        @listen_to("GET", "/{id}")
        def get_a(self, id_: str):
            return id_

    assert isinstance(AManager.__task_registries__, dict)
    assert isinstance(AManager.__task_registries__["default"], TaskRegistry)
    assert AManager.__task_registries__["default"].lookup(
        TaskID("GET", "/a/1")
    ).handlers[0].function(1, "1") == "1"

