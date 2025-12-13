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
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def get_file_commit_hash(repo_path: Path, file_path: str) -> Optional[str]:
    """
    Get the git commit hash for a specific file in the repository.
    
    Returns the commit hash or None if unable to get it.
    """
    original_dir = Path.cwd()
    
    try:
        os.chdir(repo_path)
        
        # Get the commit hash for this specific file
        result = subprocess.run(
            ["git", "log", "-n", "1", "--pretty=format:%H", "--", file_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        commit_hash = result.stdout.strip()
        return commit_hash if commit_hash else None
        
    except subprocess.CalledProcessError as e:
        log_warning(f"Failed to get commit hash for {file_path}: {e.stderr}")
        return None
    finally:
        os.chdir(original_dir)


def check_sources_changed(repo_path: Path, outline_data: dict) -> Tuple[bool, dict]:
    """
    Check if any source files in the outline have changed since last generation.
    
    Returns (has_changes, updated_outline_data):
    - has_changes: True if any sources changed or have no commit hash
    - updated_outline_data: Outline with updated commit hashes
    """
    has_changes = False
    needs_initial_hashes = False
    
    def process_sources(obj):
        """Recursively process source objects in the outline."""
        nonlocal has_changes, needs_initial_hashes
        
        if isinstance(obj, dict):
            # If this is a source object with a 'file' key
            if 'file' in obj:
                file_path = obj['file']
                current_hash = get_file_commit_hash(repo_path, file_path)
                
                if current_hash:
                    if 'commit' not in obj:
                        # No commit hash recorded - add it but mark as needing initial hash
                        obj['commit'] = current_hash
                        needs_initial_hashes = True
                        log_info(f"  Added initial commit hash for {file_path}: {current_hash[:8]}")
                    else:
                        # Compare existing hash with current hash
                        existing_hash = obj['commit']
                        if existing_hash != current_hash:
                            has_changes = True
                            log_info(f"  Changed: {file_path} ({existing_hash[:8]} → {current_hash[:8]})")
                            obj['commit'] = current_hash
                        else:
                            log_info(f"  Unchanged: {file_path} ({current_hash[:8]})")
                else:
                    log_warning(f"  Could not get commit hash for {file_path}")
            
            # Recurse into nested structures
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    process_sources(value)
        
        elif isinstance(obj, list):
            for item in obj:
                process_sources(item)
    
    # Process all sources in the outline
    outline_copy = json.loads(json.dumps(outline_data))  # Deep copy
    process_sources(outline_copy)
    
    # If we only added initial hashes and found no changes, don't regenerate
    if needs_initial_hashes and not has_changes:
        log_info("Added initial commit hashes - no regeneration needed")
        return (False, outline_copy)
    
    return (has_changes, outline_copy)


def save_outline(outline_path: Path, outline_data: dict):
    """Save updated outline data back to file."""
    try:
        with open(outline_path, 'w') as f:
            json.dump(outline_data, f, indent=2)
        log_success(f"Updated outline: {outline_path}")
    except Exception as e:
        log_error(f"Failed to save outline: {e}")


def get_output_name_from_outline(outline_path: Path) -> Optional[str]:
    """
    Extract the output filename from outline metadata.

    Returns the filename specified in _meta.output or document.output, or None if not found.
    """
    try:
        with open(outline_path, 'r') as f:
            outline_data = json.load(f)

        # Check _meta.output first, then document.output
        if '_meta' in outline_data and 'output' in outline_data['_meta']:
            return outline_data['_meta']['output']
        elif 'document' in outline_data and 'output' in outline_data['document']:
            return outline_data['document']['output']
        else:
            log_warning(f"No output filename found in outline metadata: {outline_path}")
            return None

    except Exception as e:
        log_error(f"Failed to read output name from outline {outline_path}: {e}")
        return None


def strip_repo_prefix_from_outline(outline_data: dict, repo_name: str) -> dict:
    """
    Strip repository name prefix from all file paths in the outline.

    When running doc-evergreen inside a cloned repo, file paths should be relative
    to the repo root, not include the repo name prefix.

    For example: "amplifier-core/docs/HOOKS_API.md" -> "docs/HOOKS_API.md"
    """
    repo_prefix = f"{repo_name}/"

    def process_node(obj):
        """Recursively process outline nodes to strip repo prefix from file paths."""
        if isinstance(obj, dict):
            # If this is a source object with a 'file' key
            if 'file' in obj and isinstance(obj['file'], str):
                if obj['file'].startswith(repo_prefix):
                    obj['file'] = obj['file'][len(repo_prefix):]
                    log_info(f"  Stripped prefix: {repo_prefix}{obj['file']} -> {obj['file']}")

            # Recurse into nested structures
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    process_node(value)

        elif isinstance(obj, list):
            for item in obj:
                process_node(item)

    # Deep copy and process
    outline_copy = json.loads(json.dumps(outline_data))
    process_node(outline_copy)

    return outline_copy


def generate_from_outline(repo_path: Path, outline_path: Path, expected_output_name: str, repo_name: str) -> Optional[Path]:
    """
    Generate documentation from outline using doc-evergreen.

    The output filename is specified in the outline metadata, not as a command argument.

    Returns path to generated doc file or None on failure.
    """
    log_info(f"Generating documentation from outline...")

    # Store current directory
    original_dir = Path.cwd()

    # Resolve outline_path to absolute path BEFORE changing directories
    outline_path = outline_path.resolve()

    # Read the outline and strip repo prefix from file paths
    try:
        with open(outline_path, 'r') as f:
            outline_data = json.load(f)
    except Exception as e:
        log_error(f"Failed to read outline: {e}")
        return None

    # Read the actual output filename from the outline
    actual_output_name = get_output_name_from_outline(outline_path)
    if not actual_output_name:
        log_error(f"Could not determine output filename from outline")
        return None

    log_info(f"Outline specifies output file: {actual_output_name}")

    # Strip repo name prefix from file paths in the outline
    log_info(f"Stripping '{repo_name}/' prefix from source file paths...")
    modified_outline = strip_repo_prefix_from_outline(outline_data, repo_name)

    try:
        # Change to repo root
        os.chdir(repo_path)

        # Copy modified outline file into repo directory preserving the full cache structure
        # doc-evergreen expects outlines in the same structure: .doc-evergreen/amplifier-docs-cache/...
        # We need to recreate the parent directory structure
        outline_parent_dir = outline_path.parent  # e.g., .../docs-api-cli-index/
        cache_subpath = outline_parent_dir.name  # e.g., docs-api-cli-index

        local_cache_dir = repo_path / ".doc-evergreen" / "amplifier-docs-cache" / cache_subpath
        local_cache_dir.mkdir(parents=True, exist_ok=True)

        local_outline_path = local_cache_dir / outline_path.name

        # Write the modified outline (with stripped prefixes) to the local path
        with open(local_outline_path, 'w') as f:
            json.dump(modified_outline, f, indent=2)
        log_info(f"Copied modified outline to {local_outline_path.relative_to(repo_path)}")

        # Run doc-evergreen generate-from-outline with the local path
        result = subprocess.run(
            ["doc-evergreen", "--debug-prompts", "generate-from-outline", str(local_outline_path)],
            capture_output=True,
            text=True,
            check=True
        )

        log_success(f"Generated {actual_output_name}")

        # Return path to generated file using the actual output name from outline
        generated_file = repo_path / actual_output_name
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
    dry_run: bool = False,
    only_if_changed: bool = False
) -> bool:
    """
    Process a single documentation file.
    
    If only_if_changed is True, will check git commit hashes of source files
    and only regenerate if sources have changed.
    
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
    
    # Step 4: Check if sources have changed (if requested)
    if only_if_changed:
        log_info("Checking for source file changes...")
        
        # Load the outline
        try:
            with open(outline_path, 'r') as f:
                outline_data = json.load(f)
        except Exception as e:
            log_error(f"Failed to load outline: {e}")
            return False
        
        # Check for changes
        has_changes, updated_outline = check_sources_changed(repo_path, outline_data)
        
        # Always save the updated outline (with commit hashes)
        save_outline(outline_path, updated_outline)
        
        if not has_changes:
            log_success("No source changes detected - skipping regeneration")
            return True
        
        log_info("Source changes detected - proceeding with regeneration")
    
    # Step 5: Generate documentation from outline
    generated_file = generate_from_outline(repo_path, outline_path, doc_path.name, repo_name)
    if not generated_file:
        log_error("Failed to generate documentation, skipping")
        return False
    
    # Step 6: Copy generated docs to target and cache
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
        epilog="""Examples:
  # Regenerate specific file
  python scripts/regenerate_from_outlines.py docs/architecture/overview.md

  # Regenerate entire directory
  python scripts/regenerate_from_outlines.py docs/architecture/

  # Regenerate all index.md files
  python scripts/regenerate_from_outlines.py "docs/**/index.md"

  # Regenerate multiple patterns
  python scripts/regenerate_from_outlines.py docs/architecture/ docs/community/ docs/developer/contracts/hook.md

  # Only regenerate if source files have changed
  python scripts/regenerate_from_outlines.py docs/api/ --only-if-changed

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
    
    parser.add_argument(
        '--only-if-changed',
        action='store_true',
        help='Only regenerate if source files have changed (tracks commit hashes in outline)'
    )
    
    parser.add_argument(
        '--parallel',
        type=int,
        nargs='?',
        const=-1,
        default=0,
        metavar='WORKERS',
        help='Enable parallel processing. Optionally specify number of workers (default: auto-detect based on file count and CPU cores)'
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
        # Determine parallel processing strategy
        num_files = len(doc_files)
        
        # Smart defaults for parallel processing
        if args.parallel == -1:  # Auto-detect
            # Use parallelism if we have 3+ files
            # Workers: min(num_files, cpu_count)
            if num_files >= 3:
                import multiprocessing
                max_workers = min(num_files, multiprocessing.cpu_count())
                log_info(f"Auto-detected {max_workers} workers for {num_files} files")
            else:
                max_workers = 1  # Sequential for 1-2 files
        elif args.parallel > 0:
            max_workers = args.parallel
            log_info(f"Using {max_workers} workers (explicitly set)")
        else:
            max_workers = 1  # Sequential processing
        
        # Process files
        success_count = 0
        failure_count = 0
        
        if max_workers == 1:
            # Sequential processing
            for doc_path in doc_files:
                try:
                    success = process_file(
                        doc_path,
                        args.cache_dir,
                        temp_dir,
                        base_dir,
                        args.dry_run,
                        args.only_if_changed
                    )
                    if success:
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    log_error(f"Unexpected error processing {doc_path.name}: {e}")
                    failure_count += 1
        else:
            # Parallel processing
            log_info(f"Processing {num_files} files in parallel with {max_workers} workers...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_path = {
                    executor.submit(
                        process_file,
                        doc_path,
                        args.cache_dir,
                        temp_dir,
                        base_dir,
                        args.dry_run,
                        args.only_if_changed
                    ): doc_path
                    for doc_path in doc_files
                }
                
                # Process completed tasks
                for future in as_completed(future_to_path):
                    doc_path = future_to_path[future]
                    try:
                        success = future.result()
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
