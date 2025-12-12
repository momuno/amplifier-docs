"""Tests for Anthropic (Claude) LLM client."""

import pytest
from unittest.mock import Mock, patch

from doc_gen.llm_client import (
    AnthropicClient,
    LLMResponse,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAPIError,
)


class TestAnthropicClient:
    """Test Anthropic LLM client implementation."""

    def test_anthropic_client_initializes(self):
        """AnthropicClient should initialize with API key and model."""
        # ACT
        client = AnthropicClient(api_key="test-key", model="claude-3-opus-20240229", timeout=60)

        # ASSERT
        assert client.model == "claude-3-opus-20240229"
        assert client.timeout == 60

    @patch('doc_gen.llm_client.Anthropic')
    def test_generate_sends_basic_request(self, mock_anthropic_class):
        """Generate should send request with prompt."""
        # ARRANGE
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "Generated text"
        mock_response.content = [mock_content_block]
        mock_response.usage = Mock(input_tokens=50, output_tokens=100)
        mock_response.model = "claude-3-opus-20240229"
        mock_client.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")

        # ACT
        response = client.generate(prompt="Test prompt")

        # ASSERT
        assert response.content == "Generated text"
        assert response.tokens_used == 150  # input + output
        assert response.model == "claude-3-opus-20240229"
        mock_client.messages.create.assert_called_once()

    @patch('doc_gen.llm_client.Anthropic')
    def test_generate_includes_system_prompt(self, mock_anthropic_class):
        """Generate should include system prompt if provided."""
        # ARRANGE
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "Response"
        mock_response.content = [mock_content_block]
        mock_response.usage = Mock(input_tokens=50, output_tokens=50)
        mock_response.model = "claude-3-opus-20240229"
        mock_client.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")

        # ACT
        client.generate(
            prompt="User prompt",
            system_prompt="System instructions"
        )

        # ASSERT
        call_args = mock_client.messages.create.call_args
        # Anthropic uses 'system' parameter, not in messages
        assert call_args.kwargs['system'] == "System instructions"
        # User prompt should be in messages
        messages = call_args.kwargs['messages']
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'] == 'User prompt'

    @patch('doc_gen.llm_client.Anthropic')
    def test_generate_uses_temperature(self, mock_anthropic_class):
        """Generate should use custom temperature when provided."""
        # ARRANGE
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "Response"
        mock_response.content = [mock_content_block]
        mock_response.usage = Mock(input_tokens=25, output_tokens=25)
        mock_response.model = "claude-3-opus-20240229"
        mock_client.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")

        # ACT
        client.generate(prompt="Test", temperature=0.2)

        # ASSERT
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs['temperature'] == 0.2

    @patch('doc_gen.llm_client.Anthropic')
    def test_generate_tracks_duration(self, mock_anthropic_class):
        """Generate should track request duration."""
        # ARRANGE
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "Response"
        mock_response.content = [mock_content_block]
        mock_response.usage = Mock(input_tokens=25, output_tokens=25)
        mock_response.model = "claude-3-opus-20240229"
        mock_client.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")

        # ACT
        response = client.generate(prompt="Test")

        # ASSERT
        assert response.duration_seconds >= 0
        assert isinstance(response.duration_seconds, float)

    @patch('doc_gen.llm_client.Anthropic')
    def test_generate_handles_timeout_error(self, mock_anthropic_class):
        """Generate should raise LLMTimeoutError on timeout."""
        # ARRANGE
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("Request timeout exceeded")

        client = AnthropicClient(api_key="test-key", timeout=30)

        # ACT & ASSERT
        with pytest.raises(LLMTimeoutError, match="timed out"):
            client.generate(prompt="Test")

    @patch('doc_gen.llm_client.Anthropic')
    def test_generate_handles_rate_limit_error(self, mock_anthropic_class):
        """Generate should raise LLMRateLimitError on rate limit."""
        # ARRANGE
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("Rate limit exceeded")

        client = AnthropicClient(api_key="test-key")

        # ACT & ASSERT
        with pytest.raises(LLMRateLimitError, match="rate limit"):
            client.generate(prompt="Test")

    @patch('doc_gen.llm_client.Anthropic')
    def test_generate_handles_generic_api_error(self, mock_anthropic_class):
        """Generate should raise LLMAPIError for other errors."""
        # ARRANGE
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("Service unavailable")

        client = AnthropicClient(api_key="test-key")

        # ACT & ASSERT
        with pytest.raises(LLMAPIError, match="API error"):
            client.generate(prompt="Test")

    @patch('doc_gen.llm_client.Anthropic')
    def test_generate_uses_configured_model(self, mock_anthropic_class):
        """Generate should use the model specified in init."""
        # ARRANGE
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "Response"
        mock_response.content = [mock_content_block]
        mock_response.usage = Mock(input_tokens=25, output_tokens=25)
        mock_response.model = "claude-3-sonnet-20240229"
        mock_client.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key", model="claude-3-sonnet-20240229")

        # ACT
        client.generate(prompt="Test")

        # ASSERT
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs['model'] == "claude-3-sonnet-20240229"

    @patch('doc_gen.llm_client.Anthropic')
    def test_generate_uses_configured_timeout(self, mock_anthropic_class):
        """Generate should use the timeout specified in init."""
        # ARRANGE
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "Response"
        mock_response.content = [mock_content_block]
        mock_response.usage = Mock(input_tokens=25, output_tokens=25)
        mock_response.model = "claude-3-opus-20240229"
        mock_client.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key", timeout=120)

        # ACT
        client.generate(prompt="Test")

        # ASSERT
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs['timeout'] == 120

    @patch('doc_gen.llm_client.Anthropic')
    def test_generate_sets_max_tokens(self, mock_anthropic_class):
        """Generate should set max_tokens (required by Anthropic)."""
        # ARRANGE
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "Response"
        mock_response.content = [mock_content_block]
        mock_response.usage = Mock(input_tokens=25, output_tokens=25)
        mock_response.model = "claude-3-opus-20240229"
        mock_client.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")

        # ACT
        client.generate(prompt="Test")

        # ASSERT
        call_args = mock_client.messages.create.call_args
        assert 'max_tokens' in call_args.kwargs
        assert call_args.kwargs['max_tokens'] > 0
