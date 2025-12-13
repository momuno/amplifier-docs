"""LLM client abstraction for doc-gen."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import click
from openai import OpenAI
from anthropic import Anthropic


@dataclass
class LLMResponse:
    """Response from LLM API call."""

    content: str
    tokens_used: int
    model: str
    duration_seconds: float


class LLMClient(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self):
        """Initialize LLM client."""
        self.debug = False

    def set_debug(self, debug: bool):
        """Enable/disable debug logging.

        Args:
            debug: If True, log prompts and responses
        """
        self.debug = debug

    def _log_debug(self, title: str, content: str, max_length: int = 2000):
        """Log debug information if debug mode is enabled.

        Args:
            title: Section title
            content: Content to log
            max_length: Maximum content length to display (default 2000 chars)
        """
        if not self.debug:
            return

        click.echo(f"\n{'=' * 80}", err=True)
        click.echo(f"DEBUG: {title}", err=True)
        click.echo(f"{'=' * 80}", err=True)
        
        if len(content) > max_length:
            click.echo(f"{content[:max_length]}\n... (truncated, {len(content)} total chars)", err=True)
        else:
            click.echo(content, err=True)
        
        click.echo(f"{'=' * 80}\n", err=True)

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text from prompt.

        Args:
            prompt: User prompt
            system_prompt: System prompt (instructions)
            json_mode: If True, use JSON mode for structured output
            temperature: Creativity level (0.0-2.0)

        Returns:
            LLMResponse with content and metadata

        Raises:
            LLMTimeoutError: Request timed out
            LLMRateLimitError: Rate limit exceeded
            LLMAPIError: Other API errors
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI API client."""

    def __init__(self, api_key: str, model: str = "gpt-4", timeout: int = 60):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model to use (gpt-4, gpt-3.5-turbo, etc.)
            timeout: Request timeout in seconds
        """
        super().__init__()
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text from OpenAI API.

        Args:
            prompt: User prompt
            system_prompt: System prompt (instructions)
            json_mode: If True, use JSON mode for structured output
            temperature: Creativity level (0.0-2.0)

        Returns:
            LLMResponse with content and metadata

        Raises:
            LLMTimeoutError: Request timed out
            LLMRateLimitError: Rate limit exceeded
            LLMAPIError: Other API errors
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Debug logging: Show prompts being sent
        if self.debug:
            if system_prompt:
                self._log_debug("SYSTEM PROMPT", system_prompt)
            self._log_debug("USER PROMPT", prompt)

        start_time = time.time()

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "timeout": self.timeout,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)

            duration = time.time() - start_time
            
            content = response.choices[0].message.content

            # Debug logging: Show response received
            if self.debug:
                self._log_debug("LLM RESPONSE", content)
                self._log_debug("METADATA", f"Model: {response.model}\nTokens: {response.usage.total_tokens}\nDuration: {duration:.1f}s")

            return LLMResponse(
                content=content,
                tokens_used=response.usage.total_tokens,
                model=response.model,
                duration_seconds=duration,
            )

        except Exception as e:
            # Transform exceptions into custom error types
            raise self._handle_error(e)

    def _handle_error(self, error: Exception):
        """Transform OpenAI errors into custom error types.

        Args:
            error: Original exception

        Returns:
            Custom LLM exception

        Raises:
            LLMTimeoutError: On timeout
            LLMRateLimitError: On rate limit
            LLMAPIError: On other errors
        """
        error_str = str(error).lower()

        if "timeout" in error_str:
            raise LLMTimeoutError(f"OpenAI request timed out after {self.timeout}s")
        elif "rate limit" in error_str:
            raise LLMRateLimitError("OpenAI rate limit exceeded. Wait and retry.")
        else:
            raise LLMAPIError(f"OpenAI API error: {error}")


# Custom exceptions
class LLMError(Exception):
    """Base exception for LLM errors."""

    pass


class LLMTimeoutError(LLMError):
    """LLM request timed out."""

    pass


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    pass


class LLMAPIError(LLMError):
    """Other LLM API errors."""

    pass


class AnthropicClient(LLMClient):
    """Anthropic (Claude) API client."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-opus-20240229",
        timeout: int = 60,
        max_tokens: int = 16384,
    ):
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
            model: Model to use (claude-3-opus, claude-3-sonnet, etc.)
            timeout: Request timeout in seconds
            max_tokens: Maximum tokens to generate (required by Anthropic, max 16384 for Claude 4/Sonnet 4)
        """
        super().__init__()
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text from Anthropic API.

        Args:
            prompt: User prompt
            system_prompt: System prompt (instructions)
            json_mode: If True, request JSON output (via system prompt)
            temperature: Creativity level (0.0-1.0)

        Returns:
            LLMResponse with content and metadata

        Raises:
            LLMTimeoutError: Request timed out
            LLMRateLimitError: Rate limit exceeded
            LLMAPIError: Other API errors
        """
        # Build messages (user prompt only for Anthropic)
        messages = [{"role": "user", "content": prompt}]

        # System prompt is separate in Anthropic
        system = system_prompt or ""
        
        # Add JSON instruction to system prompt if needed
        if json_mode and system:
            system += "\n\nIMPORTANT: Return your response as valid JSON only."
        elif json_mode:
            system = "Return your response as valid JSON only."

        # Debug logging: Show prompts being sent
        if self.debug:
            if system:
                self._log_debug("SYSTEM PROMPT", system)
            self._log_debug("USER PROMPT", prompt)

        start_time = time.time()

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": temperature,
                "timeout": self.timeout,
            }

            if system:
                kwargs["system"] = system

            response = self.client.messages.create(**kwargs)

            duration = time.time() - start_time

            # Extract text from content blocks
            content = response.content[0].text
            
            # Debug logging: Show response received
            if self.debug:
                self._log_debug("LLM RESPONSE", content)
                self._log_debug("METADATA", f"Model: {response.model}\nTokens In: {response.usage.input_tokens}\nTokens Out: {response.usage.output_tokens}\nDuration: {duration:.1f}s")

            # Calculate total tokens (input + output)
            total_tokens = response.usage.input_tokens + response.usage.output_tokens

            return LLMResponse(
                content=content,
                tokens_used=total_tokens,
                model=response.model,
                duration_seconds=duration,
            )

        except Exception as e:
            # Transform exceptions into custom error types
            raise self._handle_error(e)

    def _handle_error(self, error: Exception):
        """Transform Anthropic errors into custom error types.

        Args:
            error: Original exception

        Returns:
            Custom LLM exception

        Raises:
            LLMTimeoutError: On timeout
            LLMRateLimitError: On rate limit
            LLMAPIError: On other errors
        """
        error_str = str(error).lower()

        if "timeout" in error_str:
            raise LLMTimeoutError(f"Anthropic request timed out after {self.timeout}s")
        elif "rate limit" in error_str:
            raise LLMRateLimitError("Anthropic rate limit exceeded. Wait and retry.")
        else:
            raise LLMAPIError(f"Anthropic API error: {error}")
