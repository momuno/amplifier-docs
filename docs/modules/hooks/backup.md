---
title: Backup Hook
description: Transcript backup and preservation for Amplifier sessions
---

# Backup Hook

Automatically saves conversation transcripts to persistent storage for backup, audit, or replay purposes.

## Module ID

`hooks-backup`

## Installation

```yaml
hooks:
  - module: hooks-backup
    source: git+https://github.com/microsoft/amplifier-module-hooks-backup@main
    config:
      backup_dir: .amplifier/transcripts
      compress: false
      format: json
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `backup_dir` | string | `.amplifier/transcripts` | Directory for backup files |
| `compress` | bool | `false` | Enable compression for backup files |
| `format` | string | `json` | Output format: `json` or `text` |

## Features

- **Automatic backup** - Saves transcripts after each turn
- **Configurable location** - Choose where backups are stored
- **Optional compression** - Reduce storage footprint
- **Timestamped naming** - Easy identification and chronological ordering
- **Safe file handling** - Atomic writes prevent corruption
- **Error recovery** - Graceful handling of write failures

## Use Cases

- **Audit trails** - Maintain records of AI interactions
- **Debugging** - Replay sessions to diagnose issues
- **Analytics** - Analyze conversation patterns
- **Compliance** - Meet data retention requirements

## Behavior

The hook listens to session events and persists conversation state:

1. Triggers on turn completion events
2. Serializes current transcript
3. Writes to configured backup directory
4. Applies compression if enabled

## Repository

**-> [GitHub](https://github.com/microsoft/amplifier-module-hooks-backup)**
