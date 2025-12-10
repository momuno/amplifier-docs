#!/usr/bin/env python3
"""
Regenerate documentation files from existing outlines.

This script:
1. Takes file paths, directories, or glob patterns as input
2. For each matching .md file:
   - Finds its existing outline in .doc-evergreen/amplifier-docs-cache/
   - Extracts source repository information from the outline
   - Clones the source repo to a temp directory
   - Generates new docs using doc-evergreen generate-from-outline
   - Copies generated doc back to original location and cache
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def log_info(msg: str):
    """Log informational message."""
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")


def log_success(msg: str):
    """Log success message."""
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def log_warning(msg: str):
    """Log warning message."""
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def log_error(msg: str):
    """Log error message."""
    print(f"{Colors.RED}✗ {msg}{Colors.END}", file=sys.stderr)


def log_section(msg: str):
    """Log section header."""
    print(f"\n{Colors.BOLD}{msg}{Colors.END}")


def expand_patterns(base_dir: Path, patterns: List[str]) -> List[Path]:
    """
    Expand file paths, directories, and glob patterns to list of .md files.
    
    Supports:
    - Specific files: docs/architecture/overview.md
    - Directories: docs/architecture/ (finds all .md files recursively)
    - Glob patterns: docs/**/index.md, docs/architecture/*.md
    """
    all_files: Set[Path] = set()
    
    for pattern in patterns:
        pattern_path = base_dir / pattern
        
        # If it's a specific file that exists, add it
        if pattern_path.is_file() and pattern_path.suffix == '.md':
            all_files.add(pattern_path.resolve())
            continue
        
        # If it's a directory, find all .md files recursively
        if pattern_path.is_dir():
            for md_file in pattern_path.rglob("*.md"):
                all_files.add(md_file.resolve())
            continue
        
        # Otherwise treat as glob pattern
        # Use base_dir.glob for patterns
        try:
            for match in base_dir.glob(pattern):
                if match.is_file() and match.suffix == '.md':
                    all_files.add(match.resolve())
        except Exception as e:
            log_warning(f"Invalid glob pattern '{pattern}': {e}")
    
    return sorted(all_files)


def find_outline_for_file(doc_path: Path, cache_dir: Path, base_dir: Path) -> Optional[Path]:
    """
    Find the outline file for a given documentation file.
    
    Outline naming: docs/architecture/overview.md -> docs-architecture-overview_outline.json
    """
    try:
        rel_path = doc_path.relative_to(base_dir)
        # Convert path to cache directory structure
        # docs/architecture/overview.md -> docs-architecture-overview
        cache_name = str(rel_path).replace('/', '-').replace('.md', '')
        module_cache_dir = cache_dir / cache_name
        
        # Look for outline file
        outline_file = module_cache_dir / f"{doc_path.stem}_outline.json"
        
        if outline_file.exists():
            return outline_file
        else:
            log_warning(f"No outline found for {rel_path} at {outline_file}")
            return None
            
    except Exception as e:
        log_error(f"Error finding outline for {doc_path}: {e}")
        return None


def extract_repo_from_outline(outline_path: Path) -> Optional[str]:
    """
    Extract repository name from outline file.
    
    Looks for source file references in the outline to determine which repo to clone.
    Expects patterns like: amplifier-*/path/to/file
    """
    try:
        with open(outline_path, 'r') as f:
            outline_data = json.load(f)
        
        # Look through outline for source file references
        # Outlines contain a list of sections, each with source references
        source_files = []
        
        def extract_sources(obj):
            """Recursively extract source references from outline."""
            if isinstance(obj, dict):
                # Look for 'file' key in source objects
                if 'file' in obj:
                    source_files.append(obj['file'])
                # Look for 'sources' key which contains list of source objects
                if 'sources' in obj:
                    if isinstance(obj['sources'], list):
                        for source_obj in obj['sources']:
                            extract_sources(source_obj)
                # Recurse into nested structures
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        extract_sources(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_sources(item)
        
        extract_sources(outline_data)
        
        # Extract repo names from source files
        # Source files are relative paths like: amplifier_app_cli/main.py
        # We need to convert package names to repo names: amplifier_app_cli -> amplifier-app-cli
        repo_names = set()
        for source_file in source_files:
            if isinstance(source_file, str):
                # Extract first path component (package/module name)
                parts = source_file.split('/')
                if parts:
                    package_name = parts[0]
                    # Convert underscores to hyphens to get repo name
                    # amplifier_app_cli -> amplifier-app-cli
                    # amplifier_core -> amplifier-core
                    repo_name = package_name.replace('_', '-')
                    # Only keep if it looks like an amplifier repo
                    if repo_name.startswith('amplifier-'):
                        repo_names.add(repo_name)
        
        if repo_names:
            # Return first repo (most outlines reference only one repo)
            repo = sorted(repo_names)[0]
            log_info(f"Found repository: {repo}")
            return repo
        else:
            log_warning(f"No repository references found in outline: {outline_path}")
            return None
            
    except Exception as e:
        log_error(f"Failed to parse outline {outline_path}: {e}")
        return None


def clone_repo(repo_name: str, temp_dir: Path) -> Optional[Path]:
    """
    Clone repository from GitHub to temporary directory.
    
    Returns path to cloned repo or None on failure.
    """
    github_url = f"https://github.com/microsoft/{repo_name}.git"
    clone_path = temp_dir / repo_name
    
    if clone_path.exists():
        log_info(f"Repository already cloned: {repo_name}")
        return clone_path
    
    log_info(f"Cloning {repo_name} from GitHub...")
    
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", github_url, str(clone_path)],
            capture_output=True,
            text=True,
            check=True
        )
        log_success(f"Cloned {repo_name}")
        return clone_path
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to clone {repo_name}: {e.stderr}")
        return None


def create_docignore(repo_path: Path) -> bool:
    """
    Create a .docignore file in the repository to exclude markdown files and metadata.
    
    This ensures doc-evergreen only uses source truth files (code, config, etc.)
    and ignores existing documentation that may be outdated, as well as its own metadata
    and git-related files.
    
    Returns True on success.
    """
    docignore_path = repo_path / ".docignore"
    
    try:
        with open(docignore_path, 'w') as f:
            f.write("# Ignore all markdown documentation files\n")
            f.write("# We only want to generate docs from source truth (code, config, etc.)\n")
            f.write("*.md\n")
            f.write("\n")
            f.write("# Ignore metadata and configuration files\n")
            f.write(".doc-evergreen/\n")
            f.write(".git/\n")
            f.write(".gitignore\n")
            f.write(".docignore\n")
        
        log_success(f"Created .docignore to exclude *.md, .doc-evergreen/, and git files")
        return True
        
    except Exception as e:
        log_warning(f"Failed to create .docignore: {e}")
        return False


def generate_from_outline(repo_path: Path, outline_path: Path, output_name: str) -> Optional[Path]:
    """
    Generate documentation from outline using doc-evergreen.
    
    The output filename is specified in the outline metadata, not as a command argument.
    
    Returns path to generated doc file or None on failure.
    """
    log_info(f"Generating documentation from outline for {output_name}...")
    
    # Store current directory
    original_dir = Path.cwd()
    
    try:
        # Change to repo root
        os.chdir(repo_path)
        
        # Create .docignore to exclude markdown files from source analysis
        create_docignore(repo_path)
        
        # Copy outline file into repo directory so doc-evergreen can find it
        # doc-evergreen looks for outlines in .doc-evergreen/outlines/ by default
        outlines_dir = repo_path / ".doc-evergreen" / "outlines"
        outlines_dir.mkdir(parents=True, exist_ok=True)
        
        local_outline_path = outlines_dir / outline_path.name
        shutil.copy2(outline_path, local_outline_path)
        log_info(f"Copied outline to {local_outline_path.relative_to(repo_path)}")
        
        # Run doc-evergreen generate-from-outline with the local path
        result = subprocess.run(
            ["doc-evergreen", "generate-from-outline", str(local_outline_path)],
            capture_output=True,
            text=True,
            check=True
        )
        
        log_success(f"Generated {output_name}")
        
        # Return path to generated file
        generated_file = repo_path / output_name
        if generated_file.exists():
            return generated_file
        else:
            log_warning(f"Generated file not found: {generated_file}")
            return None
            
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to generate docs: {e.stderr}")
        return None
    finally:
        os.chdir(original_dir)


def copy_generated_docs(
    generated_file: Path,
    target_file: Path,
    cache_dir: Path,
    doc_name: str,
    base_dir: Path
) -> bool:
    """
    Copy generated documentation to target location and cache.
    
    Returns True on success.
    """
    try:
        # Copy generated doc to target
        log_info(f"Copying {generated_file.name} to {target_file}")
        shutil.copy2(generated_file, target_file)
        log_success(f"Copied documentation to {target_file}")
        
        # Create cache directory for this file
        rel_path = target_file.relative_to(base_dir)
        cache_name = str(rel_path).replace('/', '-').replace('.md', '')
        module_cache_dir = cache_dir / cache_name
        module_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy the final generated file to cache for reference
        cache_doc_path = module_cache_dir / doc_name
        shutil.copy2(generated_file, cache_doc_path)
        log_success(f"Cached documentation to {cache_doc_path}")
        
        return True
        
    except Exception as e:
        log_error(f"Failed to copy files: {e}")
        return False


def process_file(
    doc_path: Path,
    cache_dir: Path,
    temp_dir: Path,
    base_dir: Path,
    dry_run: bool = False
) -> bool:
    """
    Process a single documentation file.
    
    Returns True if successful.
    """
    doc_path = doc_path.resolve()
    
    try:
        relative_path = doc_path.relative_to(base_dir)
    except ValueError:
        log_error(f"File {doc_path} is not within base directory {base_dir}")
        return False
    
    log_section(f"Processing: {relative_path}")
    
    if dry_run:
        log_info("DRY RUN: Would process this file")
        return True
    
    # Step 1: Find outline
    outline_path = find_outline_for_file(doc_path, cache_dir, base_dir)
    if not outline_path:
        log_error("No outline found, skipping")
        return False
    
    # Step 2: Extract repository from outline
    repo_name = extract_repo_from_outline(outline_path)
    if not repo_name:
        log_error("Could not determine source repository from outline, skipping")
        return False
    
    # Step 3: Clone repository
    repo_path = clone_repo(repo_name, temp_dir)
    if not repo_path:
        log_error("Failed to clone repository, skipping")
        return False
    
    # Step 4: Generate documentation from outline
    generated_file = generate_from_outline(repo_path, outline_path, doc_path.name)
    if not generated_file:
        log_error("Failed to generate documentation, skipping")
        return False
    
    # Step 5: Copy generated docs to target and cache
    success = copy_generated_docs(
        generated_file,
        doc_path,
        cache_dir,
        doc_path.name,
        base_dir
    )
    
    return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Regenerate documentation from existing outlines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Regenerate specific file
  python scripts/regenerate_from_outlines.py docs/architecture/overview.md

  # Regenerate entire directory
  python scripts/regenerate_from_outlines.py docs/architecture/

  # Regenerate all index.md files
  python scripts/regenerate_from_outlines.py "docs/**/index.md"

  # Regenerate multiple patterns
  python scripts/regenerate_from_outlines.py docs/architecture/ docs/community/ docs/developer/contracts/hook.md

  # Dry run
  python scripts/regenerate_from_outlines.py docs/architecture/ --dry-run
        """
    )
    
    parser.add_argument(
        'patterns',
        nargs='+',
        help='File paths, directories, or glob patterns to process'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    parser.add_argument(
        '--cache-dir',
        type=Path,
        default=Path('.doc-evergreen/amplifier-docs-cache'),
        help='Directory containing outlines (default: .doc-evergreen/amplifier-docs-cache)'
    )
    
    parser.add_argument(
        '--keep-repos',
        action='store_true',
        help='Keep cloned repositories in .doc-evergreen/repos/ instead of temp directory'
    )
    
    args = parser.parse_args()
    
    # Determine base directory (should be repo root)
    base_dir = Path.cwd()
    if not (base_dir / "docs").exists():
        log_error("Must run from amplifier-docs repository root")
        sys.exit(1)
    
    log_section("Documentation Regeneration from Outlines")
    
    # Expand patterns to list of files
    log_info(f"Expanding patterns: {args.patterns}")
    doc_files = expand_patterns(base_dir, args.patterns)
    
    if not doc_files:
        log_warning("No documentation files found matching patterns")
        sys.exit(0)
    
    log_success(f"Found {len(doc_files)} documentation files")
    
    # Verify cache directory exists
    if not args.cache_dir.exists():
        log_error(f"Cache directory not found: {args.cache_dir}")
        log_info("Run regenerate_module_docs.py first to generate outlines")
        sys.exit(1)
    
    log_info(f"Cache directory: {args.cache_dir}")
    
    # Create directory for cloning repos
    if args.keep_repos:
        # Use persistent directory
        repos_dir = base_dir / ".doc-evergreen" / "repos"
        repos_dir.mkdir(parents=True, exist_ok=True)
        log_info(f"Repository directory: {repos_dir} (persistent)")
        temp_dir = repos_dir
        cleanup_temp = False
    else:
        # Use temporary directory that auto-cleans
        temp_dir_obj = tempfile.TemporaryDirectory()
        temp_dir = Path(temp_dir_obj.name)
        log_info(f"Repository directory: {temp_dir} (temporary)")
        cleanup_temp = True
    
    try:
        # Process each doc file
        success_count = 0
        failure_count = 0
        
        for doc_path in doc_files:
            try:
                success = process_file(
                    doc_path,
                    args.cache_dir,
                    temp_dir,
                    base_dir,
                    args.dry_run
                )
                if success:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                log_error(f"Unexpected error processing {doc_path.name}: {e}")
                failure_count += 1
        
        # Summary
        log_section("Summary")
        log_success(f"Successfully processed: {success_count}")
        if failure_count > 0:
            log_warning(f"Failed: {failure_count}")
        
        if args.dry_run:
            log_info("DRY RUN - No changes were made")
        
        if args.keep_repos:
            log_info(f"Cloned repositories kept in: {temp_dir}")
    
    finally:
        # Clean up temp directory if needed
        if cleanup_temp:
            temp_dir_obj.cleanup()


if __name__ == "__main__":
    main()
