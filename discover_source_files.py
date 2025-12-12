#!/usr/bin/env python3
"""
Source File Discovery Script for Doc Generation Recipe
Handles cloning repositories, applying filters, and discovering files
"""

import os
import sys
import hashlib
import subprocess
import fnmatch
from pathlib import Path
from typing import List, Dict, Any
import json

# Common directories to exclude
EXCLUDE_DIRS = {
    'node_modules', '.git', '__pycache__', '.pytest_cache',
    'venv', '.venv', 'env', '.env', 'build', 'dist',
    '.tox', '.eggs', '*.egg-info', '.mypy_cache',
    '.coverage', 'htmlcov', '.cache'
}

def fix_url(source: str) -> str:
    """Fix URL format if needed"""
    if source.startswith('www.github.com'):
        return 'https://' + source
    elif source.startswith('github.com'):
        return 'https://' + source
    return source

def is_remote_url(source: str) -> bool:
    """Check if source is a remote URL"""
    return any(source.startswith(prefix) for prefix in ['http://', 'https://', 'git://', 'git@'])

def generate_temp_dir(url: str) -> str:
    """Generate temporary directory path for cloned repo"""
    hash_val = hashlib.md5(url.encode()).hexdigest()[:8]
    repo_name = url.rstrip('/').split('/')[-1].replace('.git', '')
    return f"/tmp/doc-gen-{hash_val}/{repo_name}"

