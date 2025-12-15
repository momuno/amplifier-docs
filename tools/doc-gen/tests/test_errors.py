import pytest
from click.testing import CliRunner
import click
from doc_gen.errors import (
    DocGenError,
    ConfigError,
    SourceSpecError,
    LLMError,
    RepositoryError,
    handle_errors,
)


class TestDocGenErrorBase:
    def test_docgen_error_has_exit_code_1(self):
        error = DocGenError("test error")
        assert error.exit_code == 1

    def test_docgen_error_has_user_message(self):
        error = DocGenError("test error")
        message = error.user_message()
        assert isinstance(message, str)
        assert len(message) > 0

    def test_docgen_error_has_suggestion(self):
        error = DocGenError("test error")
        suggestion = error.suggestion()
        assert isinstance(suggestion, str)
        assert len(suggestion) > 0


class TestConfigError:
    def test_config_error_inherits_from_docgen_error(self):
        error = ConfigError("config.yaml not found")
        assert isinstance(error, DocGenError)

    def test_config_error_user_message_mentions_config(self):
        error = ConfigError("Missing API key")
        message = error.user_message()
        assert "config" in message.lower() or "api" in message.lower()

    def test_config_error_suggestion_is_actionable(self):
        error = ConfigError("Missing API key")
        suggestion = error.suggestion()
        assert len(suggestion) > 0
        assert any(word in suggestion.lower() for word in ["check", "set", "configure", "add"])

    def test_config_error_exit_code_is_1(self):
        error = ConfigError("test")
        assert error.exit_code == 1


class TestSourceSpecError:
    def test_sourcespec_error_inherits_from_docgen_error(self):
        error = SourceSpecError("Invalid pattern")
        assert isinstance(error, DocGenError)

    def test_sourcespec_error_user_message_mentions_sources(self):
        error = SourceSpecError("Invalid pattern")
        message = error.user_message()
        assert "source" in message.lower() or "pattern" in message.lower()

    def test_sourcespec_error_suggestion_is_actionable(self):
        error = SourceSpecError("Invalid pattern")
        suggestion = error.suggestion()
        assert len(suggestion) > 0
        assert any(word in suggestion.lower() for word in ["check", "validate", "verify"])

    def test_sourcespec_error_exit_code_is_1(self):
        error = SourceSpecError("test")
        assert error.exit_code == 1


class TestLLMError:
    def test_llm_error_inherits_from_docgen_error(self):
        error = LLMError("API error")
        assert isinstance(error, DocGenError)

    def test_llm_error_user_message_mentions_llm(self):
        error = LLMError("API error")
        message = error.user_message()
        assert any(word in message.lower() for word in ["llm", "api", "model"])

    def test_llm_error_suggestion_is_actionable(self):
        error = LLMError("API error")
        suggestion = error.suggestion()
        assert len(suggestion) > 0
        assert any(word in suggestion.lower() for word in ["check", "verify", "api", "key", "credit"])

    def test_llm_error_exit_code_is_2(self):
        error = LLMError("API error")
        assert error.exit_code == 2


class TestRepositoryError:
    def test_repository_error_inherits_from_docgen_error(self):
        error = RepositoryError("Clone failed")
        assert isinstance(error, DocGenError)

    def test_repository_error_user_message_mentions_repository(self):
        error = RepositoryError("Clone failed")
        message = error.user_message()
        assert any(word in message.lower() for word in ["repository", "repo", "clone", "access"])

    def test_repository_error_suggestion_is_actionable(self):
        error = RepositoryError("Clone failed")
        suggestion = error.suggestion()
        assert len(suggestion) > 0
        assert any(word in suggestion.lower() for word in ["verify", "check", "url", "auth", "network"])

    def test_repository_error_exit_code_is_1(self):
        error = RepositoryError("test")
        assert error.exit_code == 1


class TestHandleErrorsDecorator:
    def test_handle_errors_catches_docgen_error(self):
        @click.command()
        @click.pass_context
        @handle_errors
        def test_command(ctx):
            raise ConfigError("Test config error")

        runner = CliRunner()
        result = runner.invoke(test_command, obj={})

        assert result.exit_code == 1
        assert "config" in result.output.lower()

    def test_handle_errors_catches_generic_exception(self):
        @click.command()
        @click.pass_context
        @handle_errors
        def test_command(ctx):
            raise ValueError("Some unexpected error")

        runner = CliRunner()
        result = runner.invoke(test_command, obj={})

        assert result.exit_code == 1
        assert "error" in result.output.lower()
        assert "--debug" in result.output.lower()

    def test_handle_errors_shows_traceback_in_debug_mode(self):
        @click.command()
        @click.pass_context
        @handle_errors
        def test_command(ctx):
            raise ValueError("Test error")

        runner = CliRunner()
        result = runner.invoke(test_command, obj={"debug": True})

        assert result.exit_code == 1
        assert "Traceback" in result.output

    def test_handle_errors_shows_user_message_and_suggestion(self):
        @click.command()
        @click.pass_context
        @handle_errors
        def test_command(ctx):
            raise ConfigError("Missing API key")

        runner = CliRunner()
        result = runner.invoke(test_command, obj={})

        assert result.exit_code == 1
        output_lower = result.output.lower()
        assert "error" in output_lower
        assert any(word in output_lower for word in ["config", "api", "suggestion", "check", "set"])

    def test_handle_errors_respects_llm_error_exit_code(self):
        @click.command()
        @click.pass_context
        @handle_errors
        def test_command(ctx):
            raise LLMError("API timeout")

        runner = CliRunner()
        result = runner.invoke(test_command, obj={})

        assert result.exit_code == 2

    def test_handle_errors_allows_success(self):
        @click.command()
        @click.pass_context
        @handle_errors
        def test_command(ctx):
            click.echo("Success!")

        runner = CliRunner()
        result = runner.invoke(test_command, obj={})

        assert result.exit_code == 0
        assert "Success!" in result.output
