---
title: Streaming UI Hook
description: Progressive display for thinking blocks, tool invocations, and token usage
---

# Streaming UI Hook

Progressive display for thinking blocks, tool invocations, and token usage in the Amplifier console.

## Module ID

`hooks-streaming-ui`

## Installation

```yaml
hooks:
  - module: hooks-streaming-ui
    source: git+https://github.com/microsoft/amplifier-module-hooks-streaming-ui@main
```

## Configuration

Configure via `profile.ui` section:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `show_thinking_stream` | bool | `true` | Display thinking blocks |
| `show_tool_lines` | int | `5` | Max lines to show for tool I/O |
| `show_token_usage` | bool | `true` | Display token usage after each turn |

```yaml
ui:
  show_thinking_stream: true
  show_tool_lines: 5
  show_token_usage: true
```

## Events Hooked

| Event | Purpose | Action |
|-------|---------|--------|
| `content_block:start` | Detect thinking block start | Display "Thinking..." indicator |
| `content_block:end` | Receive complete thinking block | Display formatted thinking content |
| `tool:pre` | Tool invocation | Display tool name and arguments |
| `tool:post` | Tool result | Display success/failure with output |
| `llm:response` | LLM response received | Display token usage statistics |

## Display Format

### Thinking Blocks

```
Thinking...

============================================================
Thinking:
------------------------------------------------------------
[thinking content here]
============================================================
```

### Tool Invocations

```
Using tool: tool_name
   Arguments: {truncated arguments}

Tool result: tool_name
   {truncated output}
```

### Token Usage

```
|  Input: 1,234 | Output: 567 | Total: 1,801
```

## Features

- **Thinking block display** - Shows formatted thinking with clear boundaries
- **Tool invocation display** - Shows tool name and truncated arguments
- **Tool result display** - Shows success/failure status with truncated output
- **Token usage display** - Shows input/output/total token counts
- **Configurable truncation** - Limit tool I/O display to configured line count
- **Clean formatting** - Visual separators for better readability

## Philosophy Compliance

- **Zero kernel changes** - Pure hooks implementation
- **Pure observability** - Only displays information, no behavior changes
- **Configuration via profile** - Uses standard profile.ui settings
- **Simple, focused** - Single responsibility: console display

## Repository

**-> [GitHub](https://github.com/microsoft/amplifier-module-hooks-streaming-ui)**
