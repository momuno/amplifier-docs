"""CLI commands for doc-gen."""

from pathlib import Path

import click

from .config import Config
from .metadata import MetadataManager
from .llm_client import OpenAIClient, AnthropicClient, LLMError
from .outline import OutlineGenerator
from .generation import DocumentGenerator, DocumentValidationError
from .repos import RepoManager


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
    """Generate outline from source files.
    
    Analyzes source repositories and generates a structured outline
    for the document using AI.
    
    Example:
      doc-gen generate-outline docs/modules/providers/openai.md
    """
    config = ctx.obj["config"]
    metadata = MetadataManager(doc_path)
    
    try:
        # 1. Load sources
        click.echo(f"Loading sources for {doc_path}...")
        sources_config = metadata.read_sources()
        
        # 2. Clone repository
        click.echo("Cloning repository...")
        with RepoManager() as repo_mgr:
            repo_url = sources_config["repositories"][0]["url"]
            repo_path = repo_mgr.clone_repo(repo_url)
            
            # 3. List and read source files
            click.echo("Reading source files...")
            include_patterns = sources_config["repositories"][0]["include"]
            file_paths = repo_mgr.list_files(repo_path, include_patterns)
            
            source_files = {}
            commit_hashes = {}
            
            for file_path in file_paths:
                full_path = repo_path / file_path
                try:
                    source_files[str(file_path)] = full_path.read_text()
                    commit_hashes[str(file_path)] = repo_mgr.get_file_commit_hash(
                        repo_path, str(file_path)
                    )
                except Exception:
                    # Skip files that can't be read (binary, etc.)
                    pass
            
            click.echo(f"✓ Read {len(source_files)} files")
            
            # 4. Generate outline
            click.echo("Generating outline with LLM...")
            
            # Select LLM client based on provider
            if config.llm_provider == "anthropic":
                llm_client = AnthropicClient(
                    api_key=config.llm_api_key,
                    model=config.llm_model,
                    timeout=config.llm_timeout,
                )
            else:  # Default to OpenAI
                llm_client = OpenAIClient(
                    api_key=config.llm_api_key,
                    model=config.llm_model,
                    timeout=config.llm_timeout,
                )
            generator = OutlineGenerator(llm_client)
            
            purpose = sources_config["metadata"]["purpose"]
            outline = generator.generate_outline(
                source_files, commit_hashes, purpose
            )
            
            # 5. Save outline
            metadata.save_outline(outline)
            
            # 6. Report success
            click.echo(f"\n✓ Outline generated successfully!")
            click.echo(f"✓ Saved to: {metadata.outline_path}")
            click.echo(f"\nMetadata:")
            click.echo(f"  Model: {outline['_metadata']['model']}")
            click.echo(f"  Tokens: {outline['_metadata']['tokens_used']}")
            click.echo(f"  Duration: {outline['_metadata']['duration_seconds']:.1f}s")
            click.echo(f"\nNext steps:")
            click.echo(f"  1. Review outline: cat {metadata.outline_path}")
            click.echo(f"  2. Generate document: doc-gen generate-doc {doc_path}")
            
    except FileNotFoundError as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    except LLMError as e:
        click.echo(f"✗ LLM Error: {e}", err=True)
        click.echo(f"\nTroubleshooting:")
        click.echo(f"  - Check API key is set correctly")
        click.echo(f"  - Try again (may be transient)")
        click.echo(f"  - Check LLM provider status")
        ctx.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        if ctx.obj.get("debug"):
            raise
        ctx.exit(2)


@cli.command()
@click.argument("doc-path", type=click.Path())
@click.pass_context
def generate_doc(ctx, doc_path: str):
    """Generate markdown document from outline.
    
    Requires outline to exist (run: doc-gen generate-outline <doc-path>)
    Document is saved to staging directory for review.
    
    Example:
      doc-gen generate-doc docs/modules/providers/openai.md
    """
    config = ctx.obj["config"]
    metadata = MetadataManager(doc_path)
    
    try:
        # 1. Load outline
        click.echo(f"Loading outline for {doc_path}...")
        outline = metadata.read_outline()
        
        # 2. Load sources config
        sources_config = metadata.read_sources()
        
        # 3. Clone repository and read files mentioned in outline
        click.echo("Cloning repository...")
        with RepoManager() as repo_mgr:
            repo_url = sources_config["repositories"][0]["url"]
            repo_path = repo_mgr.clone_repo(repo_url)
            
            # Extract files mentioned in outline
            click.echo("Reading source files mentioned in outline...")
            generator_temp = DocumentGenerator(None)
            mentioned_files = generator_temp._extract_mentioned_files(outline)
            
            source_files = {}
            for file_path in mentioned_files:
                full_path = repo_path / file_path
                if full_path.exists():
                    try:
                        source_files[file_path] = full_path.read_text()
                    except Exception:
                        # Skip files that can't be read
                        pass
            
            click.echo(f"✓ Read {len(source_files)} source files")
            
            # 4. Generate document
            click.echo("Generating document with LLM...")
            
            # Select LLM client based on provider
            if config.llm_provider == "anthropic":
                llm_client = AnthropicClient(
                    api_key=config.llm_api_key,
                    model=config.llm_model,
                    timeout=config.llm_timeout,
                )
            else:  # Default to OpenAI
                llm_client = OpenAIClient(
                    api_key=config.llm_api_key,
                    model=config.llm_model,
                    timeout=config.llm_timeout,
                )
            
            generator = DocumentGenerator(llm_client)
            
            doc_purpose = sources_config["metadata"]["purpose"]
            markdown = generator.generate_document(
                outline, source_files, doc_purpose
            )
            
            # 5. Save to staging
            staging_path = metadata.get_staging_path()
            staging_path.write_text(markdown)
            
            # 6. Report success
            click.echo(f"\n✓ Document generated successfully!")
            click.echo(f"✓ Saved to: {staging_path}")
            click.echo(f"\nDocument info:")
            click.echo(f"  Length: {len(markdown)} characters")
            click.echo(f"  Lines: {len(markdown.splitlines())}")
            click.echo(f"\nNext steps:")
            click.echo(f"  1. Review document: cat {staging_path}")
            click.echo(f"  2. If satisfied, promote to live (Sprint 5)")
            click.echo(f"  3. Or regenerate: doc-gen generate-doc {doc_path}")
            
    except FileNotFoundError as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    except LLMError as e:
        click.echo(f"✗ LLM Error: {e}", err=True)
        click.echo(f"\nTroubleshooting:")
        click.echo(f"  - Check API key is set correctly")
        click.echo(f"  - Try again (may be transient)")
        click.echo(f"  - Check LLM provider status")
        ctx.exit(1)
    except DocumentValidationError as e:
        click.echo(f"✗ Validation Error: {e}", err=True)
        click.echo(f"\nTry regenerating - LLMs are non-deterministic.")
        ctx.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        if ctx.obj.get("debug"):
            raise
        ctx.exit(2)


if __name__ == "__main__":
    cli()
