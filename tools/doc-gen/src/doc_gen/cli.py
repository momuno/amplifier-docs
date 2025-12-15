"""Command-line interface for doc-gen."""

import shutil
import sys
from pathlib import Path

import click

from doc_gen.prompt_logger import PromptLogger
from doc_gen.utils import find_project_root
from doc_gen.generate.doc_generator import DocumentGenerator
from doc_gen.config import Config, create_default_config, compute_outline_path


@click.group()
@click.option('--debug-prompts', is_flag=True, help='Log all LLM prompts and responses to .doc-gen/debug/')
@click.pass_context
def cli(ctx, debug_prompts):
    """doc-gen: Documentation generation from outlines using Claude."""
    # Enable debug logging if requested
    if debug_prompts:
        project_root = find_project_root() or Path.cwd()
        PromptLogger.enable(project_root)

        log_path = PromptLogger.get_log_path()
        click.echo(f"Debug mode: Logging all prompts to {log_path}", err=True)

    # Store in context for commands to access
    ctx.ensure_object(dict)
    ctx.obj['debug_prompts'] = debug_prompts


@cli.command("generate-from-outline")
@click.argument("outline_path", type=click.Path(exists=True))
def generate_from_outline(outline_path: str):
    """Generate documentation from an existing outline JSON file.

    OUTLINE_PATH: Path to the outline.json file

    Example:
        doc-gen generate-from-outline .doc-gen/cache/docs-api-overview_outline.json
    """
    outline_path = Path(outline_path)

    if not outline_path.exists():
        click.echo(f"Error: Outline file not found: {outline_path}", err=True)
        sys.exit(1)

    # Find project root
    project_root = find_project_root() or Path.cwd()

    # Progress callback
    def progress(msg: str):
        click.echo(msg, nl=False)

    # Create generator
    generator = DocumentGenerator(
        project_root=project_root,
        progress_callback=progress
    )

    # Generate document
    try:
        click.echo(f"📄 Generating documentation from outline: {outline_path.name}\n")
        result = generator.generate_from_outline(outline_path)

        # Show summary
        char_count = len(result)
        click.echo(f"\n✨ Generation complete! ({char_count:,} characters)")

    except Exception as e:
        click.echo(f"\n❌ Error during generation: {e}", err=True)
        if PromptLogger.is_enabled():
            click.echo(f"Debug log available at: {PromptLogger.get_log_path()}", err=True)
        sys.exit(1)

    finally:
        # Close prompt logger if enabled
        if PromptLogger.is_enabled():
            PromptLogger.close()
            click.echo(f"\nDebug log saved to: {PromptLogger.get_log_path()}", err=True)


@cli.command("init")
def init():
    """Initialize doc-gen configuration.

    Creates .doc-gen/config.yaml with default settings and commented examples.
    """
    project_root = find_project_root() or Path.cwd()
    config_path = project_root / ".doc-gen" / "config.yaml"

    if config_path.exists():
        click.echo(f"Config already exists: {config_path}")
        if not click.confirm("Overwrite?"):
            sys.exit(0)

    create_default_config(project_root)
    click.echo(f"✓ Created config: {config_path}")
    click.echo(f"✓ Created storage: {project_root / '.doc-gen' / 'amplifier-docs-cache'}")


@cli.command("register-outline")
@click.argument("outline_path", type=click.Path(exists=True))
@click.argument("doc_path", type=str)
def register_outline(outline_path: str, doc_path: str):
    """Register an outline for a documentation file.

    OUTLINE_PATH: Path to the outline JSON file
    DOC_PATH: Documentation file path (e.g., docs/api/overview.md)

    Example:
        doc-gen register-outline /tmp/my-outline.json docs/api/overview.md

    This will:
    1. Copy the outline to: .doc-gen/amplifier-docs-cache/docs-api-overview/overview_outline.json
    2. Register it in .doc-gen/config.yaml
    """
    project_root = find_project_root() or Path.cwd()
    outline_path = Path(outline_path)

    # Load config
    try:
        config = Config.load(project_root)
    except FileNotFoundError:
        click.echo("Config not found. Run 'doc-gen init' first.", err=True)
        sys.exit(1)

    # Compute where outline should go
    outline_rel_path = compute_outline_path(doc_path)
    outline_full_path = project_root / config.outline_storage / outline_rel_path

    # Create parent directory
    outline_full_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy outline file
    shutil.copy2(outline_path, outline_full_path)
    click.echo(f"✓ Copied outline to: {outline_full_path.relative_to(project_root)}")

    # Register in config
    config.register_outline(doc_path, outline_rel_path)
    config.save(project_root)
    click.echo(f"✓ Registered in config: {doc_path} → {outline_rel_path}")


@cli.command("generate")
@click.argument("doc_path", type=str)
def generate(doc_path: str):
    """Generate documentation from a registered outline.

    DOC_PATH: Documentation file path (e.g., docs/api/overview.md)

    Example:
        doc-gen generate docs/api/overview.md

    This will:
    1. Look up the outline for docs/api/overview.md in .doc-gen/config.yaml
    2. Call generate-from-outline with that outline
    """
    project_root = find_project_root() or Path.cwd()

    # Load config
    try:
        config = Config.load(project_root)
    except FileNotFoundError:
        click.echo("Config not found. Run 'doc-gen init' first.", err=True)
        sys.exit(1)

    # Look up outline
    outline_path = config.get_outline_path(doc_path, project_root)
    if outline_path is None:
        click.echo(f"Error: No outline registered for: {doc_path}", err=True)
        click.echo(f"\nRegister one with: doc-gen register-outline <outline-path> {doc_path}", err=True)
        sys.exit(1)

    if not outline_path.exists():
        click.echo(f"Error: Outline file not found: {outline_path}", err=True)
        sys.exit(1)

    # Call generate-from-outline
    click.echo(f"📄 Using outline: {outline_path.relative_to(project_root)}\n")

    # Progress callback
    def progress(msg: str):
        click.echo(msg, nl=False)

    # Create generator
    generator = DocumentGenerator(
        project_root=project_root,
        progress_callback=progress
    )

    # Generate document
    try:
        result = generator.generate_from_outline(outline_path)

        # Show summary
        char_count = len(result)
        click.echo(f"\n✨ Generation complete! ({char_count:,} characters)")

    except Exception as e:
        click.echo(f"\n❌ Error during generation: {e}", err=True)
        if PromptLogger.is_enabled():
            click.echo(f"Debug log available at: {PromptLogger.get_log_path()}", err=True)
        sys.exit(1)

    finally:
        # Close prompt logger if enabled
        if PromptLogger.is_enabled():
            PromptLogger.close()
            click.echo(f"\nDebug log saved to: {PromptLogger.get_log_path()}", err=True)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
