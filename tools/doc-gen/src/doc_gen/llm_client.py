"""LLM client abstraction for doc-gen."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

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

            return LLMResponse(
                content=response.choices[0].message.content,
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
        max_tokens: int = 4096,
    ):
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
            model: Model to use (claude-3-opus, claude-3-sonnet, etc.)
            timeout: Request timeout in seconds
            max_tokens: Maximum tokens to generate (required by Anthropic)
        """
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
