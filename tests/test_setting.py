"""Tests for setting module.

Tests the new SettingField and SettingSource based setting system.
"""

import os
import json
import tempfile

from blue_firmament.setting import (
    Setting,
    SettingField,
    setting_field,
    InlineSource,
    EnvVarSource,
    JsonFileSource,
    make_setting_singleton,
    # Legacy imports for backward compatibility
    EnvSetting,
    private_field,
)
from blue_firmament._types import _undefined


class TestSettingSources:
    """Test individual SettingSource implementations."""

    def test_inline_source(self):
        """InlineSource always returns its configured value."""
        source = InlineSource("default_value")
        assert source.load() == "default_value"

        source_int = InlineSource(42)
        assert source_int.load() == 42

    def test_inline_source_with_converter(self):
        """InlineSource can apply a converter."""
        source = InlineSource("123", converter=int)
        assert source.load() == 123

    def test_inline_source_priority(self):
        """InlineSource has low priority by default."""
        source = InlineSource("value")
        assert source.priority == -100

    def test_env_var_source_found(self):
        """EnvVarSource returns the environment variable value when set."""
        os.environ["TEST_SETTING_VAR"] = "env_value"
        try:
            source = EnvVarSource("TEST_SETTING_VAR")
            assert source.load() == "env_value"
        finally:
            del os.environ["TEST_SETTING_VAR"]

    def test_env_var_source_not_found(self):
        """EnvVarSource returns _undefined when env var is not set."""
        source = EnvVarSource("NONEXISTENT_VAR_12345")
        assert source.load() is _undefined

    def test_env_var_source_with_default(self):
        """EnvVarSource returns default when env var is not set."""
        source = EnvVarSource("NONEXISTENT_VAR_12345", default="fallback")
        assert source.load() == "fallback"

    def test_env_var_source_with_converter(self):
        """EnvVarSource can convert the value."""
        os.environ["TEST_PORT"] = "8080"
        try:
            source = EnvVarSource("TEST_PORT", converter=int)
            assert source.load() == 8080
        finally:
            del os.environ["TEST_PORT"]

    def test_env_var_source_priority(self):
        """EnvVarSource has high priority by default."""
        source = EnvVarSource("TEST")
        assert source.priority == 100

    def test_json_file_source(self):
        """JsonFileSource loads values from JSON files."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"database": {"host": "localhost", "port": 5432}}, f)
            temp_path = f.name

        try:
            source = JsonFileSource(temp_path, "database.host")
            assert source.load() == "localhost"

            source_port = JsonFileSource(temp_path, "database.port")
            assert source_port.load() == 5432
        finally:
            os.unlink(temp_path)

    def test_json_file_source_missing_key(self):
        """JsonFileSource returns _undefined for missing keys."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"database": {}}, f)
            temp_path = f.name

        try:
            source = JsonFileSource(temp_path, "database.host")
            assert source.load() is _undefined
        finally:
            os.unlink(temp_path)

    def test_json_file_source_missing_file(self):
        """JsonFileSource returns _undefined for missing files."""
        source = JsonFileSource("/nonexistent/path/config.json", "key")
        assert source.load() is _undefined


class TestSettingField:
    """Test SettingField behavior."""

    def test_setting_field_with_inline_source(self):
        """SettingField loads value from InlineSource."""
        sf = SettingField(sources=[InlineSource("default")])
        value = sf.load_from_sources()
        assert value == "default"

    def test_setting_field_source_priority(self):
        """Sources are tried in priority order (highest first)."""
        sf = SettingField(
            sources=[
                InlineSource("low", priority=-100),
                InlineSource("high", priority=100),
                InlineSource("medium", priority=0),
            ]
        )
        value = sf.load_from_sources()
        assert value == "high"

    def test_setting_field_fallback(self):
        """Falls back to lower priority sources when higher ones return _undefined."""
        os.environ.pop("NONEXISTENT_SETTING", None)

        sf = SettingField(
            sources=[
                EnvVarSource("NONEXISTENT_SETTING"),  # Will return _undefined
                InlineSource("fallback"),
            ]
        )
        value = sf.load_from_sources()
        assert value == "fallback"

    def test_setting_field_env_override(self):
        """Environment variable overrides inline default."""
        os.environ["MY_SETTING"] = "from_env"
        try:
            sf = SettingField(
                sources=[
                    EnvVarSource("MY_SETTING"),
                    InlineSource("default"),
                ]
            )
            value = sf.load_from_sources()
            assert value == "from_env"
        finally:
            del os.environ["MY_SETTING"]

    def test_setting_field_no_sources(self):
        """SettingField with no sources returns _undefined."""
        sf = SettingField(sources=[])
        value = sf.load_from_sources()
        assert value is _undefined


class TestSetting:
    """Test Setting class behavior."""

    def test_setting_load_basic(self):
        """Setting.load() populates fields from sources."""

        class MySetting(Setting):
            name: SettingField[str] = SettingField(sources=[InlineSource("test_name")])
            port: SettingField[int] = SettingField(sources=[InlineSource(8080)])

        setting = MySetting.load()
        assert setting.name == "test_name"
        assert setting.port == 8080

    def test_setting_load_with_env_override(self):
        """Setting fields can be overridden by environment variables."""
        os.environ["APP_PORT"] = "9000"
        try:

            class AppSetting(Setting):
                port: SettingField[int] = SettingField(
                    sources=[
                        EnvVarSource("APP_PORT", converter=int),
                        InlineSource(8080),
                    ]
                )

            setting = AppSetting.load()
            assert setting.port == 9000
        finally:
            del os.environ["APP_PORT"]

    def test_setting_load_with_json_file(self):
        """Setting fields can load from JSON files."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"server": {"host": "0.0.0.0"}}, f)
            temp_path = f.name

        try:

            class ServerSetting(Setting):
                host: SettingField[str] = SettingField(
                    sources=[
                        JsonFileSource(temp_path, "server.host"),
                        InlineSource("localhost"),
                    ]
                )

            setting = ServerSetting.load()
            assert setting.host == "0.0.0.0"
        finally:
            os.unlink(temp_path)

    def test_setting_mixed_fields(self):
        """Setting can have both SettingField and regular Field."""

        class MixedSetting(Setting):
            dynamic_value: SettingField[str] = SettingField(
                sources=[InlineSource("dynamic")]
            )
            static_value: str = "static"

        setting = MixedSetting.load()
        assert setting.dynamic_value == "dynamic"
        assert setting.static_value == "static"

    def test_setting_field_factory(self):
        """setting_field() factory function works correctly."""

        class FactorySetting(Setting):
            value: SettingField[int] = setting_field(
                sources=[InlineSource(42)], description="A test value"
            )

        setting = FactorySetting.load()
        assert setting.value == 42


class TestSettingSingleton:
    """Test make_setting_singleton helper."""

    def test_singleton_get_set(self):
        """Singleton pattern works correctly."""

        class SingletonSetting(Setting):
            value: SettingField[str] = SettingField(sources=[InlineSource("initial")])

        initial = SingletonSetting.load()
        get_setting, set_setting = make_setting_singleton(initial)

        assert get_setting().value == "initial"

        # Update singleton
        new_setting = SingletonSetting.load()
        new_setting._set_value(SingletonSetting.__fields__["value"], "updated")
        set_setting(new_setting)

        assert get_setting().value == "updated"


class TestLegacyEnvSetting:
    """Test legacy EnvSetting for backward compatibility."""

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
        assert setting.override_field == "local first"
