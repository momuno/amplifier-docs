# doc-gen

Multi-repository documentation generation tool with AI-powered outline and document generation.

## Installation

```bash
cd tools/doc-gen
pip install -e .
```

## Configuration

Set your Anthropic API key (recommended):

```bash
export ANTHROPIC_API_KEY=your-key-here
```

Or create a config file at `.doc-gen/config.yaml`:

```yaml
llm:
  provider: anthropic  # anthropic (default), openai (optional)
  model: claude-sonnet-4-5-20250929  # Recommended: best balance of intelligence, speed, and cost
  # Other models: claude-3-7-sonnet-20250219 (legacy)
  timeout: 60

repositories:
  # Optional: custom temp directory
  # temp_dir: /custom/temp/dir
```

**OpenAI Support** (optional): Set `provider: openai` and use `OPENAI_API_KEY` if you prefer GPT models.

## Usage

### Initialize sources for a document

```bash
doc-gen init docs/modules/providers/openai.md
```

This creates `.doc-gen/metadata/docs/modules/providers/openai/sources.yaml`.

Edit `sources.yaml` to define your source repositories and file patterns.

### Validate sources (Sprint 4)

```bash
doc-gen validate-sources docs/example.md
```

Validates source repositories and patterns, shows matched files, estimates tokens and costs.

### Generate document outline

```bash
doc-gen generate-outline docs/example.md
```

Generates structured outline with sections and source file references. Supports both single-repo and multi-repo sources.

### Generate document from outline

```bash
doc-gen generate-doc docs/example.md
```

Generates final markdown document from outline. Includes frontmatter and proper formatting.

### Debug mode

```bash
doc-gen --debug generate-outline docs/example.md
```

Saves LLM prompts and responses to `.doc-gen/debug/` for troubleshooting.

### Future commands (coming in Sprint 5+)

- `doc-gen review <doc-path>` - Review staged changes (Sprint 5)
- `doc-gen promote <doc-path>` - Promote staged to final (Sprint 5)
- `doc-gen check-changes` - Check for source changes (Sprint 5)
- `doc-gen regenerate-changed` - Regenerate changed docs (Sprint 6)

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov
```

## Current Status (v0.1.0 - Sprint 4/6)

✅ **Sprint 1**: Project structure, config management, CLI framework, repository operations  
✅ **Sprint 2**: LLM integration, outline generation, schema validation  
✅ **Sprint 3**: Document generation, debug logging, frontmatter handling  
✅ **Sprint 4**: Multi-repo support, pattern matching, source validation, cost estimation

**Test Coverage**: 73 comprehensive tests, 100% coverage for core modules

## Next Steps

Sprint 5 will add change detection and review workflow for safer documentation updates.
