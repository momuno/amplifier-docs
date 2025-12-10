---
title: Cost-Aware Scheduler Hook
description: Cost and latency aware scheduling for tool and agent selection
---

# Cost-Aware Scheduler Hook

Optimizes tool and agent selection based on cost and latency metrics to improve performance and reduce operational costs.

## Module ID

`hooks-scheduler-cost-aware`

## Installation

```yaml
hooks:
  - module: hooks-scheduler-cost-aware
    source: git+https://github.com/microsoft/amplifier-module-hooks-scheduler-cost-aware@main
    config:
      cost_weight: 0.6
      latency_weight: 0.4
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `cost_weight` | float | `0.6` | Weight for cost optimization (0.0-1.0) |
| `latency_weight` | float | `0.4` | Weight for latency optimization (0.0-1.0) |

## Events Handled

The scheduler registers handlers for decision events:

| Event | Purpose |
|-------|---------|
| `decision:tool_resolution` | Select tool based on cost/latency optimization |
| `decision:agent_resolution` | Select agent considering resource costs |
| `decision:context_resolution` | Optimize context compaction decisions |

## Response Format

Returns resolution responses with:

- **Selected option** - The chosen tool/agent/context
- **Optimization score** - Value between 0.0-1.0
- **Cost-based rationale** - Explanation of selection
- **Metadata** - Weights used and scoring details

## Use Cases

- **Cost optimization** - Minimize API and compute costs
- **Latency optimization** - Reduce response times
- **Balanced selection** - Trade off between cost and speed
- **Budget management** - Stay within operational limits

## Repository

**-> [GitHub](https://github.com/microsoft/amplifier-module-hooks-scheduler-cost-aware)**
