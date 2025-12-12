"""Tests for outline generation."""

import json
import pytest
from unittest.mock import Mock

from doc_gen.outline import (
    OutlineGenerator,
    OutlineValidationError,
)
from doc_gen.llm_client import LLMResponse


class TestOutlineGenerator:
    """Test outline generation with LLM."""

    def test_outline_generator_initializes(self):
        """OutlineGenerator should initialize with LLM client."""
        # ARRANGE
        mock_client = Mock()

        # ACT
        generator = OutlineGenerator(mock_client)

        # ASSERT
        assert generator.client == mock_client

    def test_generate_outline_creates_prompt(self):
        """generate_outline should create prompt with source files."""
        # ARRANGE
        mock_client = Mock()
        mock_response = LLMResponse(
            content='{"title": "Test", "sections": []}',
            tokens_used=100,
            model="gpt-4",
            duration_seconds=1.0
        )
        mock_client.generate.return_value = mock_response

        generator = OutlineGenerator(mock_client)
        source_files = {"test.py": "print('hello')"}
        commit_hashes = {"test.py": "abc123"}

        # ACT
        outline = generator.generate_outline(source_files, commit_hashes, "Test purpose")

        # ASSERT
        # Should have called LLM with prompt
        mock_client.generate.assert_called_once()
        call_args = mock_client.generate.call_args
        assert "test.py" in call_args.kwargs['prompt']
        assert "print('hello')" in call_args.kwargs['prompt']
        assert "Test purpose" in call_args.kwargs['prompt']

    def test_generate_outline_uses_json_mode(self):
        """generate_outline should use JSON mode."""
        # ARRANGE
        mock_client = Mock()
        mock_response = LLMResponse(
            content='{"title": "Test", "sections": []}',
            tokens_used=100,
            model="gpt-4",
            duration_seconds=1.0
        )
        mock_client.generate.return_value = mock_response

        generator = OutlineGenerator(mock_client)

        # ACT
        generator.generate_outline({"test.py": "code"}, {"test.py": "hash"}, "Purpose")

        # ASSERT
        call_args = mock_client.generate.call_args
        assert call_args.kwargs['json_mode'] is True

    def test_generate_outline_includes_system_prompt(self):
        """generate_outline should include system prompt."""
        # ARRANGE
        mock_client = Mock()
        mock_response = LLMResponse(
            content='{"title": "Test", "sections": []}',
            tokens_used=100,
            model="gpt-4",
            duration_seconds=1.0
        )
        mock_client.generate.return_value = mock_response

        generator = OutlineGenerator(mock_client)

        # ACT
        generator.generate_outline({"test.py": "code"}, {"test.py": "hash"}, "Purpose")

        # ASSERT
        call_args = mock_client.generate.call_args
        assert call_args.kwargs['system_prompt'] is not None
        assert "documentation expert" in call_args.kwargs['system_prompt'].lower()

    def test_generate_outline_embeds_commit_hashes(self):
        """generate_outline should embed commit hashes in outline."""
        # ARRANGE
        mock_client = Mock()
        mock_response = LLMResponse(
            content='{"title": "Test", "sections": [{"heading": "Section", "sources": [{"file": "test.py"}]}]}',
            tokens_used=100,
            model="gpt-4",
            duration_seconds=1.0
        )
        mock_client.generate.return_value = mock_response

        generator = OutlineGenerator(mock_client)
        commit_hashes = {"test.py": "abc123"}

        # ACT
        outline = generator.generate_outline({"test.py": "code"}, commit_hashes, "Purpose")

        # ASSERT
        assert "_commit_hashes" in outline
        assert outline["_commit_hashes"]["test.py"] == "abc123"

    def test_generate_outline_adds_metadata(self):
        """generate_outline should add generation metadata."""
        # ARRANGE
        mock_client = Mock()
        mock_response = LLMResponse(
            content='{"title": "Test", "sections": []}',
            tokens_used=150,
            model="gpt-4",
            duration_seconds=2.5
        )
        mock_client.generate.return_value = mock_response

        generator = OutlineGenerator(mock_client)

        # ACT
        outline = generator.generate_outline({"test.py": "code"}, {"test.py": "hash"}, "Purpose")

        # ASSERT
        assert "_metadata" in outline
        assert outline["_metadata"]["model"] == "gpt-4"
        assert outline["_metadata"]["tokens_used"] == 150
        assert outline["_metadata"]["duration_seconds"] == 2.5
        assert "generated_at" in outline["_metadata"]

    def test_parse_and_validate_accepts_valid_outline(self):
        """_parse_and_validate should accept valid outline JSON."""
        # ARRANGE
        mock_client = Mock()
        generator = OutlineGenerator(mock_client)
        valid_json = '{"title": "Test Title", "sections": [{"heading": "Section 1"}]}'

        # ACT
        outline = generator._parse_and_validate(valid_json)

        # ASSERT
        assert outline["title"] == "Test Title"
        assert len(outline["sections"]) == 1
        assert outline["sections"][0]["heading"] == "Section 1"

    def test_parse_and_validate_raises_error_on_invalid_json(self):
        """_parse_and_validate should raise error on invalid JSON."""
        # ARRANGE
        mock_client = Mock()
        generator = OutlineGenerator(mock_client)
        invalid_json = '{"title": "Test", invalid json}'

        # ACT & ASSERT
        with pytest.raises(OutlineValidationError, match="invalid JSON"):
            generator._parse_and_validate(invalid_json)

    def test_parse_and_validate_raises_error_on_missing_title(self):
        """_parse_and_validate should raise error if title missing."""
        # ARRANGE
        mock_client = Mock()
        generator = OutlineGenerator(mock_client)
        missing_title = '{"sections": []}'

        # ACT & ASSERT
        with pytest.raises(OutlineValidationError, match="Missing required field: title"):
            generator._parse_and_validate(missing_title)

    def test_parse_and_validate_raises_error_on_missing_sections(self):
        """_parse_and_validate should raise error if sections missing."""
        # ARRANGE
        mock_client = Mock()
        generator = OutlineGenerator(mock_client)
        missing_sections = '{"title": "Test"}'

        # ACT & ASSERT
        with pytest.raises(OutlineValidationError, match="Missing required field: sections"):
            generator._parse_and_validate(missing_sections)

    def test_parse_and_validate_raises_error_if_sections_not_list(self):
        """_parse_and_validate should raise error if sections is not a list."""
        # ARRANGE
        mock_client = Mock()
        generator = OutlineGenerator(mock_client)
        invalid_sections = '{"title": "Test", "sections": "not a list"}'

        # ACT & ASSERT
        with pytest.raises(OutlineValidationError, match="must be a list"):
            generator._parse_and_validate(invalid_sections)

    def test_parse_and_validate_raises_error_on_section_missing_heading(self):
        """_parse_and_validate should raise error if section missing heading."""
        # ARRANGE
        mock_client = Mock()
        generator = OutlineGenerator(mock_client)
        missing_heading = '{"title": "Test", "sections": [{"topics": ["Topic 1"]}]}'

        # ACT & ASSERT
        with pytest.raises(OutlineValidationError, match="missing 'heading'"):
            generator._parse_and_validate(missing_heading)

    def test_embed_commit_hashes_adds_top_level_hashes(self):
        """_embed_commit_hashes should add top-level commit hash mapping."""
        # ARRANGE
        mock_client = Mock()
        generator = OutlineGenerator(mock_client)
        outline = {"title": "Test", "sections": []}
        commit_hashes = {"file1.py": "hash1", "file2.py": "hash2"}

        # ACT
        result = generator._embed_commit_hashes(outline, commit_hashes)

        # ASSERT
        assert result["_commit_hashes"] == commit_hashes

    def test_embed_commit_hashes_adds_to_source_references(self):
        """_embed_commit_hashes should add commit hashes to source references."""
        # ARRANGE
        mock_client = Mock()
        generator = OutlineGenerator(mock_client)
        outline = {
            "title": "Test",
            "sections": [
                {
                    "heading": "Section 1",
                    "sources": [
                        {"file": "test.py", "note": "Test note"}
                    ]
                }
            ]
        }
        commit_hashes = {"test.py": "abc123"}

        # ACT
        result = generator._embed_commit_hashes(outline, commit_hashes)

        # ASSERT
        assert result["sections"][0]["sources"][0]["commit_hash"] == "abc123"

    def test_create_prompt_truncates_large_files(self):
        """_create_prompt should truncate very large files."""
        # ARRANGE
        mock_client = Mock()
        generator = OutlineGenerator(mock_client)
        large_content = "x" * 15000  # Larger than 10,000 char limit
        source_files = {"large.py": large_content}

        # ACT
        prompt = generator._create_prompt(source_files, "Purpose")

        # ASSERT
        assert "(truncated)" in prompt
        # Should not contain full content
        assert len(prompt) < len(large_content) + 1000

    def test_create_prompt_includes_all_files(self):
        """_create_prompt should include all source files."""
        # ARRANGE
        mock_client = Mock()
        generator = OutlineGenerator(mock_client)
        source_files = {
            "file1.py": "content1",
            "file2.py": "content2",
            "file3.py": "content3"
        }

        # ACT
        prompt = generator._create_prompt(source_files, "Purpose")

        # ASSERT
        assert "file1.py" in prompt
        assert "file2.py" in prompt
        assert "file3.py" in prompt
        assert "content1" in prompt
        assert "content2" in prompt
        assert "content3" in prompt

    def test_create_prompt_includes_purpose(self):
        """_create_prompt should include documentation purpose."""
        # ARRANGE
        mock_client = Mock()
        generator = OutlineGenerator(mock_client)
        purpose = "Document the authentication module"

        # ACT
        prompt = generator._create_prompt({"test.py": "code"}, purpose)

        # ASSERT
        assert purpose in prompt
