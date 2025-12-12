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
  model: claude-3-5-sonnet-20240620  # Recommended: fast and capable
  # Other models: claude-3-opus-20240229 (most capable), claude-3-haiku-20240229 (fastest)
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

### Future commands (coming in Sprint 2+)

- `doc-gen generate-outline <doc-path>` - Generate document outline (Sprint 2)
- `doc-gen generate-doc <doc-path>` - Generate document from outline (Sprint 3)
- `doc-gen validate-sources <doc-path>` - Validate source patterns (Sprint 4)
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

## Sprint 1 Status

✅ Project structure and installation
✅ Config management (API keys, model selection)
✅ CLI framework with `init` command
✅ Metadata management (sources.yaml)
✅ Repository cloning and operations

## Next Steps

Sprint 2 will add LLM integration for outline generation.
