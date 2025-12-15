"""Centralized prompt logging for debugging LLM interactions."""

import json
from datetime import datetime, timezone
from pathlib import Path


class PromptLogger:
    """Logger for capturing all LLM API calls with full prompts.

    When enabled via --debug-prompts flag, logs every API call to:
    .doc-gen/debug/prompts-YYYYMMDD-HHMMSS.json

    Creates a valid JSON array with comma-separated entries:
    - timestamp: ISO 8601 timestamp
    - model: Model identifier
    - temperature: Temperature setting
    - prompt: Full prompt text
    - response: Full response text (if available)
    - location: Where in code this was called from
    """

    _enabled = False
    _log_file = None
    _log_path = None
    _first_entry = True

    @classmethod
    def enable(cls, project_root: Path = None):
        """Enable prompt logging and create log file.

        Args:
            project_root: Project root directory (defaults to cwd)
        """
        if cls._enabled:
            return  # Already enabled

        cls._enabled = True
        cls._first_entry = True

        # Create log directory
        if project_root is None:
            project_root = Path.cwd()

        log_dir = project_root / ".doc-gen" / "debug"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        cls._log_path = log_dir / f"prompts-{timestamp}.json"

        # Open file for writing
        cls._log_file = open(cls._log_path, "w", encoding="utf-8")

        # Write opening bracket for JSON array
        cls._log_file.write("[\n")

        # Write session start as first entry
        cls._log_file.write(json.dumps({
            "type": "session_start",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "log_file": str(cls._log_path)
        }, indent=2))
        cls._log_file.flush()
        cls._first_entry = False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if prompt logging is enabled."""
        return cls._enabled

    @classmethod
    def get_log_path(cls) -> Path | None:
        """Get the current log file path."""
        return cls._log_path

    @classmethod
    def _estimate_tokens(cls, text: str) -> int:
        """Estimate token count from character length.

        Uses rough approximation: 1 token ≈ 4 characters

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        return len(text) // 4

    @classmethod
    def log_api_call(
        cls,
        model: str,
        prompt: str,
        temperature: float,
        location: str,
        response: str = None,
        max_tokens: int = None,
        **kwargs
    ):
        """Log an API call with full details.

        Args:
            model: Model identifier (e.g., "claude-sonnet-4-20250514")
            prompt: Full prompt text sent to LLM
            temperature: Temperature setting
            location: Where in code this was called (e.g., "outline_generator.py:242")
            response: Full response text (optional, log before/after)
            max_tokens: Max response tokens setting
            **kwargs: Additional metadata to log
        """
        if not cls._enabled or cls._log_file is None:
            return

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "temperature": temperature,
            "location": location,
            "prompt": prompt,
            "prompt_length_chars": len(prompt),
            "prompt_length_tokens_est": cls._estimate_tokens(prompt),
        }

        if max_tokens is not None:
            log_entry["max_response_tokens"] = max_tokens

        if response is not None:
            log_entry["response"] = response
            log_entry["response_length_chars"] = len(response)
            log_entry["response_length_tokens_est"] = cls._estimate_tokens(response)

        # Add any additional metadata
        log_entry.update(kwargs)

        # Write to file with proper JSON array formatting
        if not cls._first_entry:
            cls._log_file.write(",\n")
        cls._log_file.write(json.dumps(log_entry, indent=2))
        cls._log_file.flush()
        cls._first_entry = False

    @classmethod
    def close(cls):
        """Close the log file."""
        if cls._log_file is not None:
            # Write session end entry
            if not cls._first_entry:
                cls._log_file.write(",\n")
            cls._log_file.write(json.dumps({
                "type": "session_end",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, indent=2))
            # Close JSON array
            cls._log_file.write("\n]\n")
            cls._log_file.close()
            cls._log_file = None
        cls._enabled = False
        cls._first_entry = True
