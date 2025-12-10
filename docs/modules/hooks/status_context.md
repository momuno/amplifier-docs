---
title: Status Context Hook
description: Injects environment info and git status into agent context
---

# Status Context Hook

Injects environment information (working directory, platform, OS, date) and optional git status into agent context before each prompt.

## Module ID

`hooks-status-context`

## Installation

```yaml
hooks:
  - module: hooks-status-context
    source: git+https://github.com/microsoft/amplifier-module-hooks-status-context@main
    config:
      include_git: true
      include_datetime: true
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `working_dir` | string | `.` | Working directory for operations |
| `include_git` | bool | `true` | Enable git status injection |
| `git_include_status` | bool | `true` | Show working directory status |
| `git_include_commits` | int | `5` | Recent commits count (0 to disable) |
| `git_include_branch` | bool | `true` | Show current branch |
| `git_include_main_branch` | bool | `true` | Detect and show main branch |
| `include_datetime` | bool | `true` | Show date/time |
| `datetime_include_timezone` | bool | `false` | Include timezone name |

## Output Format

### In Git Repository

```xml
<system-reminder>
Here is useful information about the environment you are running in:
<env>
Working directory: /home/user/projects/myapp
Is directory a git repo: Yes
Platform: linux
OS Version: Linux 6.6.87.2-microsoft-standard-WSL2
Today's date: 2025-11-09 14:23:45
</env>

gitStatus: This is the git status at the start of the conversation.
Current branch: feature/new-api

Main branch (you will usually use this for PRs): main

Status:
M src/api.py
?? tests/test_api.py

Recent commits:
abc1234 feat: Add new API endpoint
def5678 refactor: Simplify request handling
</system-reminder>
```

### Outside Git Repository

```xml
<system-reminder>
Here is useful information about the environment you are running in:
<env>
Working directory: /home/user/documents
Is directory a git repo: No
Platform: linux
OS Version: Linux 6.6.87.2-microsoft-standard-WSL2
Today's date: 2025-11-09 14:23:45
</env>
</system-reminder>
```

## Features

- **Fresh context** - Injected before each prompt
- **Git awareness** - Branch, status, and recent commits
- **Platform info** - OS, platform, working directory
- **Configurable** - Enable/disable each component

## Use Cases

- **Development assistance** - AI knows current branch and changes
- **Context awareness** - AI understands the working environment
- **PR workflows** - AI knows the main branch for PRs

## Repository

**-> [GitHub](https://github.com/microsoft/amplifier-module-hooks-status-context)**
