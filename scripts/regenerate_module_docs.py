#!/usr/bin/env python3
"""
Automate documentation regeneration for all documentation files.

This script:
1. Finds all MD files in docs/modules/
2. For each file:
   - Extracts intent using doc-evergreen extract-intent
   - Looks up source repo in DOC_SOURCE_MAPPING.csv
   - Clones the source repo to a temp directory
   - Generates new docs from the repo using doc-evergreen generate
   - Copies generated doc back to original location
   - Stores extracted intent and outline for reference
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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


def get_checkpoint_file(base_dir: Path) -> Path:
    """Get path to checkpoint file for tracking progress."""
    return base_dir / ".doc-evergreen" / "regeneration_checkpoint.json"


def save_checkpoint(base_dir: Path, completed_file: Path):
    """
    Save checkpoint after successful file completion.
    
    Stores the relative path of the completed file and timestamp.
    """
    checkpoint_file = get_checkpoint_file(base_dir)
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Get relative path for storage
        rel_path = completed_file.relative_to(base_dir)
        
        checkpoint_data = {
            "last_completed": str(rel_path),
            "timestamp": datetime.now().isoformat(),
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        log_info(f"Checkpoint saved: {rel_path}")
        
    except Exception as e:
        log_warning(f"Failed to save checkpoint: {e}")


def load_checkpoint(base_dir: Path) -> Optional[str]:
    """
    Load checkpoint to find last completed file.
    
    Returns relative path of last completed file or None if no checkpoint.
    """
    checkpoint_file = get_checkpoint_file(base_dir)
    
    if not checkpoint_file.exists():
        return None
    
    try:
        with open(checkpoint_file, 'r') as f:
            checkpoint_data = json.load(f)
        
        last_completed = checkpoint_data.get("last_completed")
        timestamp = checkpoint_data.get("timestamp", "unknown time")
        
        if last_completed:
            log_info(f"Found checkpoint: {last_completed} (completed at {timestamp})")
            return last_completed
        
    except Exception as e:
        log_warning(f"Failed to load checkpoint: {e}")
    
    return None


def clear_checkpoint(base_dir: Path):
    """Clear checkpoint file after successful completion of all files."""
    checkpoint_file = get_checkpoint_file(base_dir)
    
    if checkpoint_file.exists():
        try:
            checkpoint_file.unlink()
            log_info("Checkpoint cleared")
        except Exception as e:
            log_warning(f"Failed to clear checkpoint: {e}")


def find_module_docs(base_dir: Path) -> List[Path]:
    """
    Find all module documentation files.
    
    Excludes index.md files as they are catalog pages, not module-specific docs.
    """
    docs_dir = base_dir / "docs" / "modules"
    if not docs_dir.exists():
        log_error(f"Documentation directory not found: {docs_dir}")
        return []
    
    # Find all .md files recursively, excluding index.md
    module_docs = []
    for md_file in docs_dir.rglob("*.md"):
        if md_file.name != "index.md":
            module_docs.append(md_file)
    
    return sorted(module_docs)


def load_source_mapping(base_dir: Path) -> Dict[str, Dict[str, str]]:
    """
    Load DOC_SOURCE_MAPPING.csv and create a lookup dictionary.
    
    Returns dict mapping doc path to source info.
    """
    csv_path = base_dir / "docs" / "DOC_SOURCE_MAPPING.csv"
    if not csv_path.exists():
        log_error(f"Source mapping not found: {csv_path}")
        return {}
    
    mapping = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            doc_path = row['Documentation Page']
            mapping[doc_path] = {
                'sources': row['Source Files'],
                'type': row['Relationship Type'],
                'notes': row.get('Notes', '')
            }
    
    return mapping


def extract_intent(doc_path: Path, cache_dir: Path, base_dir: Path) -> Optional[str]:
    """
    Extract intent from existing documentation using doc-evergreen.
    
    Returns the extracted intent/purpose string.
    """
    log_info(f"Extracting intent from {doc_path.name}...")
    
    # Store the current directory
    original_dir = Path.cwd()
    
    try:
        # Run from base directory (repo root) so metadata goes to root .doc-evergreen/
        os.chdir(base_dir)
        
        # Get relative path from base directory to document
        rel_path = doc_path.relative_to(base_dir)
        
        result = subprocess.run(
            ["doc-evergreen", "extract-intent", str(rel_path)],
            capture_output=True,
            text=True,
            check=True
        )
        
        # The extracted intent is cached in .doc-evergreen/metadata/ at repo root
        # doc-evergreen converts the path: docs/modules/tools/bash.md -> docs-modules-tools-bash.json
        metadata_filename = str(rel_path).replace('/', '-').replace('.md', '.json')
        metadata_file = base_dir / ".doc-evergreen" / "metadata" / metadata_filename
        
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                # Intent is directly under "intent" key in the JSON
                intent = metadata.get('intent', '')
                
                if not intent:
                    log_warning(f"No intent found in metadata: {metadata_file}")
                    return None
                
                # Create module-specific cache directory
                # docs/modules/tools/bash.md -> docs-modules-tools-bash
                module_cache_name = str(rel_path).replace('/', '-').replace('.md', '')
                module_cache_dir = cache_dir / module_cache_name
                module_cache_dir.mkdir(parents=True, exist_ok=True)
                
                # Store intent in module-specific cache directory
                cache_file = module_cache_dir / f"{doc_path.stem}_intent.json"
                with open(cache_file, 'w') as cf:
                    json.dump(metadata, cf, indent=2)
                
                log_success(f"Intent extracted: {intent[:80]}...")
                return intent
        else:
            log_warning(f"Metadata file not found after extraction: {metadata_file}")
            return None
            
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to extract intent: {e.stderr}")
        return None
    finally:
        # Always return to original directory
        os.chdir(original_dir)


def extract_repo_info(source_string: str) -> Optional[Tuple[str, str]]:
    """
    Extract repository name and source file from source string.
    
    Examples:
        "amplifier-module-tool-bash/amplifier_module_tool_bash/__init__.py"
        -> ("amplifier-module-tool-bash", "amplifier_module_tool_bash/__init__.py")
        
        "amplifier-module-provider-*/README.md"
        -> None (wildcards in repo name are not supported)
    
    Returns tuple of (repo_name, source_file) or None if can't parse.
    """
    if not source_string or source_string == "N/A":
        return None
    
    # Split by | to get first source if multiple are listed
    first_source = source_string.split('|')[0].strip()
    
    # Match pattern: repo-name/path/to/file
    # Repo names typically start with "amplifier-"
    match = re.match(r'^(amplifier-[^/]+)', first_source)
    if match:
        repo_name = match.group(1)
        
        # Skip if repo name contains wildcards (can't clone these)
        # Examples: amplifier-module-provider-*, amplifier-module-tool-*
        if '*' in repo_name:
            return None
        
        # Extract the path after repo name
        source_file = first_source[len(repo_name)+1:] if len(first_source) > len(repo_name) else ""
        return (repo_name, source_file)
    
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


def generate_docs(repo_path: Path, output_name: str, intent: str) -> Optional[Path]:
    """
    Generate documentation from repository using doc-evergreen.
    
    Returns path to generated doc file or None on failure.
    """
    log_info(f"Generating documentation for {output_name}...")
    
    # Store current directory
    original_dir = Path.cwd()
    
    try:
        # Change to repo root
        os.chdir(repo_path)
        
        # Create .docignore to exclude markdown files from source analysis
        create_docignore(repo_path)
        
        # Run doc-evergreen generate
        result = subprocess.run(
            ["doc-evergreen", "generate", output_name, "--purpose", intent],
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
    repo_path: Path,
    cache_dir: Path,
    doc_name: str,
    base_dir: Path
) -> bool:
    """
    Copy generated documentation and outline to target locations.
    
    Returns True on success.
    """
    try:
        # Copy generated doc to target
        log_info(f"Copying {generated_file.name} to {target_file}")
        shutil.copy2(generated_file, target_file)
        log_success(f"Copied documentation to {target_file}")
        
        # Create module-specific cache directory
        # docs/modules/tools/bash.md -> docs-modules-tools-bash
        rel_path = target_file.relative_to(base_dir)
        module_cache_name = str(rel_path).replace('/', '-').replace('.md', '')
        module_cache_dir = cache_dir / module_cache_name
        module_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy the final generated file to cache for reference
        cache_doc_path = module_cache_dir / doc_name
        shutil.copy2(generated_file, cache_doc_path)
        log_success(f"Cached documentation to {cache_doc_path}")
        
        # Find and copy the most recent outline
        outline_dir = repo_path / ".doc-evergreen" / "outlines"
        if outline_dir.exists():
            # Find all outlines for this document
            outline_files = list(outline_dir.glob(f"{doc_name.replace('.md', '')}*.json"))
            
            if outline_files:
                # Get most recent outline (by modification time)
                latest_outline = max(outline_files, key=lambda p: p.stat().st_mtime)
                
                # Copy to module-specific cache directory
                cache_outline_path = module_cache_dir / f"{doc_name.replace('.md', '')}_outline.json"
                shutil.copy2(latest_outline, cache_outline_path)
                log_success(f"Cached outline to {cache_outline_path}")
            else:
                log_warning(f"No outline files found in {outline_dir}")
        else:
            log_warning(f"Outline directory not found: {outline_dir}")
        
        return True
        
    except Exception as e:
        log_error(f"Failed to copy files: {e}")
        return False


def process_module_doc(
    doc_path: Path,
    source_mapping: Dict[str, Dict[str, str]],
    cache_dir: Path,
    temp_dir: Path,
    base_dir: Path,
    dry_run: bool = False
) -> bool:
    """
    Process a single module documentation file.
    
    Returns True if successful.
    """
    # Ensure doc_path is absolute and resolve it
    doc_path = doc_path.resolve()
    
    try:
        relative_path = doc_path.relative_to(base_dir)
    except ValueError:
        log_error(f"File {doc_path} is not within base directory {base_dir}")
        return False
    
    log_section(f"Processing: {relative_path}")
    
    # Get relative path for lookup in CSV
    csv_key = str(relative_path).replace('\\', '/')
    
    if csv_key not in source_mapping:
        log_warning(f"No source mapping found for {csv_key}")
        return False
    
    source_info = source_mapping[csv_key]
    
    # Extract repository info
    repo_info = extract_repo_info(source_info['sources'])
    if not repo_info:
        log_warning(f"Could not extract repo info from: {source_info['sources']}")
        return False
    
    repo_name, source_file = repo_info
    log_info(f"Source repository: {repo_name}")
    
    if dry_run:
        log_info("DRY RUN: Would process this file")
        return True
    
    # Step 1: Extract intent
    intent = extract_intent(doc_path, cache_dir, base_dir)
    if not intent:
        log_error("Failed to extract intent, skipping")
        return False
    
    # Step 2: Clone repository
    repo_path = clone_repo(repo_name, temp_dir)
    if not repo_path:
        log_error("Failed to clone repository, skipping")
        return False
    
    # Step 3: Generate documentation
    generated_file = generate_docs(repo_path, doc_path.name, intent)
    if not generated_file:
        log_error("Failed to generate documentation, skipping")
        return False
    
    # Step 4: Copy generated docs and outline
    success = copy_generated_docs(
        generated_file,
        doc_path,
        repo_path,
        cache_dir,
        doc_path.name,
        base_dir
    )
    
    return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Regenerate documentation using doc-evergreen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all docs
  python scripts/regenerate_module_docs.py

  # Dry run to see what would be processed
  python scripts/regenerate_module_docs.py --dry-run

  # Process specific file
  python scripts/regenerate_module_docs.py --file docs/modules/tools/bash.md
  
  # Process specific category
  python scripts/regenerate_module_docs.py --category tools
  
  # Continue from last successful completion
  python scripts/regenerate_module_docs.py --from-csv --continue
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    parser.add_argument(
        '--file',
        type=Path,
        help='Process only this specific file'
    )
    
    parser.add_argument(
        '--directory',
        type=Path,
        help='Process all .md files in this directory (recursively)'
    )
    
    parser.add_argument(
        '--category',
        choices=['tools', 'providers', 'orchestrators', 'contexts', 'hooks'],
        help='Process only files in this category (shortcut for common directories)'
    )
    
    parser.add_argument(
        '--cache-dir',
        type=Path,
        default=Path('.doc-evergreen/amplifier-docs-cache'),
        help='Directory to store extracted intents and outlines (default: .doc-evergreen/amplifier-docs-cache)'
    )
    
    parser.add_argument(
        '--keep-repos',
        action='store_true',
        help='Keep cloned repositories in .doc-evergreen/repos/ instead of temp directory'
    )
    
    parser.add_argument(
        '--from-csv',
        action='store_true',
        help='Process all entries from DOC_SOURCE_MAPPING.csv that have valid source files'
    )
    
    parser.add_argument(
        '--continue',
        dest='continue_from_checkpoint',
        action='store_true',
        help='Continue from last successful completion (uses checkpoint file)'
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
    if not (base_dir / "docs" / "modules").exists():
        log_error("Must run from amplifier-docs repository root")
        sys.exit(1)
    
    log_section("Documentation Regeneration")
    
    # Load source mapping
    log_info("Loading DOC_SOURCE_MAPPING.csv...")
    source_mapping = load_source_mapping(base_dir)
    if not source_mapping:
        log_error("Failed to load source mapping")
        sys.exit(1)
    log_success(f"Loaded {len(source_mapping)} documentation mappings")
    
    # Validate mutually exclusive options
    options_count = sum([
        args.file is not None,
        args.directory is not None,
        args.category is not None,
        args.from_csv
    ])
    if options_count > 1:
        log_error("Cannot use --file, --directory, --category, and --from-csv together. Choose one.")
        sys.exit(1)
    
    # Find module docs to process
    if args.file:
        # Process single file
        if not args.file.exists():
            log_error(f"File not found: {args.file}")
            sys.exit(1)
        module_docs = [args.file.resolve()]
        
    elif args.directory:
        # Process all .md files in directory recursively
        if not args.directory.exists():
            log_error(f"Directory not found: {args.directory}")
            sys.exit(1)
        if not args.directory.is_dir():
            log_error(f"Not a directory: {args.directory}")
            sys.exit(1)
        
        # Find all .md files recursively, excluding index.md
        module_docs = []
        for md_file in args.directory.rglob("*.md"):
            if md_file.name != "index.md":
                module_docs.append(md_file.resolve())
        module_docs = sorted(module_docs)
        
    elif args.category:
        # Process files in specific category
        module_docs = find_module_docs(base_dir)
        module_docs = [
            doc for doc in module_docs
            if f"modules/{args.category}/" in str(doc)
        ]
        
    elif args.from_csv:
        # Process all entries from CSV that have valid source files
        log_info("Processing entries from DOC_SOURCE_MAPPING.csv...")
        module_docs = []
        skipped = []
        
        for doc_path, info in source_mapping.items():
            sources = info['sources']
            
            # Skip if no sources or N/A
            if not sources or sources.upper() == 'N/A':
                skipped.append(doc_path)
                continue
            
            # Skip if sources can't be parsed to extract repo info
            repo_info = extract_repo_info(sources)
            if not repo_info:
                skipped.append(doc_path)
                continue
            
            # Convert CSV path to actual file path
            file_path = base_dir / doc_path
            if file_path.exists():
                module_docs.append(file_path.resolve())
            else:
                log_warning(f"File listed in CSV but not found: {doc_path}")
                skipped.append(doc_path)
        
        module_docs = sorted(module_docs)
        
        if skipped:
            log_info(f"Skipped {len(skipped)} entries without valid source files")
            if len(skipped) <= 10:
                for skip in skipped:
                    log_info(f"  - {skip}")
        
    else:
        # Process all module docs
        module_docs = find_module_docs(base_dir)
    
    if not module_docs:
        log_warning("No documentation files found")
        sys.exit(0)
    
    log_success(f"Found {len(module_docs)} documentation files")
    
    # Handle --continue option: skip files up to and including last completed
    start_index = 0
    if args.continue_from_checkpoint:
        last_completed = load_checkpoint(base_dir)
        if last_completed:
            # Find the index of the last completed file
            last_completed_path = base_dir / last_completed
            try:
                # Find index of last completed file
                for i, doc_path in enumerate(module_docs):
                    if doc_path.resolve() == last_completed_path.resolve():
                        start_index = i + 1  # Start with next file
                        log_info(f"Continuing from index {start_index} (after {last_completed})")
                        break
                else:
                    log_warning(f"Last completed file not found in current list: {last_completed}")
                    log_info("Starting from beginning")
            except Exception as e:
                log_warning(f"Error processing checkpoint: {e}")
                log_info("Starting from beginning")
        else:
            log_info("No checkpoint found, starting from beginning")
    
    # Skip already-processed files if continuing
    if start_index > 0:
        skipped_count = start_index
        module_docs = module_docs[start_index:]
        log_info(f"Skipping {skipped_count} already-completed files")
        log_success(f"Processing {len(module_docs)} remaining documentation files")
    
    # Create cache directory
    cache_dir = args.cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    log_info(f"Cache directory: {cache_dir}")
    
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
        num_files = len(module_docs)
        
        # Parallel processing is incompatible with checkpointing (--continue)
        # because files must be processed in order for sequential checkpointing
        if args.continue_from_checkpoint and args.parallel:
            log_warning("Parallel processing disabled: --continue requires sequential processing")
            args.parallel = 0
        
        # Smart defaults for parallel processing
        if args.parallel == -1:  # Auto-detect
            # Use parallelism if we have 3+ files
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
            # Sequential processing (supports checkpointing)
            for doc_path in module_docs:
                try:
                    success = process_module_doc(
                        doc_path,
                        source_mapping,
                        cache_dir,
                        temp_dir,
                        base_dir,
                        args.dry_run
                    )
                    if success:
                        success_count += 1
                        # Save checkpoint after each successful completion (unless dry run)
                        if not args.dry_run:
                            save_checkpoint(base_dir, doc_path)
                    else:
                        failure_count += 1
                except Exception as e:
                    log_error(f"Unexpected error processing {doc_path.name}: {e}")
                    failure_count += 1
        else:
            # Parallel processing (no checkpointing)
            log_info(f"Processing {num_files} files in parallel with {max_workers} workers...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_path = {
                    executor.submit(
                        process_module_doc,
                        doc_path,
                        source_mapping,
                        cache_dir,
                        temp_dir,
                        base_dir,
                        args.dry_run
                    ): doc_path
                    for doc_path in module_docs
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
        
        # Clear checkpoint if all files completed successfully (sequential mode only)
        if max_workers == 1 and failure_count == 0 and not args.dry_run:
            clear_checkpoint(base_dir)
        
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
