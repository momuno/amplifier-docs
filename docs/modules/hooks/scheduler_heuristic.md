---
title: Heuristic Scheduler Hook
description: Simple heuristic-based scheduling for tool and agent selection
---

# Heuristic Scheduler Hook

Provides basic scheduling strategies for event-driven orchestration using simple heuristics.

## Module ID

`hooks-scheduler-heuristic`

## Installation

```yaml
hooks:
  - module: hooks-scheduler-heuristic
    source: git+https://github.com/microsoft/amplifier-module-hooks-scheduler-heuristic@main
    config:
      strategy: first
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `strategy` | string | `first` | Selection strategy: `first`, `round-robin`, or `random` |
| `seed` | int | - | Optional seed for reproducible random selection |

## Strategies

### First Available (`first`)

Selects the first available option. Simple and predictable.

### Round Robin (`round-robin`)

Distributes selections evenly across available options.

### Random (`random`)

Randomly selects from available options. Use `seed` for reproducibility.

## Events Handled

| Event | Purpose |
|-------|---------|
| `decision:tool_resolution` | Select tool from available options |
| `decision:agent_resolution` | Select agent for task delegation |
| `decision:context_resolution` | Decide context compaction strategy |

## Response Format

Returns `ToolResolutionResponse`, `AgentResolutionResponse`, or `ContextResolutionResponse` with:

- **Selected option** - The chosen item
- **Score** - Value between 0.0-1.0
- **Rationale** - Explanation of selection
- **Metadata** - Strategy used and selection details

## Use Cases

- **Simple deployments** - When cost optimization isn't needed
- **Testing** - Reproducible selection with seeded random
- **Load balancing** - Distribute load with round-robin

## Repository

**-> [GitHub](https://github.com/microsoft/amplifier-module-hooks-scheduler-heuristic)**
