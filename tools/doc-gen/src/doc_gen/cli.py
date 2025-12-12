"""CLI commands for doc-gen."""

from pathlib import Path

import click

from .config import Config
from .metadata import MetadataManager


@click.group()
@click.pass_context
def cli(ctx):
    """Multi-repository documentation generation tool.
    
    Generates and maintains documentation from multiple source repositories
    with AI-powered outline and content generation.
    """
    # Load config and store in context
    ctx.ensure_object(dict)
    
    try:
        # Try to load config
        config = Config.load()
        ctx.obj["config"] = config
    except FileNotFoundError:
        # Config doesn't exist yet - create template
        click.echo("No config found. Creating template at .doc-gen/config.yaml")
        Config().save()
        click.echo("Please edit config and add your API key, or set environment variable:")
        click.echo("  export OPENAI_API_KEY=your-key-here")
        click.echo("  export ANTHROPIC_API_KEY=your-key-here")
        ctx.exit(1)


@cli.command()
@click.argument("doc-path", type=click.Path())
def init(doc_path: str):
    """Initialize source specification for a document.
    
    Creates a sources.yaml template at:
      .doc-gen/metadata/{doc-path}/sources.yaml
    
    Example:
      doc-gen init docs/modules/providers/openai.md
    """
    metadata = MetadataManager(doc_path)
    metadata.init_sources()
    
    click.echo(f"✓ Initialized sources for {doc_path}")
    click.echo(f"✓ Edit: {metadata.sources_path}")
    click.echo(f"\nNext steps:")
    click.echo(f"  1. Edit sources.yaml to define repositories")
    click.echo(f"  2. Run: doc-gen generate-outline {doc_path}")


@cli.command()
@click.argument("doc-path", type=click.Path())
@click.pass_context
def generate_outline(ctx, doc_path: str):
    """Generate outline from source files (Sprint 2).
    
    Analyzes source repositories and generates a structured outline
    for the document using AI.
    
    Example:
      doc-gen generate-outline docs/modules/providers/openai.md
    """
    click.echo("Coming in Sprint 2: Outline generation")
    click.echo("This command will:")
    click.echo("  - Clone source repositories")
    click.echo("  - Extract relevant files")
    click.echo("  - Generate outline with LLM")
    click.echo("  - Save to outline.json")


@cli.command()
@click.argument("doc-path", type=click.Path())
def generate_doc(doc_path: str):
    """Generate document from outline (Sprint 3).
    
    Generates the full document content from the outline
    using AI.
    
    Example:
      doc-gen generate-doc docs/modules/providers/openai.md
    """
    click.echo("Coming in Sprint 3: Document generation")
    click.echo("This command will:")
    click.echo("  - Load outline.json")
    click.echo("  - Generate document sections with LLM")
    click.echo("  - Save to staging directory")


if __name__ == "__main__":
    cli()
