# doc-gen

Simplified documentation generation tool extracted from doc-evergreen, focused on generating documentation from outlines using Anthropic Claude.

## Features

- **Generate from Outline**: Create complete documentation from structured JSON outlines
- **Claude Integration**: Uses Anthropic Claude for high-quality content generation
- **Debug Logging**: Optional `--debug-prompts` flag to log all LLM interactions
- **Hierarchical Generation**: Depth-first traversal maintains context across sections

## Installation

```bash
# From the doc-gen directory
pip install -e .
```

## Setup

### API Key

Set up your Anthropic API key using one of these methods:

**Option 1: Environment Variable**
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

**Option 2: File**
```bash
mkdir -p ~/.claude
echo "sk-ant-api03-..." > ~/.claude/api_key.txt
```

## Usage

### Generate from Outline

```bash
doc-gen generate-from-outline path/to/outline.json
```

### With Debug Logging

```bash
doc-gen --debug-prompts generate-from-outline path/to/outline.json
```

Debug logs are saved to `.doc-gen/debug/prompts-YYYYMMDD-HHMMSS.json`

## Outline Format

Outlines are JSON files with this structure:

```json
{
  "_meta": {
    "doc_type": "tutorial",
    "user_intent": "Help users get started",
    "output": "docs/getting-started.md"
  },
  "document": {
    "title": "Getting Started Guide",
    "output": "docs/getting-started.md",
    "sections": [
      {
        "heading": "# Introduction",
        "level": 1,
        "prompt": "Write an introduction...",
        "sources": [
          {
            "file": "src/main.py",
            "reasoning": "Contains the main entry point"
          }
        ],
        "sections": []
      }
    ]
  }
}
```

## Architecture

- `cli.py` - Command-line interface
- `llm_client.py` - Anthropic Claude API wrapper
- `prompt_logger.py` - Debug logging infrastructure
- `generate/doc_generator.py` - Main generation logic
- `generate/outline_models.py` - Data models for outlines

## Differences from doc-evergreen

This is a simplified extraction focused only on:
- `generate-from-outline` command
- Anthropic Claude integration
- `--debug-prompts` support

Removed features:
- OpenAI support
- Outline generation (create-outline command)
- Repository analysis
- Interactive prompts
- Other doc-evergreen commands

## Development

```bash
# Install in development mode
pip install -e .

# Test generation
doc-gen generate-from-outline test/outline.json
```
