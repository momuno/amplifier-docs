# doc-gen: Multi-Repository Documentation Generator

Automatically generate and maintain documentation from source code across multiple repositories using AI.

## Features

- 📚 **Multi-repo support** - Document code across multiple repositories simultaneously
- 🔍 **Change detection** - Automatically detect when documentation is stale
- ✅ **Safe workflow** - Review changes before publishing with built-in diff viewer
- 🤖 **LLM-powered** - Uses GPT-4 or Claude for intelligent documentation generation
- 📝 **Two-phase pipeline** - Outline → Document for cost efficiency and control
- 🔄 **Batch operations** - Regenerate all changed docs with one command
- 💾 **Automatic backups** - Safe promotion with timestamped backups

## Quick Start

### Installation

```bash
cd tools/doc-gen
pip install -e .
```

### Setup

1. **Initialize a document**:
```bash
doc-gen init docs/my-documentation.md
```

This creates a template at `.doc-gen/metadata/docs/my-documentation.md/sources.yaml`.

2. **Set your API key**:
```bash
export OPENAI_API_KEY=your-key-here
# Or for Anthropic:
export ANTHROPIC_API_KEY=your-key-here
```

3. **Edit sources.yaml** to specify repositories and files:
```yaml
metadata:
  purpose: "Document the XYZ module functionality"

repositories:
  - name: my-repo
    url: https://github.com/owner/repo.git
    patterns:
      include:
        - "src/**/*.py"
        - "README.md"
      exclude:
        - "tests/**"
        - "**/__pycache__/**"
```

### Basic Workflow

```bash
# 1. Validate sources (verify patterns match files)
doc-gen validate-sources docs/my-documentation.md

# 2. Generate outline (structure from source code)
doc-gen generate-outline docs/my-documentation.md

# 3. Generate document (markdown from outline)
doc-gen generate-doc docs/my-documentation.md

# 4. Review changes (see diff)
doc-gen review docs/my-documentation.md

# 5. Promote to live (with backup)
doc-gen promote docs/my-documentation.md
```

### Detect Changes & Batch Regenerate

Once you have documentation set up, keep it fresh automatically:

```bash
# Check which docs need updating
doc-gen check-changes

# Preview what would be regenerated
doc-gen regenerate-changed --dry-run

# Regenerate all changed docs
doc-gen regenerate-changed

# Review and promote each
doc-gen review docs/changed-doc.md
doc-gen promote docs/changed-doc.md
```

## Commands

### `init <doc-path>`
Initialize source specification for a document.

**Example:**
```bash
doc-gen init docs/modules/providers/openai.md
```

Creates `.doc-gen/metadata/docs/modules/providers/openai.md/sources.yaml` template.

### `validate-sources <doc-path>`
Validate patterns and show what files will be included.

**Example:**
```bash
doc-gen validate-sources docs/modules/providers/openai.md
```

Shows:
- Matched files (first 10 as preview)
- Total lines of code
- Estimated token count
- Estimated cost

### `generate-outline <doc-path>`
Generate structured outline from source code using AI.

**Example:**
```bash
doc-gen generate-outline docs/modules/providers/openai.md
```

Creates `.doc-gen/metadata/docs/modules/providers/openai.md/outline.json`.

### `generate-doc <doc-path>`
Generate markdown document from outline using AI.

**Example:**
```bash
doc-gen generate-doc docs/modules/providers/openai.md
```

Creates staged document at `.doc-gen/staging/docs/modules/providers/openai.md`.

### `review <doc-path>`
Show colorized diff between staging and live documentation.

**Example:**
```bash
doc-gen review docs/modules/providers/openai.md
```

Shows:
- Diff with color highlighting (green/red)
- Statistics (lines added/removed/modified)
- Next step suggestion

### `promote <doc-path>`
Promote staged document to live location (with automatic backup).

**Example:**
```bash
doc-gen promote docs/modules/providers/openai.md
```

Actions:
- Creates timestamped backup of live doc (if exists)
- Copies staging to live location
- Shows git workflow suggestions

### `check-changes [doc-path]`
Detect which documents have stale sources.

**Examples:**
```bash
# Check specific document
doc-gen check-changes docs/modules/providers/openai.md

# Check all documents
doc-gen check-changes
doc-gen check-changes --all
```

Shows:
- Changed files with commit messages
- New files added
- Removed files
- Summary of all docs

**Exit codes:**
- 0 = No changes detected
- 1 = Changes detected

### `regenerate-changed [--dry-run]`
Regenerate all documents with source changes.

**Examples:**
```bash
# Preview what would be regenerated
doc-gen regenerate-changed --dry-run

# Regenerate all changed docs
doc-gen regenerate-changed
```

Shows:
- Progress per document (X/Y)
- Success/failure counts
- Total time and token usage
- Estimated cost
- Failed docs with error messages

## Configuration

### Global Config (.doc-gen/config.yaml)

```yaml
llm:
  provider: openai  # openai or anthropic
  model: gpt-4
  timeout: 60
```

API keys are read from environment variables:
- `OPENAI_API_KEY` for OpenAI
- `ANTHROPIC_API_KEY` for Anthropic

### Source Specification

Example `.doc-gen/metadata/<doc-path>/sources.yaml`:

```yaml
metadata:
  purpose: "Document the authentication module"

repositories:
  - name: auth-service
    url: https://github.com/company/auth-service.git
    patterns:
      include:
        - "src/**/*.py"
        - "README.md"
        - "docs/**/*.md"
      exclude:
        - "tests/**"
        - "**/__pycache__/**"
        - "**/migrations/**"
  
  - name: auth-client
    url: https://github.com/company/auth-client.git
    patterns:
      include:
        - "src/**/*.ts"
        - "src/**/*.tsx"
      exclude:
        - "**/*.test.ts"
        - "**/node_modules/**"
```

