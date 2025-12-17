"""Command-line interface for doc-gen."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import click

from doc_gen.prompt_logger import PromptLogger
from doc_gen.utils import find_project_root
from doc_gen.generate.doc_generator import DocumentGenerator
from doc_gen.config import Config, create_default_config, compute_outline_path
from doc_gen.validate import DocumentValidator


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
@click.argument("output_path", type=str)
def generate_from_outline(outline_path: str, output_path: str):
    """Generate documentation from an existing outline JSON file.

    OUTLINE_PATH: Path to the outline.json file
    OUTPUT_PATH: Where to write the generated documentation

    Example:
        doc-gen generate-from-outline outline.json docs/api/overview.md
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
        result = generator.generate_from_outline(outline_path, output_path)

        # Show summary
        char_count = len(result)
        click.echo(f"\n✨ Generation complete! ({char_count:,} characters)")
        click.echo(f"📝 Written to: {output_path}")

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
    Also creates a sample outline at .doc-gen/examples/sample-outline.json.
    """
    project_root = find_project_root() or Path.cwd()
    config_path = project_root / ".doc-gen" / "config.yaml"

    # Handle config creation
    config_exists = config_path.exists()
    if config_exists:
        click.echo(f"Config already exists: {config_path}")
        if click.confirm("Overwrite?"):
            create_default_config(project_root)
            click.echo(f"✓ Created config: {config_path}")
            click.echo(f"✓ Created storage: {project_root / '.doc-gen' / 'amplifier-docs-cache'}")
        else:
            click.echo(f"✓ Keeping existing config: {config_path}")
    else:
        create_default_config(project_root)
        click.echo(f"✓ Created config: {config_path}")
        click.echo(f"✓ Created storage: {project_root / '.doc-gen' / 'amplifier-docs-cache'}")
    
    # Create sample outline (independently of config creation)
    sample_outline_dir = project_root / ".doc-gen" / "examples"
    sample_outline_dir.mkdir(parents=True, exist_ok=True)
    sample_outline_path = sample_outline_dir / "sample-outline.json"
    
    # Check if sample outline already exists
    if sample_outline_path.exists():
        click.echo(f"\n✓ Sample outline already exists: {sample_outline_path.relative_to(project_root)}")
    else:
        sample_outline_content = """{
  "_meta": {
    "name": "getting-started-guide",
    "document_instruction": "Write clear, concise documentation for beginners. Use code examples, bullet points, and practical guidance. Keep the tone friendly and approachable.",
    "model": "claude-sonnet-4-20250514",
    "max_response_tokens": 8000,
    "temperature": 0.2
  },
  "document": {
    "title": "Getting Started with My Project",
    "output": "docs/getting-started.md",
    "sections": [
      {
        "heading": "# Getting Started",
        "level": 1,
        "prompt": "Write a welcoming introduction to the project. Explain what users will learn in this guide and why they should use this project.",
        "sources": [
          {
            "file": "https://github.com/your-org/your-repo/blob/main/README.md",
            "reasoning": "Contains project overview and key features",
            "commit": "abc123def456"
          }
        ],
        "sections": [
          {
            "heading": "## Installation",
            "level": 2,
            "prompt": "Provide step-by-step installation instructions. Show the exact commands users need to run. Include any prerequisites.",
            "sources": [
              {
                "file": "https://github.com/your-org/your-repo/blob/main/README.md",
                "reasoning": "Contains installation instructions and prerequisites",
                "commit": "abc123def456"
              }
            ],
            "sections": []
          },
          {
            "heading": "## Quick Start",
            "level": 2,
            "prompt": "Walk users through their first task with the project. Show a complete, working example they can copy and paste. Explain what each step does.",
            "sources": [
              {
                "file": "https://github.com/your-org/your-repo/blob/main/examples/hello-world.py",
                "reasoning": "Contains a simple working example for beginners",
                "commit": "abc123def456"
              }
            ],
            "sections": []
          },
          {
            "heading": "## Next Steps",
            "level": 2,
            "prompt": "Point users to additional resources: tutorials, API documentation, community channels. Keep it brief and actionable.",
            "sources": [
              {
                "file": "https://github.com/your-org/your-repo/blob/main/README.md",
                "reasoning": "Links to additional documentation and resources",
                "commit": "abc123def456"
              }
            ],
            "sections": []
          }
        ]
      }
    ]
  }
}"""
        
        sample_outline_path.write_text(sample_outline_content)
        click.echo(f"✓ Created sample outline: {sample_outline_path.relative_to(project_root)}")


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
    2. Generate to staging area at .doc-gen/staging/<doc-path>
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

    # Calculate staging path
    staging_path = f".doc-gen/staging/{doc_path}"

    # Call generate-from-outline with staging path
    click.echo(f"📄 Using outline: {outline_path.relative_to(project_root)}\n")

    # Progress callback
    def progress(msg: str):
        click.echo(msg, nl=False)

    # Create generator
    generator = DocumentGenerator(
        project_root=project_root,
        progress_callback=progress
    )

    # Generate document to staging area
    try:
        result = generator.generate_from_outline(outline_path, staging_path)

        # Show summary
        char_count = len(result)
        click.echo(f"\n✨ Generation complete! ({char_count:,} characters)")
        click.echo(f"📝 Staged at: {staging_path}")
        click.echo(f"\n👀 Review with: cat {staging_path}")
        click.echo(f"✅ Promote with: doc-gen promote {doc_path}")

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


@cli.command("validate-update")
@click.argument("doc_path", type=str)
def validate_update(doc_path: str):
    """Validate and iteratively fix staged documentation.
    
    DOC_PATH: Documentation file path (e.g., docs/api/overview.md)
    
    Example:
        doc-gen validate-update docs/api/overview.md
    
    This command:
    1. Checks documentation completeness against outline and sources
    2. Identifies missing material (HIGH/MEDIUM/LOW priority)
    3. Automatically fixes HIGH and MEDIUM priority issues
    4. Re-checks and iterates up to 5 times
    5. Stops for human review if issues persist after 5 iterations
    """
    project_root = find_project_root() or Path.cwd()
    
    # Load config
    try:
        config = Config.load(project_root)
    except FileNotFoundError:
        click.echo("Config not found. Run 'doc-gen init' first.", err=True)
        sys.exit(1)
    
    # Build paths
    staging_path = project_root / ".doc-gen" / "staging" / doc_path
    
    # Check if staged file exists
    if not staging_path.exists():
        click.echo(f"❌ Error: No staged file found at: .doc-gen/staging/{doc_path}", err=True)
        click.echo(f"\nGenerate one first with: doc-gen generate {doc_path}", err=True)
        sys.exit(1)
    
    # Look up outline
    outline_path = config.get_outline_path(doc_path, project_root)
    if outline_path is None:
        click.echo(f"Error: No outline registered for: {doc_path}", err=True)
        sys.exit(1)
    
    if not outline_path.exists():
        click.echo(f"Error: Outline file not found: {outline_path}", err=True)
        sys.exit(1)
    
    # Progress callback
    def progress(msg: str):
        click.echo(msg)
    
    try:
        # Create validator
        validator = DocumentValidator(
            project_root=project_root,
            progress_callback=progress
        )
        
        click.echo(f"🔍 Validating and fixing: {doc_path}\n")
        click.echo(f"📄 Staged file: {staging_path.relative_to(project_root)}")
        click.echo(f"📋 Outline: {outline_path.relative_to(project_root)}")
        
        # Run validation and fixing
        result = validator.validate_and_fix(staging_path, outline_path)
        
        # Show final results
        click.echo("\n" + "=" * 80)
        click.echo("FINAL RESULTS")
        click.echo("=" * 80)
        
        if result["status"] == "PASSED":
            click.echo(f"\n✅ SUCCESS! Document passed validation after {result['iterations']} iteration(s)")
            click.echo(f"\n📝 Updated file: {staging_path.relative_to(project_root)}")
            click.echo(f"\n👀 Review changes: cat {staging_path.relative_to(project_root)}")
            click.echo(f"✅ If satisfied, promote: doc-gen promote {doc_path}")
        
        elif result["status"] == "NEEDS_REVIEW":
            click.echo(f"\n⚠️  HUMAN REVIEW REQUIRED")
            click.echo(f"\nDocument still has issues after {result['iterations']} iterations.")
            click.echo(f"\n📝 Current file: {staging_path.relative_to(project_root)}")
            click.echo(f"\nPlease review the file manually and either:")
            click.echo(f"  1. Fix remaining issues and run: doc-gen validate-update {doc_path}")
            click.echo(f"  2. Accept as-is and promote: doc-gen promote {doc_path}")
            
            # Show summary of last iteration
            last_check = result["history"][-1]["check"]
            click.echo(f"\nLast iteration found:")
            click.echo(f"  HIGH priority: {last_check['high_priority_count']}")
            click.echo(f"  MEDIUM priority: {last_check['medium_priority_count']}")
            click.echo(f"  LOW priority: {last_check['low_priority_count']}")
    
    except Exception as e:
        click.echo(f"\n❌ Error during validation: {e}", err=True)
        if PromptLogger.is_enabled():
            click.echo(f"Debug log: {PromptLogger.get_log_path()}", err=True)
        sys.exit(1)
    
    finally:
        # Close prompt logger if enabled
        if PromptLogger.is_enabled():
            PromptLogger.close()
            click.echo(f"\nDebug log saved: {PromptLogger.get_log_path()}")


@cli.command("check")
@click.argument("doc_path", type=str)
def check(doc_path: str):
    """Check staged documentation for accuracy and fix issues.
    
    DOC_PATH: Documentation file path (e.g., docs/api/overview.md)
    
    Example:
        doc-gen check docs/api/overview.md
    
    This runs an accuracy check recipe that:
    1. Validates content against the outline
    2. Checks source accuracy
    3. Fixes identified issues
    4. Verifies the fixes
    """
    project_root = find_project_root() or Path.cwd()
    
    # Load config
    try:
        config = Config.load(project_root)
    except FileNotFoundError:
        click.echo("Config not found. Run 'doc-gen init' first.", err=True)
        sys.exit(1)
    
    # Build paths
    staging_path = project_root / ".doc-gen" / "staging" / doc_path
    
    # Check if staged file exists
    if not staging_path.exists():
        click.echo(f"❌ Error: No staged file found at: .doc-gen/staging/{doc_path}", err=True)
        click.echo(f"\nGenerate one first with: doc-gen generate {doc_path}", err=True)
        sys.exit(1)
    
    # Look up outline
    outline_path = config.get_outline_path(doc_path, project_root)
    if outline_path is None:
        click.echo(f"Error: No outline registered for: {doc_path}", err=True)
        sys.exit(1)
    
    if not outline_path.exists():
        click.echo(f"Error: Outline file not found: {outline_path}", err=True)
        sys.exit(1)
    
    # Find the recipe in the tool's directory
    # The recipe is part of the tool, not the ephemeral .doc-gen directory
    tool_dir = Path(__file__).parent.parent.parent  # src/doc_gen/cli.py -> tools/doc-gen
    recipe_path = tool_dir / "recipes" / "doc-accuracy-iterative-fixer.yaml"
    
    if not recipe_path.exists():
        click.echo(f"❌ Error: Accuracy check recipe not found at: {recipe_path}", err=True)
        click.echo("\nThis is a doc-gen tool file. Please report this issue.", err=True)
        sys.exit(1)
    
    # Execute the recipe using Amplifier
    click.echo(f"🔍 Running accuracy check on: {doc_path}\n")
    click.echo(f"📄 Staged file: {staging_path.relative_to(project_root)}")
    click.echo(f"📋 Outline: {outline_path.relative_to(project_root)}\n")
    
    # Build context for recipe
    context = {
        "doc_path": doc_path,
        "staged_file": str(staging_path),
        "outline_file": str(outline_path),
        "outline_storage": str(project_root / config.outline_storage)
    }
    
    try:
        # Execute recipe via Amplifier natural language command
        # Format: amplifier run "execute <recipe> with var1=value1 and var2=value2 and ..."
        
        # Convert absolute paths to relative paths from project root
        rel_recipe_path = recipe_path.relative_to(project_root)
        rel_staged_file = staging_path.relative_to(project_root)
        rel_outline_file = outline_path.relative_to(project_root)
        rel_outline_storage = Path(config.outline_storage)
        
        # Build the natural language command with "and" separators
        run_command = (
            f"execute {rel_recipe_path} with "
            f"doc_path={doc_path} and "
            f"staged_file={rel_staged_file} and "
            f"outline_file={rel_outline_file} and "
            f"outline_storage={rel_outline_storage}"
        )
        
        cmd = [
            "amplifier",
            "run",
            run_command
        ]
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=False,  # Let output stream to terminal
            text=True
        )
        
        if result.returncode != 0:
            click.echo(f"\n❌ Recipe execution failed with exit code {result.returncode}", err=True)
            sys.exit(1)
        
        click.echo(f"\n✅ Accuracy check complete!")
        click.echo(f"📝 Updated file at: {staging_path.relative_to(project_root)}")
        click.echo(f"\n👀 Review changes: cat {staging_path.relative_to(project_root)}")
        click.echo(f"✅ If satisfied, promote with: doc-gen promote {doc_path}")
        click.echo(f"🔄 Or run check again: doc-gen check {doc_path}")
        
    except FileNotFoundError:
        click.echo("❌ Error: 'amplifier' command not found.", err=True)
        click.echo("Make sure Amplifier is installed and in your PATH.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error running recipe: {e}", err=True)
        sys.exit(1)


@cli.command("promote")
@click.argument("doc_path", type=str)
def promote(doc_path: str):
    """Promote a staged document to its final location.
    
    DOC_PATH: Documentation file path (e.g., docs/api/overview.md)
    
    Example:
        doc-gen promote docs/api/overview.md
    """
    project_root = find_project_root() or Path.cwd()
    
    # Build staging path
    staging_path = project_root / ".doc-gen" / "staging" / doc_path
    
    # Check if staged file exists
    if not staging_path.exists():
        click.echo(f"❌ Error: No staged file found at: .doc-gen/staging/{doc_path}", err=True)
        click.echo(f"\nGenerate one first with: doc-gen generate {doc_path}", err=True)
        sys.exit(1)
    
    # Build final path
    final_path = project_root / doc_path
    
    # Create parent directories if needed
    final_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy from staging to final location
    shutil.copy2(staging_path, final_path)
    
    click.echo(f"✅ Promoted: {doc_path}")
    click.echo(f"📝 Written to: {doc_path}")
    
    # Remove from staging
    staging_path.unlink()
    click.echo(f"🗑️  Removed from staging")
    
    # Clean up empty staging directories
    try:
        staging_dir = staging_path.parent
        while staging_dir != project_root / ".doc-gen" / "staging":
            if not any(staging_dir.iterdir()):
                staging_dir.rmdir()
                staging_dir = staging_dir.parent
            else:
                break
    except Exception:
        # Ignore cleanup errors
        pass


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
