"""Tests for LLM client abstraction."""

import pytest
from unittest.mock import Mock, patch

from doc_gen.llm_client import (
    LLMClient,
    LLMResponse,
    OpenAIClient,
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAPIError,
)


class TestLLMResponse:
    """Test LLMResponse dataclass."""

    def test_llm_response_has_required_fields(self):
        """LLMResponse should have all required fields."""
        # ACT
        response = LLMResponse(
            content="Test content",
            tokens_used=100,
            model="gpt-4",
            duration_seconds=1.5
        )

        # ASSERT
        assert response.content == "Test content"
        assert response.tokens_used == 100
        assert response.model == "gpt-4"
        assert response.duration_seconds == 1.5


class TestOpenAIClient:
    """Test OpenAI LLM client implementation."""

    def test_openai_client_initializes(self):
        """OpenAIClient should initialize with API key and model."""
        # ACT
        client = OpenAIClient(api_key="test-key", model="gpt-4", timeout=60)

        # ASSERT
        assert client.model == "gpt-4"
        assert client.timeout == 60

    @patch('doc_gen.llm_client.OpenAI')
    def test_generate_sends_basic_request(self, mock_openai_class):
        """Generate should send request with prompt."""
        # ARRANGE
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Generated text"))]
        mock_response.usage = Mock(total_tokens=150)
        mock_response.model = "gpt-4"
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")

        # ACT
        response = client.generate(prompt="Test prompt")

        # ASSERT
        assert response.content == "Generated text"
        assert response.tokens_used == 150
        assert response.model == "gpt-4"
        mock_client.chat.completions.create.assert_called_once()

    @patch('doc_gen.llm_client.OpenAI')
    def test_generate_includes_system_prompt(self, mock_openai_class):
        """Generate should include system prompt if provided."""
        # ARRANGE
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response"))]
        mock_response.usage = Mock(total_tokens=100)
        mock_response.model = "gpt-4"
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")

        # ACT
        client.generate(
            prompt="User prompt",
            system_prompt="System instructions"
        )

        # ASSERT
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == 'System instructions'
        assert messages[1]['role'] == 'user'
        assert messages[1]['content'] == 'User prompt'

    @patch('doc_gen.llm_client.OpenAI')
    def test_generate_uses_json_mode(self, mock_openai_class):
        """Generate should enable JSON mode when requested."""
        # ARRANGE
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"key": "value"}'))]
        mock_response.usage = Mock(total_tokens=50)
        mock_response.model = "gpt-4"
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")

        # ACT
        client.generate(prompt="Test", json_mode=True)

        # ASSERT
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs['response_format'] == {"type": "json_object"}

    @patch('doc_gen.llm_client.OpenAI')
    def test_generate_uses_temperature(self, mock_openai_class):
        """Generate should use custom temperature when provided."""
        # ARRANGE
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response"))]
        mock_response.usage = Mock(total_tokens=50)
        mock_response.model = "gpt-4"
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")

        # ACT
        client.generate(prompt="Test", temperature=0.2)

        # ASSERT
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs['temperature'] == 0.2

    @patch('doc_gen.llm_client.OpenAI')
    def test_generate_tracks_duration(self, mock_openai_class):
        """Generate should track request duration."""
        # ARRANGE
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response"))]
        mock_response.usage = Mock(total_tokens=50)
        mock_response.model = "gpt-4"
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")

        # ACT
        response = client.generate(prompt="Test")

        # ASSERT
        assert response.duration_seconds >= 0
        assert isinstance(response.duration_seconds, float)

    @patch('doc_gen.llm_client.OpenAI')
    def test_generate_handles_timeout_error(self, mock_openai_class):
        """Generate should raise LLMTimeoutError on timeout."""
        # ARRANGE
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Request timeout exceeded")

        client = OpenAIClient(api_key="test-key", timeout=30)

        # ACT & ASSERT
        with pytest.raises(LLMTimeoutError, match="timed out"):
            client.generate(prompt="Test")

    @patch('doc_gen.llm_client.OpenAI')
    def test_generate_handles_rate_limit_error(self, mock_openai_class):
        """Generate should raise LLMRateLimitError on rate limit."""
        # ARRANGE
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")

        client = OpenAIClient(api_key="test-key")

        # ACT & ASSERT
        with pytest.raises(LLMRateLimitError, match="rate limit"):
            client.generate(prompt="Test")

    @patch('doc_gen.llm_client.OpenAI')
    def test_generate_handles_generic_api_error(self, mock_openai_class):
        """Generate should raise LLMAPIError for other errors."""
        # ARRANGE
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Service unavailable")

        client = OpenAIClient(api_key="test-key")

        # ACT & ASSERT
        with pytest.raises(LLMAPIError, match="API error"):
            client.generate(prompt="Test")

    @patch('doc_gen.llm_client.OpenAI')
    def test_generate_uses_configured_model(self, mock_openai_class):
        """Generate should use the model specified in init."""
        # ARRANGE
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response"))]
        mock_response.usage = Mock(total_tokens=50)
        mock_response.model = "gpt-3.5-turbo"
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key", model="gpt-3.5-turbo")

        # ACT
        client.generate(prompt="Test")

        # ASSERT
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs['model'] == "gpt-3.5-turbo"

    @patch('doc_gen.llm_client.OpenAI')
    def test_generate_uses_configured_timeout(self, mock_openai_class):
        """Generate should use the timeout specified in init."""
        # ARRANGE
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response"))]
        mock_response.usage = Mock(total_tokens=50)
        mock_response.model = "gpt-4"
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key", timeout=120)

        # ACT
        client.generate(prompt="Test")

        # ASSERT
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs['timeout'] == 120
