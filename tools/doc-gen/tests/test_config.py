"""Tests for config management."""

import os
import tempfile
from pathlib import Path
import pytest
import yaml

from doc_gen.config import Config


class TestConfig:
    """Test Config dataclass and loading."""

    def test_config_has_default_values(self):
        """Config should have sensible defaults."""
        config = Config()
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert config.llm_timeout == 60
        assert config.llm_api_key is None
        assert config.temp_dir is None

    def test_config_load_from_file(self, tmp_path):
        """Config should load from YAML file."""
        # ARRANGE
        config_file = tmp_path / "config.yaml"
        config_data = {
            "llm": {
                "provider": "anthropic",
                "model": "claude-3-opus",
                "timeout": 120,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # ACT
        config = Config.load(config_file)

        # ASSERT
        assert config.llm_provider == "anthropic"
        assert config.llm_model == "claude-3-opus"
        assert config.llm_timeout == 120

    def test_config_load_from_environment(self, tmp_path, monkeypatch):
        """Config should load API key from environment variable."""
        # ARRANGE
        config_file = tmp_path / "config.yaml"
        config_data = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4",
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.setenv("OPENAI_API_KEY", "test-key-from-env")

        # ACT
        config = Config.load(config_file)

        # ASSERT
        assert config.llm_api_key == "test-key-from-env"

    def test_config_environment_overrides_file(self, tmp_path, monkeypatch):
        """Environment variables should override config file."""
        # ARRANGE
        config_file = tmp_path / "config.yaml"
        config_data = {
            "llm": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.setenv("OPENAI_API_KEY", "env-override-key")

        # ACT
        config = Config.load(config_file)

        # ASSERT
        assert config.llm_api_key == "env-override-key"

    def test_config_load_nonexistent_file_uses_defaults(self):
        """Loading non-existent config should use defaults."""
        # ARRANGE
        nonexistent = Path("/tmp/does-not-exist-config.yaml")

        # ACT
        config = Config.load(nonexistent)

        # ASSERT
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"

    def test_config_save_creates_yaml_file(self, tmp_path):
        """Config should save to YAML file."""
        # ARRANGE
        config = Config(
            llm_provider="anthropic",
            llm_model="claude-3-opus",
            llm_timeout=90
        )
        config_file = tmp_path / "config.yaml"

        # ACT
        config.save(config_file)

        # ASSERT
        assert config_file.exists()
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
        assert data["llm"]["provider"] == "anthropic"
        assert data["llm"]["model"] == "claude-3-opus"
        assert data["llm"]["timeout"] == 90

    def test_config_validate_raises_error_without_api_key(self):
        """Validation should fail without API key."""
        # ARRANGE
        config = Config(llm_provider="openai", llm_api_key=None)

        # ACT & ASSERT
        with pytest.raises(ValueError, match="LLM API key not found"):
            config.validate()

    def test_config_validate_passes_with_api_key(self):
        """Validation should pass with API key."""
        # ARRANGE
        config = Config(llm_provider="openai", llm_api_key="valid-key")

        # ACT & ASSERT (should not raise)
        config.validate()

    def test_config_load_with_custom_temp_dir(self, tmp_path):
        """Config should support custom temp directory."""
        # ARRANGE
        config_file = tmp_path / "config.yaml"
        custom_temp = tmp_path / "custom_temp"
        config_data = {
            "llm": {"provider": "openai"},
            "repositories": {"temp_dir": str(custom_temp)}
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # ACT
        config = Config.load(config_file)

        # ASSERT
        assert config.temp_dir == custom_temp

    def test_config_anthropic_api_key_from_env(self, tmp_path, monkeypatch):
        """Config should load Anthropic API key from ANTHROPIC_API_KEY."""
        # ARRANGE
        config_file = tmp_path / "config.yaml"
        config_data = {
            "llm": {
                "provider": "anthropic",
                "model": "claude-3-opus",
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test-key")

        # ACT
        config = Config.load(config_file)

        # ASSERT
        assert config.llm_api_key == "anthropic-test-key"