**Pattern matching:**
- Supports glob patterns (e.g., `**/*.py`, `src/*.js`)
- Include patterns are required
- Exclude patterns are optional
- Patterns are matched against relative paths within repositories

## Directory Structure

```
.doc-gen/
├── config.yaml                    # Global configuration
├── metadata/
│   └── <doc-path>/
│       ├── sources.yaml          # Source specifications
│       └── outline.json          # Generated outline
├── staging/
│   └── <doc-path>                # Staged documents (for review)
├── backups/
│   └── YYYY-MM-DD-HHMMSS-*.md   # Timestamped backups
└── repos/
    └── <repo-name>/              # Cloned repositories (cached)
```

## Troubleshooting

### "API key not found"

**Problem:** No API key configured.

**Solution:**
```bash
export OPENAI_API_KEY=your-key-here
# Or for Anthropic:
export ANTHROPIC_API_KEY=your-key-here
```

### "No matches found" during validation

**Problem:** Include patterns don't match any files.

**Solution:**
1. Check patterns with `validate-sources`
2. Verify repository URL is correct
3. Ensure patterns use correct glob syntax
4. Try broader patterns first (e.g., `*.py` before `src/**/*.py`)

### "LLM timeout"

**Problem:** Request took too long.

**Solution:**
1. Reduce source file count (use more specific patterns)
2. Increase timeout in `.doc-gen/config.yaml`:
   ```yaml
   llm:
     timeout: 120  # Increase from default 60
   ```

### "Failed to clone repository"

**Problem:** Cannot access repository.

**Solution:**
1. Verify repository URL is correct
2. Check network connection
3. For private repos:
   - Set up SSH keys: `ssh-keygen` and add to GitHub/GitLab
   - Or use HTTPS with token: `https://token@github.com/owner/repo.git`

### "Staging document not found" during review/promote

**Problem:** Document hasn't been generated yet.

**Solution:**
```bash
doc-gen generate-outline docs/my-doc.md
doc-gen generate-doc docs/my-doc.md
# Now review/promote will work
```

### Debugging issues

Run with `--debug` flag for full error details:
```bash
doc-gen --debug generate-outline docs/my-doc.md
```

## FAQ

### Q: How much does it cost?

**A:** Costs depend on source code size:
- Outline generation: ~$0.20-0.50 per doc (depending on source size)
- Document generation: ~$0.10-0.30 per doc

Use `validate-sources` to see estimated costs before generating.

### Q: Can I edit the outline before generating the document?

**A:** Yes! After running `generate-outline`, edit `.doc-gen/metadata/<doc-path>/outline.json` to customize structure, then run `generate-doc`.

### Q: How do I undo a promotion?

**A:** Restore from backup in `.doc-gen/backups/`:
```bash
cp .doc-gen/backups/YYYY-MM-DD-HHMMSS-my-doc.md docs/my-doc.md
```

### Q: Can I use with private repositories?

**A:** Yes, but you need authentication:
- SSH: Set up SSH keys and use SSH URLs (`git@github.com:owner/repo.git`)
- HTTPS: Use token in URL (`https://token@github.com/owner/repo.git`)

### Q: How often should I regenerate documentation?

**A:** Use `check-changes` to detect when sources have changed. Regenerate when:
- Source code is modified
- New features are added
- Before releases
- On a schedule (e.g., weekly)

### Q: Can I customize the LLM prompts?

**A:** Not in v0.1.0, but this is planned for v0.2.0. Current prompts are optimized for general documentation.

### Q: What LLM providers are supported?

**A:** 
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Opus)

Configure in `.doc-gen/config.yaml`:
```yaml
llm:
  provider: anthropic
  model: claude-3-5-sonnet-20241022
```

### Q: Can I generate docs for multiple languages?

**A:** Yes! Use include patterns for any file types:
```yaml
patterns:
  include:
    - "**/*.py"   # Python
    - "**/*.ts"   # TypeScript
    - "**/*.java" # Java
    - "**/*.go"   # Go
```

## Workflow Best Practices

### First-time setup
1. Start with one document to learn the workflow
2. Use `validate-sources` to verify patterns before generating
3. Review the outline and adjust if needed
4. Generate the document and review carefully
5. Promote when satisfied

### Ongoing maintenance
1. Run `check-changes` regularly (e.g., before releases)
2. Use `regenerate-changed` to update all stale docs at once
3. Review all regenerated docs before promoting
4. Commit docs with meaningful git messages

### Multi-repository projects
1. Organize related repositories in single source specifications
2. Use clear repository names (they appear in the outline)
3. Test patterns with `validate-sources` before full generation
4. Consider separate docs for different aspects (API, architecture, deployment)

## Exit Codes

All commands follow these conventions:
- `0` = Success
- `1` = User error (e.g., missing config, invalid patterns)
- `2` = System error (e.g., LLM API failure)

Useful for CI/CD scripts:
```bash
if doc-gen check-changes; then
  echo "All docs up-to-date"
else
  echo "Changes detected, regenerating..."
  doc-gen regenerate-changed
fi
```

## Examples

See example source specifications in `examples/`:
- `examples/single-repo/` - Simple single repository documentation
- `examples/multi-repo/` - Complex multi-repository documentation
- `examples/patterns/` - Common pattern use cases

## Support

For issues and questions:
- GitHub Issues: [Report bugs or request features]
- Documentation: This README and inline help (`doc-gen --help`)
- Debug mode: Run with `--debug` flag for detailed error information

## License

[Your license here]

## Version

v0.1.0 - Initial MVP release

---

**Made with [Amplifier](https://github.com/microsoft/amplifier)** 🤖
