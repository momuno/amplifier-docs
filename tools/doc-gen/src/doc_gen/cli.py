"""CLI commands for doc-gen."""

from pathlib import Path

import click

from .config import Config
from .metadata import MetadataManager
from .llm_client import OpenAIClient, AnthropicClient, LLMError
from .outline import OutlineGenerator
from .generation import DocumentGenerator, DocumentValidationError
from .repos import RepoManager
from .sources import SourceParser, SourceSpecError
from .validation import SourceValidator, ValidationReport
from .change_detection import ChangeDetector
from .review import DiffGenerator


@click.group()
@click.option('--debug', is_flag=True, help='Show detailed debug information (prompts and responses)')
@click.pass_context
def cli(ctx, debug: bool):
    """Multi-repository documentation generation tool.
    
    Generates and maintains documentation from multiple source repositories
    with AI-powered outline and content generation.
    """
    # Load config and store in context
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    
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
    click.echo(f"  2. Validate: doc-gen validate-sources {doc_path}")
    click.echo(f"  3. Generate: doc-gen generate-outline {doc_path}")


@cli.command()
@click.argument("doc-path", type=click.Path())
@click.pass_context
def validate_sources(ctx, doc_path: str):
    """Validate source specifications before generation.
    
    Clones repositories, matches patterns, shows what files will be included.
    Use this before generate-outline to catch errors early.
    
    Example:
      doc-gen validate-sources docs/modules/providers/openai.md
    """
    metadata = MetadataManager(doc_path)
    
    try:
        # Load sources
        click.echo(f"Loading sources for {doc_path}...")
        
        # Parse source specs
        source_specs = SourceParser.parse_sources_yaml(metadata.sources_path)
        click.echo(f"✓ Found {len(source_specs)} repository(ies)\n")
        
        # Validate
        click.echo("Validating repositories...\n")
        
        with RepoManager() as repo_mgr:
            validator = SourceValidator(repo_mgr)
            report = validator.validate_sources(source_specs)
            
            # Display results
            _display_validation_report(report)
            
            # Exit with appropriate code
            if report.is_valid():
                click.echo("\n✓ All sources valid!")
                click.echo(f"\nNext steps:")
                click.echo(f"  doc-gen generate-outline {doc_path}")
                ctx.exit(0)
            else:
                click.echo("\n✗ Validation failed. Fix errors and try again.")
                ctx.exit(1)
                
    except SourceSpecError as e:
        click.echo(f"✗ Source specification error: {e}", err=True)
        ctx.exit(1)
    except FileNotFoundError as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        if ctx.obj.get("debug"):
            raise
        ctx.exit(2)


