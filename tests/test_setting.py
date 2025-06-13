"""Tests for setting module.
"""

from blue_firmament.setting import EnvSetting, private_field, field


class TestEnvSetting:

    def test_load(self):
        """
        - priority: local > env > base
        """

        class EnvBase(EnvSetting):
            _env = private_field(default="base")

            base_field: int = 1
            local_field: int
            env_field: int
            override_field: str

        class EnvLocal(EnvBase):
            _env = private_field(default="local")

            local_field: int = 4
            override_field = "local first"

        class EnvProduction(EnvBase):
            _env = private_field(default="production")

            env_field: int = 5
            override_field = "env value"

        setting = EnvBase.load()

        assert setting.base_field == 1
        assert setting.local_field == 4
        assert setting.env_field == 5
        assert setting.override_field == 'local first'
