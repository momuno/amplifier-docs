---
title: Todo Reminder Hook
description: Injects todo list reminders into AI context before each LLM request
---

# Todo Reminder Hook

Automatically injects current todo state into AI's context before each LLM request, providing gentle, contextual reminders that help AI track progress.

## Module ID

`hooks-todo-reminder`

## Installation

```yaml
hooks:
  - module: hooks-todo-reminder
    source: git+https://github.com/microsoft/amplifier-module-hooks-todo-reminder@main
    config:
      inject_role: user
      priority: 10
      recent_tool_threshold: 3
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `inject_role` | string | `user` | Context injection role: `user`, `system`, or `assistant` |
| `priority` | int | `10` | Hook execution priority (higher runs after lower) |
| `recent_tool_threshold` | int | `3` | Number of recent tool calls to check for todo usage |

## How It Works

1. **Tracks tool usage** via `tool:post` events
2. **Triggers** on `provider:request` event (before each LLM call)
3. **Checks** for `coordinator.todo_state` (populated by tool-todo)
4. **Generates adaptive reminder**:
   - If todo tool not used recently: Gentle reminder to consider using it
   - If todos exist: Shows current todo list
5. **Appends to last tool result** for contextual awareness

## Injection Format

### When Todo Tool Not Used Recently

```xml
<system-reminder>
The todo tool hasn't been used recently. If you're working on tasks that would
benefit from tracking progress, consider using the todo tool to track progress.
[...]

Here are the existing contents of your todo list:
[completed] Completed task
[in_progress] In-progress task
[pending] Pending task
</system-reminder>
```

### When Todo Tool Was Used Recently

```xml
<system-reminder>
[completed] Completed task
[in_progress] In-progress task
[pending] Pending task
</system-reminder>
```

## Symbols

| Symbol | Status |
|--------|--------|
| `[completed]` | Completed task |
| `[in_progress]` | In progress (shows activeForm) |
| `[pending]` | Pending task |

## Integration with tool-todo

This hook works with `amplifier-module-tool-todo`:

```
tool-todo (storage)  +  hooks-todo-reminder (injection)  =  AI accountability
```

**Without reminder hook:**
- AI creates todos but must manually check status
- Risk: AI forgets to check during multi-step execution

**With reminder hook:**
- Hook auto-injects before every LLM call
- AI sees status at every decision point
- AI maintains awareness through complex turns

## Key Features

- **Adaptive messaging** - Adjusts based on recent tool usage
- **Contextual placement** - Appends to tool results for natural flow
- **Ephemeral injection** - Not stored in conversation history
- **Session-scoped** - Todos live only during current session
- **Graceful degradation** - Failures don't crash session

## Repository

**-> [GitHub](https://github.com/microsoft/amplifier-module-hooks-todo-reminder)**