def _display_validation_report(report: ValidationReport):
    """Display validation report with formatting."""
    for result in report.repo_results:
        if result.success:
            click.echo(click.style(f"✓ {result.repo_name}", fg="green"))
            click.echo(f"  URL: {result.repo_url}")
            click.echo(f"  Matched files: {result.total_files}")
            
            # Show first 10 files as preview
            if result.matched_files:
                click.echo(f"  Sample files:")
                for file_path, line_count in result.matched_files[:10]:
                    click.echo(f"    - {file_path} ({line_count:,} lines)")
                
                if len(result.matched_files) > 10:
                    remaining = len(result.matched_files) - 10
                    click.echo(f"    ... and {remaining} more files")
            
            click.echo(f"  Total lines: {result.total_lines:,}")
            click.echo(f"  Estimated tokens: ~{result.estimated_tokens:,}")
            click.echo()
        else:
            click.echo(click.style(f"✗ {result.repo_name}", fg="red"))
            click.echo(f"  URL: {result.repo_url}")
            click.echo(f"  Error: {result.error_message}")
            click.echo()
    
    # Summary
    click.echo("=" * 60)
    click.echo(f"Summary:")
    click.echo(f"  Repositories: {report.successful_repos}/{report.total_repos} successful")
    if report.successful_repos > 0:
        click.echo(f"  Total files: {report.total_files:,}")
        click.echo(f"  Total lines: {report.total_lines:,}")
        click.echo(f"  Estimated tokens: ~{report.estimated_tokens:,}")
        click.echo(f"  Estimated cost: ~${report.estimated_cost_usd:.4f} (GPT-4 pricing)")


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
        # 1. Load and parse sources
        click.echo(f"Loading sources for {doc_path}...")
        source_specs = SourceParser.parse_sources_yaml(metadata.sources_path)
        sources_config = metadata.read_sources()
        click.echo(f"✓ Found {len(source_specs)} repository(ies)")
        
        # 2. Clone repositories and read source files
        click.echo("Cloning repositories...")
        source_files = {}
        commit_hashes = {}
        
        with RepoManager() as repo_mgr:
            for source_spec in source_specs:
                click.echo(f"  - {source_spec.repo_name}...")
                repo_path = repo_mgr.clone_repo(source_spec.url)
                
                # List all files in repo
                all_files = list(repo_path.rglob("*"))
                all_files = [f for f in all_files if f.is_file()]
                
                # Filter by patterns
                for file_path in all_files:
                    relative_path = file_path.relative_to(repo_path)
                    if source_spec.matches_file(str(relative_path)):
                        try:
                            # Read file content
                            content = file_path.read_text()
                            # Use repo-prefixed key for multi-repo
                            key = f"{source_spec.repo_name}/{relative_path}"
                            source_files[key] = content
                            
                            # Get commit hash
                            commit_hash = repo_mgr.get_file_commit_hash(
                                repo_path, str(relative_path)
                            )
                            commit_hashes[key] = commit_hash
                        except Exception:
                            # Skip files that can't be read (binary, etc.)
                            pass
            
            click.echo(f"✓ Read {len(source_files)} files from {len(source_specs)} repo(s)")
            
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
            
            # Enable debug mode if requested
            llm_client.set_debug(ctx.obj.get("debug", False), command_name="generate-outline")
            
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
        
        # 2. Load and parse sources
        source_specs = SourceParser.parse_sources_yaml(metadata.sources_path)
        sources_config = metadata.read_sources()
        
        # 3. Extract files mentioned in outline
        generator_temp = DocumentGenerator(None)
        mentioned_files = generator_temp._extract_mentioned_files(outline)
        
        # 4. Clone repositories and read mentioned files
        click.echo(f"Cloning {len(source_specs)} repository(ies)...")
        source_files = {}
        
        with RepoManager() as repo_mgr:
            for source_spec in source_specs:
                click.echo(f"  - {source_spec.repo_name}...")
                repo_path = repo_mgr.clone_repo(source_spec.url)
                
                # Read files mentioned in outline that match this repo
                for mentioned_file in mentioned_files:
                    # Handle both single-repo format (file.py) and multi-repo format (repo/file.py)
                    if "/" in mentioned_file and mentioned_file.startswith(source_spec.repo_name + "/"):
                        # Multi-repo format: repo/file.py
                        relative_path = mentioned_file[len(source_spec.repo_name) + 1:]
                    elif "/" not in mentioned_file or not any(mentioned_file.startswith(spec.repo_name + "/") for spec in source_specs):
                        # Single-repo format or unqualified path
                        relative_path = mentioned_file
                    else:
                        # This file belongs to a different repo
                        continue
                    
                    full_path = repo_path / relative_path
                    if full_path.exists():
                        try:
                            source_files[mentioned_file] = full_path.read_text()
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
            
            # Enable debug mode if requested
            llm_client.set_debug(ctx.obj.get("debug", False), command_name="generate-doc")
            
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


@cli.command()
@click.argument("doc-path", required=False, type=click.Path())
@click.option("--all", "check_all", is_flag=True, help="Check all documents")
@click.pass_context
def check_changes(ctx, doc_path: str, check_all: bool):
    """Detect which documents have stale sources.
    
    Compares commit hashes in outlines with current repository state.
    Shows which files changed and their commit messages.
    
    Examples:
      doc-gen check-changes docs/example.md    # Check one doc
      doc-gen check-changes --all              # Check all docs
      doc-gen check-changes                    # Same as --all
    """
    # Determine which docs to check
    if doc_path:
        docs_to_check = [Path(doc_path)]
    else:
        # Check all docs with metadata
        docs_to_check = MetadataManager.find_all_docs()
        if not docs_to_check:
            click.echo("No documents found with metadata.")
            click.echo("Initialize with: doc-gen init <doc-path>")
            ctx.exit(0)
    
    click.echo(f"Checking {len(docs_to_check)} document(s) for changes...\n")
    
    docs_with_changes = []
    docs_up_to_date = []
    docs_no_outline = []
    
    with RepoManager() as repo_mgr:
        for doc in docs_to_check:
            status = _check_single_doc(doc, repo_mgr, ctx)
            
            if status == "changes":
                docs_with_changes.append(doc)
            elif status == "up_to_date":
                docs_up_to_date.append(doc)
            else:  # "no_outline"
                docs_no_outline.append(doc)
    
    # Summary
    click.echo("\n" + "=" * 60)
    click.echo("Summary:")
    
    if docs_with_changes:
        click.echo(click.style(
            f"  ⚠  {len(docs_with_changes)} document(s) need regeneration",
            fg="yellow"
        ))
        for doc in docs_with_changes:
            click.echo(f"     - {doc}")
    
    if docs_up_to_date:
        click.echo(click.style(
            f"  ✓ {len(docs_up_to_date)} document(s) up-to-date",
            fg="green"
        ))
    
    if docs_no_outline:
        click.echo(click.style(
            f"  ✗ {len(docs_no_outline)} document(s) not yet generated",
            fg="red"
        ))
    
    if docs_with_changes:
        click.echo(f"\nRegenerate stale docs with:")
        click.echo(f"  doc-gen generate-outline <doc-path>")
        ctx.exit(1)  # Exit 1 = changes found
    else:
        ctx.exit(0)  # Exit 0 = all up-to-date


