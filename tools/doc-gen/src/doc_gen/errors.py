import functools
import traceback
import click


class DocGenError(Exception):
    exit_code = 1

    def user_message(self) -> str:
        return f"Error: {str(self)}"

    def suggestion(self) -> str:
        return "Please check your configuration and try again."


class ConfigError(DocGenError):
    def user_message(self) -> str:
        return f"Configuration error: {str(self)}"

    def suggestion(self) -> str:
        return "Check your config.yaml file and ensure your API key is set correctly."


class SourceSpecError(DocGenError):
    def user_message(self) -> str:
        return f"Source specification error: {str(self)}"

    def suggestion(self) -> str:
        return "Check your sources.yaml file and validate all patterns are correct."


class LLMError(DocGenError):
    exit_code = 2

    def user_message(self) -> str:
        return f"LLM API error: {str(self)}"

    def suggestion(self) -> str:
        return "Check your API key, verify you have credits remaining, and check the provider status."


class RepositoryError(DocGenError):
    def user_message(self) -> str:
        return f"Repository error: {str(self)}"

    def suggestion(self) -> str:
        return "Verify the repository URL, check your network connection, and ensure authentication is set up."


def handle_errors(func):
    @functools.wraps(func)
    def wrapper(ctx, *args, **kwargs):
        try:
            return func(ctx, *args, **kwargs)
        except DocGenError as e:
            if ctx.obj.get("debug"):
                click.echo(traceback.format_exc(), err=True)
            else:
                click.echo(f"\n{e.user_message()}", err=True)
                click.echo(f"\nSuggestion: {e.suggestion()}", err=True)
            ctx.exit(e.exit_code)
        except Exception as e:
            if ctx.obj.get("debug"):
                click.echo(traceback.format_exc(), err=True)
            else:
                click.echo(f"\nUnexpected error: {str(e)}", err=True)
                click.echo(f"\nRun with --debug flag for full traceback.", err=True)
            ctx.exit(1)

    return wrapper
