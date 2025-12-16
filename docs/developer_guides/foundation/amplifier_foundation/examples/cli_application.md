---
title: CLI Application Example
description: Building production CLI tools with best practices
---

# CLI Application Example

Learn how to build production-ready CLI applications with Amplifier - proper architecture, error handling, logging, configuration management, and lifecycle management.

## What This Example Demonstrates

- **Application Architecture**: Encapsulating Amplifier in reusable classes
- **Configuration Management**: Environment variables, settings, validation
- **Error Handling**: Graceful failures and recovery
- **Logging**: Structured logging with proper levels
- **Session Lifecycle**: Initialization, execution, cleanup
- **CLI Patterns**: Interactive mode and single-prompt mode

**Time to Complete**: 15 minutes  
**Complexity**: ⭐⭐ Intermediate

## Running the Example

```bash
# Clone the repository
git clone https://github.com/microsoft/amplifier-foundation
cd amplifier-foundation

# Set your API key
export ANTHROPIC_API_KEY='your-key-here'

# Interactive mode
uv run python examples/08_cli_application.py

# Single prompt mode
uv run python examples/08_cli_application.py "Your prompt here"
```

[:material-github: View Full Source Code](https://github.com/microsoft/amplifier-foundation/blob/main/examples/08_cli_application.py){ .md-button }

## How It Works

This example shows **production-ready patterns** for building CLI tools with Amplifier.

### Architecture Overview

```python
class AmplifierApp:
    """Application class encapsulating Amplifier."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.session = None
        self.logger = self._setup_logging()
    
    async def initialize(self):
        """Load bundles, prepare, create session"""
        
    async def execute(self, prompt: str) -> str:
        """Execute a prompt"""
        
    async def shutdown(self):
        """Cleanup resources"""
```

**Why this pattern?**
- Encapsulates Amplifier complexity
- Reusable across multiple applications
- Testable with mocks
- Clear initialization/cleanup lifecycle

### Configuration Management

```python
@dataclass
class AppConfig:
    """Application configuration"""
    provider_bundle: str = "anthropic-sonnet.yaml"
    api_key: str | None = None
    log_level: str = "INFO"
    storage_path: Path = Path.home() / ".amplifier" / "app_sessions"
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load from environment variables"""
        return cls(
            provider_bundle=os.getenv("PROVIDER", "anthropic-sonnet.yaml"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
    
    def validate(self) -> None:
        """Validate configuration before use"""
        if not self.api_key:
            raise ValueError("API key not set")
```

**Configuration sources** (in order of precedence):
1. Environment variables
2. Config files (`.amplifier/settings.yaml`)
3. Command-line arguments
4. Defaults

Learn more: [Config Library](/libraries/config.md)

### Error Handling Pattern

```python
async def execute(self, prompt: str) -> str:
    try:
        self.logger.info(f"Executing: {prompt[:100]}...")
        response = await self.session.execute(prompt)
        self.logger.info("Execution completed")
        return response
        
    except Exception as e:
        self.logger.error(f"Execution failed: {e}", exc_info=True)
        # In production:
        # - Retry with exponential backoff
        # - Fallback to simpler model
        # - Return user-friendly error message
        raise
```

**Error handling strategies**:
- Log errors with full context (`exc_info=True`)
- Distinguish transient vs permanent failures
- Provide actionable error messages to users
- Never expose internal details to users

### Logging Setup

```python
def _setup_logging(self) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, self.config.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Add file handler for production:
            # logging.FileHandler("app.log")
        ]
    )
    return logging.getLogger("amplifier_app")
```

**Logging levels**:
- `DEBUG`: Detailed diagnostic information
- `INFO`: General application flow
- `WARNING`: Unexpected but recoverable events
- `ERROR`: Errors that need attention

### Lifecycle Management

```python
async def __aenter__(self):
    """Context manager entry"""
    await self.initialize()
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    """Context manager exit - always cleanup"""
    await self.shutdown()
```

**Using as context manager**:
```python
async with AmplifierApp(config) as app:
    response = await app.execute("prompt")
# Cleanup happens automatically
```

This ensures resources are **always cleaned up**, even on errors.

### CLI Interface Patterns

**Interactive Mode**:
```python
async def run_interactive_cli(app: AmplifierApp):
    while True:
        prompt = input("\n💬 You: ")
        if prompt.lower() in ("quit", "exit", "q"):
            break
        try:
            response = await app.execute(prompt)
            print(f"\n🤔 Agent: {response}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            # Session is still active, can continue
```

**Single Prompt Mode**:
```python
async def run_single_prompt(app: AmplifierApp, prompt: str):
    response = await app.execute(prompt)
    print(f"\nResponse:\n{response}")
```

## Real-World Use Cases

This pattern is ideal for:

- **Internal Developer Tools**: Code review assistants, refactoring tools
- **Data Analysis Tools**: Query and analyze datasets
- **Automation Scripts**: Workflow automation with AI
- **Command-Line Utilities**: Any CLI tool needing AI capabilities

## Expected Output

```
🚀 Amplifier CLI Application Example
============================================================
✓ Configuration loaded
  Provider: anthropic-sonnet.yaml
  Log level: INFO

2025-12-16 05:20:00 [INFO] amplifier_app: Initializing...
2025-12-16 05:20:01 [INFO] amplifier_app: ✓ Application initialized successfully

============================================================
🤖 Amplifier CLI App - Interactive Mode
============================================================
Type your prompts, or 'quit' to exit.

💬 You: What is 2 + 2?

🤔 Agent: 2 + 2 equals 4.

💬 You: quit

👋 Goodbye!
```

## Why This Pattern

**Advantages**:

1. **Reusable** - Same class works for interactive, batch, or API modes
2. **Testable** - Mock the session for testing
3. **Configurable** - Environment-based configuration
4. **Observable** - Structured logging throughout
5. **Robust** - Proper error handling and cleanup

## Key Patterns Demonstrated

### Pattern 1: Encapsulation

```python
# ❌ Inline everything
foundation = await load_bundle(...)
provider = await load_bundle(...)
# ... 50 lines of setup

# ✅ Encapsulate in a class
app = AmplifierApp(config)
await app.initialize()
```

### Pattern 2: Configuration Separation

```python
# ❌ Hardcoded values
api_key = "sk-..."

# ✅ Environment-based config
config = AppConfig.from_env()
config.validate()
```

### Pattern 3: Context Managers

```python
# ❌ Manual cleanup
app = AmplifierApp(config)
try:
    await app.initialize()
    result = await app.execute(prompt)
finally:
    await app.shutdown()

# ✅ Automatic cleanup
async with AmplifierApp(config) as app:
    result = await app.execute(prompt)
```

## Related Concepts

- **[Getting Started](../getting_started.md)** - Basic bundle workflow
- **[Config Library](/libraries/config.md)** - Configuration management
- **[Session API](/api/core/session.md)** - Session lifecycle
- **[Application Developer Guide](/developer_guides/applications/)** - More patterns

## Next Steps

- **[Multi-Agent System Example](multi_agent_system.md)** - Complex agent workflows
- **[Application Guide](/developer_guides/applications/)** - Production application patterns
- **[CLI Case Study](/developer_guides/applications/cli_case_study.md)** - Real-world CLI architecture
