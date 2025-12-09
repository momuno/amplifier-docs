# Module Documentation Regeneration Script

This directory contains automation scripts for regenerating module documentation using [doc-evergreen](https://github.com/momuno/doc-evergreen).

## Overview

The `regenerate_module_docs.py` script automates the process of regenerating documentation for all Amplifier module pages by:

1. **Extracting intent** from existing module documentation files
2. **Looking up source repositories** in `docs/DOC_SOURCE_MAPPING.csv`
3. **Cloning source repositories** from GitHub
4. **Generating fresh documentation** from the source code using doc-evergreen
5. **Copying generated docs** back to the original location
6. **Caching metadata** (intents and outlines) for reference

## Prerequisites

Before running the script, ensure you have:

1. **Python 3.11+** installed
2. **doc-evergreen** installed via pipx:
   ```bash
   pipx install git+https://github.com/momuno/doc-evergreen.git
   ```
3. **Anthropic API key** set as an environment variable:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```
4. **Git** installed for cloning repositories

## Usage

### Basic Usage

Run from the repository root directory:

```bash
# RECOMMENDED: Process all entries from DOC_SOURCE_MAPPING.csv
# This automatically skips entries with N/A or missing sources
python scripts/regenerate_module_docs.py --from-csv

# Dry run to preview what would be processed (recommended first step)
python scripts/regenerate_module_docs.py --from-csv --dry-run

# Legacy: Process all files in docs/modules/ directory
python scripts/regenerate_module_docs.py
```

### Process Specific Files or Directories

```bash
# Process a single file
python scripts/regenerate_module_docs.py --file docs/modules/tools/bash.md

# Process all files in a directory (recursively)
python scripts/regenerate_module_docs.py --directory docs/modules/tools
python scripts/regenerate_module_docs.py --directory docs/modules/providers

# Process all files in a category (shortcut for common directories)
python scripts/regenerate_module_docs.py --category tools
python scripts/regenerate_module_docs.py --category providers
```

### Available Categories

- `tools` - Tool modules (bash, filesystem, web, search, task, todo)
- `providers` - Provider modules (anthropic, openai, azure, ollama, vllm)
- `orchestrators` - Orchestrator modules (loop_basic, loop_streaming, loop_events)
- `contexts` - Context modules (simple, persistent)
- `hooks` - Hook modules (logging, approval, redaction)

### Options

```
--from-csv          Process all entries from DOC_SOURCE_MAPPING.csv (RECOMMENDED)
--dry-run           Show what would be done without making changes
--file PATH         Process only the specified file
--directory PATH    Process all .md files in this directory (recursively)
--category NAME     Process only files in the specified category (shortcut)
--cache-dir PATH    Directory for storing intents/outlines (default: .doc-evergreen/amplifier-docs-cache)
--keep-repos        Keep cloned repositories in .doc-evergreen/repos/ for inspection
```

**Note:** Options `--from-csv`, `--file`, `--directory`, and `--category` are mutually exclusive - use only one at a time.

## How It Works

### Workflow for Each Module

1. **Extract Intent**
   - Runs `doc-evergreen extract-intent` on the existing documentation
   - Caches the extracted metadata (intent, doc type, confidence)

2. **Parse Source Mapping**
   - Looks up the module in `docs/DOC_SOURCE_MAPPING.csv`
   - Extracts repository name and source file path

3. **Clone Repository**
   - Clones the source repository from `github.com/microsoft/` to a temporary directory
   - Uses shallow clone (`--depth 1`) for efficiency

4. **Generate Documentation**
   - Changes to the repository root
   - Runs `doc-evergreen generate <output-name> --purpose <intent>`
   - The tool analyzes the repository and generates comprehensive documentation

5. **Copy Results**
   - Copies the generated markdown file to replace the original
   - Copies the generated outline to the cache directory for reference

### File Structure

After running the script, you'll have an organized cache structure:

```
amplifier-docs/
├── docs/modules/
│   └── tools/
│       └── bash.md                                    # Updated with fresh content
├── .doc-evergreen/
│   ├── metadata/
│   │   └── docs-modules-tools-bash.json              # Intent metadata (from doc-evergreen)
│   ├── amplifier-docs-cache/
│   │   └── docs-modules-tools-bash/                  # Module-specific cache directory
│   │       ├── bash_intent.json                      # Cached intent metadata
│   │       ├── bash_outline.json                     # Cached outline structure
│   │       └── bash.md                               # Final generated doc (for reference)
│   └── repos/                                         # Only with --keep-repos flag
│       └── amplifier-module-tool-bash/               # Cloned source repository
│           ├── amplifier_module_tool_bash/           # Source code
│           ├── bash.md                               # Generated doc (before copy)
│           └── .doc-evergreen/
│               └── outlines/
│                   └── bash-*.json                   # Original outline
└── scripts/
    └── regenerate_module_docs.py
```

**Cache Organization:** Each module gets its own subdirectory under `amplifier-docs-cache/` named after its file path (e.g., `docs-modules-tools-bash/`). This makes it easy to find all artifacts for a specific module.

**Note:** By default, cloned repositories are stored in a temporary directory (`/tmp/`) and automatically deleted after processing. Use `--keep-repos` to keep them in `.doc-evergreen/repos/` for inspection.

## Output

The script provides colored terminal output showing:

- 🔵 **Blue (ℹ)** - Informational messages
- 🟢 **Green (✓)** - Success messages
- 🟡 **Yellow (⚠)** - Warnings
- 🔴 **Red (✗)** - Errors

### Example Output

```
Module Documentation Regeneration
ℹ Loading DOC_SOURCE_MAPPING.csv...
✓ Loaded 70 documentation mappings
✓ Found 1 module documentation files
ℹ Cache directory: .doc-evergreen/amplifier-docs-cache
ℹ Temporary directory: /tmp/tmpXXXXXXXX

Processing: docs/modules/tools/bash.md
ℹ Source repository: amplifier-module-tool-bash
ℹ Extracting intent from bash.md...
✓ Intent extracted: This document provides technical reference information...
ℹ Cloning amplifier-module-tool-bash from GitHub...
✓ Cloned amplifier-module-tool-bash
ℹ Generating documentation for bash.md...
✓ Generated bash.md
ℹ Copying bash.md to docs/modules/tools/bash.md
✓ Copied documentation to docs/modules/tools/bash.md
✓ Cached outline to .doc-evergreen/amplifier-docs-cache/outlines/bash_outline.json

Summary
✓ Successfully processed: 1
```

## Cache Directory

The script maintains a cache directory (`.doc-evergreen/amplifier-docs-cache/`) containing:

- **Intent metadata** - Extracted intent, doc type, and reasoning for each module
- **Outlines** - Generated documentation outlines showing section structure

This cache is useful for:
- Understanding what intent was used for generation
- Reviewing the document structure that was generated
- Debugging or iterating on the documentation process

## Troubleshooting

### "Command timed out"

The documentation generation can take time (30-120 seconds per file) as it calls the LLM API. This is normal. The script will continue processing and the timeout message can be ignored if the file was successfully generated.

### "No source mapping found"

Make sure the file path in `docs/DOC_SOURCE_MAPPING.csv` exactly matches the file you're trying to process.

### "Failed to clone repository"

- Check your internet connection
- Verify the repository exists at `github.com/microsoft/<repo-name>`
- Ensure you have git installed

### "Failed to extract intent"

- Make sure the file exists and is readable
- Check that doc-evergreen is properly installed
- Verify your ANTHROPIC_API_KEY is set

## Examples

### Process Everything from CSV (Recommended)

```bash
# Preview what would be processed
python scripts/regenerate_module_docs.py --from-csv --dry-run

# Process all 64 documentation files with valid sources
# (automatically skips 6 entries with N/A sources)
python scripts/regenerate_module_docs.py --from-csv
```

This is the **recommended approach** as it:
- Processes all documentation files that have source mappings
- Automatically skips entries with N/A or missing sources
- Ensures consistency with DOC_SOURCE_MAPPING.csv
- Covers the entire documentation set (64 files)

### Process all tool modules

```bash
# Using category shortcut
python scripts/regenerate_module_docs.py --category tools

# Or using directory (equivalent)
python scripts/regenerate_module_docs.py --directory docs/modules/tools
```

### Process multiple categories

```bash
# Process tools and providers (run sequentially)
python scripts/regenerate_module_docs.py --category tools
python scripts/regenerate_module_docs.py --category providers

# Or process entire modules directory at once
python scripts/regenerate_module_docs.py --directory docs/modules
```

### Preview changes for all modules

```bash
python scripts/regenerate_module_docs.py --dry-run

# Preview specific directory
python scripts/regenerate_module_docs.py --directory docs/modules/tools --dry-run
```

### Regenerate a specific module

```bash
python scripts/regenerate_module_docs.py --file docs/modules/providers/anthropic.md
```

### Keep cloned repos for inspection

```bash
# Keep repos in .doc-evergreen/repos/ instead of temp directory
python scripts/regenerate_module_docs.py --file docs/modules/tools/bash.md --keep-repos

# After it finishes, inspect the cloned repo
ls -la .doc-evergreen/repos/amplifier-module-tool-bash/
```

## Notes

- The script runs from the repository root and expects to be in the `amplifier-docs` repository
- Temporary repositories are cloned to `/tmp/` and cleaned up automatically
- The original documentation files are overwritten with the generated content
- The script processes files sequentially to avoid overwhelming the API
- Each generation call requires an API call to Anthropic's Claude model

## Integration with Git

After running the script, review the changes:

```bash
# See what files were modified
git status

# Review changes to a specific file
git diff docs/modules/tools/bash.md

# Commit the changes
git add docs/modules/
git commit -m "docs: regenerate module documentation with doc-evergreen"
```