def _check_single_doc(doc_path: Path, repo_mgr: RepoManager, ctx) -> str:
    """Check a single document for changes. Returns status string."""
    metadata = MetadataManager(str(doc_path))
    
    try:
        # Load outline
        outline = metadata.read_outline()
    except FileNotFoundError:
        click.echo(f"{doc_path}")
        click.echo(click.style("  ✗ Outline not found (never generated)", fg="red"))
        click.echo()
        return "no_outline"
    
    try:
        # Load sources and clone repos
        source_specs = SourceParser.parse_sources_yaml(metadata.sources_path)
        
        # Clone repos
        repo_paths = {}
        for spec in source_specs:
            repo_path = repo_mgr.clone_repo(spec.url)
            repo_paths[spec.repo_name] = repo_path
        
        # Check for changes
        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, str(doc_path))
        
        # Display results
        click.echo(f"{doc_path}")
        
        if report.needs_regeneration():
            click.echo(click.style(
                f"  ⚠  {report.total_changes()} change(s) detected",
                fg="yellow"
            ))
            
            for change in report.changed_files:
                click.echo(f"    • {change.file_path}")
                click.echo(f"      {change.old_hash} → {change.new_hash}")
                if change.commit_message:
                    click.echo(f"      \"{change.commit_message}\"")
            
            for new_file in report.new_files:
                click.echo(f"    + {new_file} (new)")
            
            for removed_file in report.removed_files:
                click.echo(f"    - {removed_file} (removed)")
            
            click.echo(f"  ✓ {len(report.unchanged_files)} file(s) unchanged")
            click.echo()
            return "changes"
        else:
            click.echo(click.style("  ✓ All sources unchanged", fg="green"))
            generated_at = outline.get("_metadata", {}).get("generated_at", "unknown")
            click.echo(f"    Last generated: {generated_at}")
            click.echo()
            return "up_to_date"
            
    except Exception as e:
        click.echo(click.style(f"  ✗ Error: {e}", fg="red"))
        click.echo()
        return "no_outline"


@cli.command()
@click.argument("doc-path", type=click.Path())
@click.pass_context
def review(ctx, doc_path: str):
    """Review changes between staging and live documentation.
    
    Shows a unified diff of changes between the staging document
    (generated but not yet promoted) and the live document.
    
    Example:
      doc-gen review docs/modules/providers/openai.md
    """
    metadata = MetadataManager(doc_path)
    
    try:
        # Get staging and live paths
        staging_path = metadata.get_staging_path()
        live_path = Path(doc_path)
        
        # Check if staging exists
        if not staging_path.exists():
            click.echo(f"✗ Staging document not found: {staging_path}", err=True)
            click.echo(f"\nGenerate staging document first:")
            click.echo(f"  doc-gen generate-doc {doc_path}")
            ctx.exit(1)
        
        # Generate diff
        generator = DiffGenerator()
        diff_text, stats = generator.generate_diff(staging_path, live_path)
        
        # Display results
        if not diff_text:
            click.echo(click.style("✓ No changes", fg="green"))
            click.echo("Staging and live documents are identical.")
        else:
            # Show document path
            click.echo(f"Reviewing: {doc_path}")
            click.echo(f"Staging: {staging_path}")
            click.echo(f"Live: {live_path}")
            click.echo()
            
            # Show diff
            click.echo(diff_text)
            click.echo()
            
            # Show statistics
            click.echo("=" * 60)
            click.echo("Statistics:")
            click.echo(click.style(f"  + {stats['added']} line(s) added", fg="green"))
            click.echo(click.style(f"  - {stats['removed']} line(s) removed", fg="red"))
            if stats['modified'] > 0:
                click.echo(f"  ~ {stats['modified']} line(s) modified")
            
            click.echo()
            click.echo("Next steps:")
            click.echo(f"  doc-gen promote {doc_path}  # Promote to live (Sprint 5)")
        
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        if ctx.obj.get("debug"):
            raise
        ctx.exit(2)


if __name__ == "__main__":
    cli()