def clone_repository(url: str, target_dir: str) -> Dict[str, Any]:
    """Clone a repository using shallow clone"""
    result = {
        'success': False,
        'url': url,
        'target_dir': target_dir,
        'error': None
    }
    
    try:
        # Check if directory already exists and is a valid git repo
        if os.path.exists(target_dir):
            if os.path.isdir(os.path.join(target_dir, '.git')):
                print(f"✓ Repository already cloned at {target_dir}, using existing clone", file=sys.stderr)
                result['success'] = True
                return result
            else:
                # Directory exists but is not a git repo, remove it
                print(f"Removing non-git directory at {target_dir}...", file=sys.stderr)
                subprocess.run(['rm', '-rf', target_dir], check=True)
        
        # Create parent directory
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        
        # Clone with shallow clone
        print(f"Cloning {url} to {target_dir}...", file=sys.stderr)
        subprocess.run(
            ['git', 'clone', '--depth', '1', url, target_dir],
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per clone
        )
        result['success'] = True
        print(f"✓ Successfully cloned {url}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        result['error'] = "Clone operation timed out (5 minutes)"
        print(f"✗ Failed to clone {url}: timeout", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        result['error'] = f"Git clone failed: {e.stderr}"
        print(f"✗ Failed to clone {url}: {e.stderr}", file=sys.stderr)
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
        print(f"✗ Failed to clone {url}: {str(e)}", file=sys.stderr)
    
    return result

def should_exclude_dir(dir_name: str) -> bool:
    """Check if directory should be excluded"""
    return dir_name in EXCLUDE_DIRS or dir_name.startswith('.')

def match_patterns(file_path: str, patterns: List[str], base_path: str) -> bool:
    """Check if file matches any of the patterns"""
    # Get relative path from base
    try:
        rel_path = os.path.relpath(file_path, base_path)
    except ValueError:
        rel_path = file_path
    
    for pattern in patterns:
        # Handle glob patterns
        if '**' in pattern:
            # Recursive glob pattern
            parts = pattern.split('**/')
            if len(parts) == 2:
                prefix, suffix = parts
                if prefix and not rel_path.startswith(prefix.rstrip('/')):
                    continue
                # Check if any part of the path matches the suffix
                path_parts = rel_path.split(os.sep)
                for i in range(len(path_parts)):
                    sub_path = os.sep.join(path_parts[i:])
                    if fnmatch.fnmatch(sub_path, suffix):
                        return True
            else:
                # Full recursive pattern
                if fnmatch.fnmatch(rel_path, pattern.replace('**/', '*/')):
                    return True
        elif fnmatch.fnmatch(rel_path, pattern):
            return True
        elif fnmatch.fnmatch(os.path.basename(file_path), pattern):
            return True
    
    return False

def discover_files(repo_path: str, mode: str, patterns: List[str]) -> List[str]:
    """Discover files in repository based on mode and patterns"""
    discovered = []
    
    for root, dirs, files in os.walk(repo_path):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if not should_exclude_dir(d)]
        
        for file in files:
            file_path = os.path.join(root, file)
            matches = match_patterns(file_path, patterns, repo_path)
            
            if mode == 'include' and matches:
                discovered.append(file_path)
            elif mode == 'ignore' and not matches:
                discovered.append(file_path)
    
    return discovered

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get file metadata"""
    try:
        stat = os.stat(file_path)
        return {
            'path': file_path,
            'size': stat.st_size,
            'extension': Path(file_path).suffix,
            'exists': True
        }
    except Exception as e:
        return {
            'path': file_path,
            'size': 0,
            'extension': Path(file_path).suffix,
            'exists': False,
            'error': str(e)
        }

def main():
    # Parse source specification
    import yaml
    
    # Try corrected file first, fall back to original
    spec_file = 'recipes/developer-guide-sources-corrected.yaml'
    if not os.path.exists(spec_file):
        spec_file = 'recipes/developer-guide-sources.yaml'
    
    print(f"Reading source specification from: {spec_file}", file=sys.stderr)
    with open(spec_file, 'r') as f:
        spec = yaml.safe_load(f)
    
    repositories = spec.get('repositories', [])
    
    results = {
        'repositories_processed': [],
        'discovered_files': [],
        'temp_directories': [],
        'warnings': [],
        'errors': [],
        'statistics': {
            'total_repositories': len(repositories),
            'cloned_repos': 0,
            'local_repos': 0,
            'total_files': 0,
            'files_per_repo': {}
        }
    }
    
    # Process each repository
    for idx, repo in enumerate(repositories, 1):
        source = repo.get('source', '')
        mode = repo.get('mode', 'include')
        patterns = repo.get('patterns', [])
        
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Processing Repository {idx}/{len(repositories)}", file=sys.stderr)
        print(f"Source: {source}", file=sys.stderr)
        print(f"Mode: {mode}", file=sys.stderr)
        print(f"Patterns: {patterns}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        
        repo_result = {
            'original_source': source,
            'mode': mode,
            'patterns': patterns,
            'is_remote': False,
            'repo_path': None,
            'cloned': False,
            'files': [],
            'file_count': 0
        }
        
        # Fix URL if needed
        fixed_source = fix_url(source)
        
        # Determine if remote or local
        if is_remote_url(fixed_source):
            # Remote repository - clone it
            repo_result['is_remote'] = True
            temp_dir = generate_temp_dir(fixed_source)
            repo_result['temp_dir'] = temp_dir
            
            clone_result = clone_repository(fixed_source, temp_dir)
            
            if clone_result['success']:
                results['temp_directories'].append(temp_dir)
                results['statistics']['cloned_repos'] += 1
                repo_result['cloned'] = True
                repo_result['repo_path'] = temp_dir
            else:
                error_msg = f"Failed to clone {source}: {clone_result['error']}"
                results['errors'].append(error_msg)
                results['warnings'].append(f"Repository {source} skipped due to clone failure")
                results['repositories_processed'].append(repo_result)
                continue
        else:
            # Local repository
            repo_result['is_remote'] = False
            repo_path = os.path.expanduser(source)
            
            if not os.path.exists(repo_path):
                error_msg = f"Local path does not exist: {source}"
                results['errors'].append(error_msg)
                results['warnings'].append(f"Repository {source} skipped - path not found")
                results['repositories_processed'].append(repo_result)
                continue
            
            results['statistics']['local_repos'] += 1
            repo_result['repo_path'] = repo_path
        
        # Discover files
        print(f"Discovering files in {repo_result['repo_path']}...", file=sys.stderr)
        discovered = discover_files(repo_result['repo_path'], mode, patterns)
        repo_result['file_count'] = len(discovered)
        
        if len(discovered) == 0:
            warning_msg = f"Repository {source} yielded 0 files"
            results['warnings'].append(warning_msg)
            print(f"⚠ {warning_msg}", file=sys.stderr)
        else:
            print(f"✓ Discovered {len(discovered)} files", file=sys.stderr)
        
        # Collect file info
        for file_path in discovered:
            file_info = get_file_info(file_path)
            file_info['repository'] = source
            file_info['repository_path'] = repo_result['repo_path']
            file_info['is_from_clone'] = repo_result['cloned']
            repo_result['files'].append(file_path)
            results['discovered_files'].append(file_info)
        
        results['statistics']['files_per_repo'][source] = len(discovered)
        results['statistics']['total_files'] += len(discovered)
        results['repositories_processed'].append(repo_result)
    
    # Output results as JSON
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    main()
