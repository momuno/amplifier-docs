"""Configuration management for doc-gen."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Config:
    """Global configuration for doc-gen."""

    # LLM Configuration
    llm_provider: str = "anthropic"  # anthropic, openai
    llm_model: str = "claude-3-5-sonnet-20240620"  # claude-3-5-sonnet-20240620, claude-3-opus-20240229
    llm_api_key: Optional[str] = None
    llm_timeout: int = 60  # seconds

    # Repository Configuration
    temp_dir: Optional[Path] = None  # None = use system temp

    @classmethod
    def load(cls, config_path: Path = Path(".doc-gen/config.yaml")) -> "Config":
        """Load configuration from file and environment.

        Args:
            config_path: Path to config YAML file

        Returns:
            Config instance with loaded values
        """
        # Start with defaults
        config_dict = {}

        # 1. Load from config.yaml if exists
        if config_path.exists():
            with open(config_path, "r") as f:
                data = yaml.safe_load(f) or {}

            # Parse LLM config
            if "llm" in data:
                llm_config = data["llm"]
                if "provider" in llm_config:
                    config_dict["llm_provider"] = llm_config["provider"]
                if "model" in llm_config:
                    config_dict["llm_model"] = llm_config["model"]
                if "timeout" in llm_config:
                    config_dict["llm_timeout"] = llm_config["timeout"]

            # Parse repository config
            if "repositories" in data:
                repo_config = data["repositories"]
                if "temp_dir" in repo_config:
                    config_dict["temp_dir"] = Path(repo_config["temp_dir"])

        # 2. Override with environment variables
        # Determine which API key to load based on provider
        provider = config_dict.get("llm_provider", "anthropic")
        if provider == "anthropic":
            env_key = os.getenv("ANTHROPIC_API_KEY")
        elif provider == "openai":
            env_key = os.getenv("OPENAI_API_KEY")
        else:
            env_key = None

        if env_key:
            config_dict["llm_api_key"] = env_key

        # Create config instance
        return cls(**config_dict)

    def save(self, config_path: Path = Path(".doc-gen/config.yaml")):
        """Save configuration to file.

        Args:
            config_path: Path to save config YAML file
        """
        # Create parent directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Build config structure
        config_data = {
            "llm": {
                "provider": self.llm_provider,
                "model": self.llm_model,
                "timeout": self.llm_timeout,
            }
        }

        # Add repository config if temp_dir is set
        if self.temp_dir is not None:
            config_data["repositories"] = {
                "temp_dir": str(self.temp_dir)
            }

        # Write to file
        with open(config_path, "w") as f:
            yaml.dump(config_data, f, sort_keys=False, default_flow_style=False)

    def validate(self):
        """Validate configuration is complete.

        Raises:
            ValueError: If required configuration is missing
        """
        if not self.llm_api_key:
            provider_upper = self.llm_provider.upper()
            raise ValueError(
                f"LLM API key not found. Set in config.yaml or environment:\n"
                f"  export {provider_upper}_API_KEY=your-key-here"
            )
