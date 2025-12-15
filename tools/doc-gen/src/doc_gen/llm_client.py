"""Simple Anthropic Claude LLM client with debug logging support."""

import os
from pathlib import Path

from doc_gen.prompt_logger import PromptLogger


class ClaudeClient:
    """Simple wrapper for Anthropic Claude API with debug logging."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """Initialize Claude client.

        Args:
            model: Model identifier (default: claude-sonnet-4-20250514)

        Raises:
            ValueError: If API key not found
            ImportError: If anthropic package not installed
        """
        # Get API key from environment
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            # Fallback to loading from file
            claude_key_path = Path.home() / ".claude" / "api_key.txt"
            if claude_key_path.exists():
                api_key = claude_key_path.read_text().strip()
                if "=" in api_key:
                    api_key = api_key.split("=", 1)[1].strip()

        if not api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or create ~/.claude/api_key.txt"
            )

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def generate(self, prompt: str, temperature: float = 0.3, model: str = None, max_tokens: int = None, location: str = "unknown") -> str:
        """Generate response from Claude with optional debug logging.

        Args:
            prompt: The prompt to send to Claude
            temperature: Temperature setting (0.0-1.0)
            model: Model to use (overrides default if provided)
            max_tokens: Maximum response tokens to generate (overrides default if provided)
            location: Location identifier for debug logging

        Returns:
            Generated text response
        """
        # Use provided values or fall back to defaults
        use_model = model or self.model
        use_max_response_tokens = max_tokens or 4096

        # Log request if debug mode enabled
        if PromptLogger.is_enabled():
            PromptLogger.log_api_call(
                model=use_model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=use_max_response_tokens,
                location=location
            )

        # Make API call
        message = self.client.messages.create(
            model=use_model,
            max_tokens=use_max_response_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        response = message.content[0].text

        # Log response if debug mode enabled
        if PromptLogger.is_enabled():
            PromptLogger.log_api_call(
                model=use_model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=use_max_response_tokens,
                location=location,
                response=response
            )

        return response
