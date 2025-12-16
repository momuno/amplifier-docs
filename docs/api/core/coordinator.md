# Coordinator API

The Coordinator API centers around the `ModuleCoordinator` class, which serves as the central coordination and infrastructure context for all modules in an Amplifier session. The coordinator provides essential services including module mounting and management, inter-module communication through capabilities and contribution channels, hook result processing, and access to session infrastructure like configuration and module loading.

The `ModuleCoordinator` acts as the bridge between the kernel and modules, offering a standardized interface for modules to interact with the session context and each other. It maintains mount points for different module types (orchestrators, providers, tools, context managers), manages the hook registry, and provides mechanisms for modules to register capabilities and contribute to shared channels.

Key capabilities include:

- **Module Management**: Mount, unmount, and retrieve modules at designated mount points
- **Infrastructure Access**: Provide session ID, configuration, and module loader references
- **Inter-Module Communication**: Capability registry and contribution channels for loose coupling
- **Hook Processing**: Route hook results to appropriate subsystems (approval, display, context injection)
- **Resource Management**: Cleanup registration and session lifecycle management
- **Budget Enforcement**: Token and size limits for context injections based on session policy

The coordinator embodies the kernel's "minimal context plumbing" philosophy by providing only the essential identifiers and state necessary to make module boundaries work effectively.

## ModuleCoordinator

The `ModuleCoordinator` class is the central coordination hub that provides infrastructure context and services to all modules within an Amplifier session. It acts as the kernel's primary interface for module management, inter-module communication, and session-level operations.

**Source**: [`amplifier_core/coordinator.py`](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/coordinator.py)

The coordinator is initialized with a parent `AmplifierSession` and optional approval and display systems:

```python
coordinator = ModuleCoordinator(
    session=session,
    approval_system=approval_system,  # Optional
    display_system=display_system     # Optional
)
```

**Core Responsibilities:**

| Area | Description |
|------|-------------|
| **Module Management** | Mount/unmount modules at designated mount points (orchestrator, providers, tools, context, hooks) |
| **Infrastructure Access** | Provide session ID, parent ID, configuration, and module loader references |
| **Inter-Module Communication** | Capability registry for loose coupling and contribution channels for aggregation |
| **Hook Processing** | Route hook results to approval systems, display systems, and context managers |
| **Resource Management** | Cleanup registration, budget enforcement, and session lifecycle management |

**Mount Points:**

The coordinator maintains several mount points for different module types:

- `orchestrator` - Single orchestration module
- `providers` - Multiple provider modules by name  
- `tools` - Multiple tool modules by name
- `context` - Single context manager
- `hooks` - Built-in hook registry
- `module-source-resolver` - Optional custom source resolver

**Budget Enforcement:**

The coordinator enforces configurable limits on context injections:

- **Injection Budget**: Token limit per turn (configurable via session config)
- **Size Limit**: Byte limit per individual injection
- **Default Policy**: Unlimited (kernel provides mechanism, not policy)

The coordinator embodies the kernel's "minimal context plumbing" philosophy by providing only essential identifiers and state necessary for effective module boundaries while maintaining clean separation between kernel mechanisms and application-layer policies.

### Properties

The `ModuleCoordinator` exposes several properties that provide access to session infrastructure, configuration, and policy settings. These properties enable modules to access essential context information and enforce resource limits based on session configuration.

**Available Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `session` | `AmplifierSession` | Parent session reference for spawning child sessions |
| `session_id` | `str` | Current session ID for persistence and correlation |
| `parent_id` | `str \| None` | Parent session ID for lineage tracking in child sessions |
| `config` | `dict` | Session configuration including mount plan and module settings |
| `loader` | `ModuleLoader` | Module loader for dynamic module loading |
| `injection_budget_per_turn` | `int \| None` | Token budget per turn from session config (None = unlimited) |
| `injection_size_limit` | `int \| None` | Byte limit per context injection (None = unlimited) |

**Usage Examples:**

```python
# Access session infrastructure
session_id = coordinator.session_id
parent_session = coordinator.session

# Get configuration for module setup
config = coordinator.config
provider_config = config.get('providers', {}).get('openai', {})

# Check resource limits before injection
budget = coordinator.injection_budget_per_turn
size_limit = coordinator.injection_size_limit

if size_limit and len(content) > size_limit:
    raise ValueError(f"Content exceeds {size_limit} bytes")

# Load modules dynamically
loader = coordinator.loader
module_mount = await loader.load('tool-filesystem', {})
```

**Policy Configuration:**

Resource limits are configured in the session config under the `session` key:

```python
config = {
    "session": {
        "injection_budget_per_turn": 1000,  # Token limit per turn
        "injection_size_limit": 50000       # Byte limit per injection
    }
}
```

The coordinator follows the kernel's philosophy of providing mechanism without policy - limits default to `None` (unlimited) and are only enforced when explicitly configured.

### Methods

The `ModuleCoordinator` provides a comprehensive set of methods for managing modules, facilitating inter-module communication, and processing hook results. These methods enable dynamic module lifecycle management, capability registration for loose coupling, and resource cleanup during session termination.

**Available Methods:**

| Category | Methods | Purpose |
|----------|---------|---------|
| **Module Management** | `mount`, `unmount`, `get` | Mount/unmount modules at designated mount points |
| **Resource Management** | `register_cleanup`, `cleanup`, `reset_turn` | Handle cleanup functions and session lifecycle |
| **Inter-Module Communication** | `register_capability`, `get_capability` | Enable capability-based module interaction |
| **Contribution System** | `register_contributor`, `collect_contributions` | Aggregate contributions from multiple modules |
| **Hook Processing** | `process_hook_result` | Route hook results to appropriate subsystems |

**Common Usage Patterns:**

```python
# Module lifecycle management
await coordinator.mount('providers', openai_provider, 'openai')
provider = coordinator.get('providers', 'openai')
await coordinator.unmount('providers', 'openai')

# Inter-module communication
coordinator.register_capability('agents.list', list_agents_func)
list_func = coordinator.get_capability('agents.list')

# Contribution aggregation
coordinator.register_contributor('observability.events', 'tool-task', 
                                lambda: ['task:spawned', 'task:completed'])
events = await coordinator.collect_contributions('observability.events')

# Hook result processing
processed_result = await coordinator.process_hook_result(
    result, event='before_call', hook_name='security_check'
)
```

The methods follow the kernel's philosophy of providing mechanism without policy - they offer flexible infrastructure that applications can configure according to their specific needs.

#### mount

Mounts a module at a specified mount point within the coordinator's module registry. This method handles both single-module mount points (like orchestrator, context) and multi-module mount points (like providers, tools) with automatic name resolution and validation.

**Method Signature:**
```python
async def mount(self, mount_point: str, module: Any, name: str | None = None) -> None
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mount_point` | `str` | Yes | Target mount point ('orchestrator', 'providers', 'tools', 'context', 'module-source-resolver') |
| `module` | `Any` | Yes | Module instance to mount |
| `name` | `str \| None` | Conditional | Required for multi-module mount points; optional for single-module mount points |

**Return Value:** `None`

**Execution Behavior:**

The method validates the mount point and applies different mounting logic based on the mount point type:

- **Single-module mount points** (`orchestrator`, `context`, `module-source-resolver`): Replaces any existing module with a warning if one exists
- **Multi-module mount points** (`providers`, `tools`, `agents`): Requires a name parameter or attempts to extract the name from the module's `name` attribute
- **Hooks mount point**: Raises an error directing users to register hooks directly with the HookRegistry

**Usage Example:**
```python
# Mount single modules
await coordinator.mount('orchestrator', orchestrator_instance)
await coordinator.mount('context', context_manager)

# Mount named modules (explicit name)
await coordinator.mount('providers', openai_provider, 'openai')
await coordinator.mount('tools', filesystem_tool, 'filesystem')

# Mount with auto-detected name (module.name attribute)
class MyTool:
    name = "custom-tool"
    
my_tool = MyTool()
await coordinator.mount('tools', my_tool)  # Uses "custom-tool" as name
```

The method logs successful mounts with the module class name and mount location for debugging and audit purposes. Invalid mount points or missing names for multi-module mount points raise `ValueError` exceptions.

#### unmount

Removes a module from a specified mount point within the coordinator's module registry. This method handles both single-module mount points that are set to `None` and multi-module mount points where specific named modules are deleted from the registry.

**Method Signature:**
```python
async def unmount(self, mount_point: str, name: str | None = None) -> None
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mount_point` | `str` | Yes | Target mount point to unmount from |
| `name` | `str \| None` | Conditional | Required for multi-module mount points; not used for single-module mount points |

**Return Value:** `None`

**Execution Behavior:**

The method validates the mount point and applies different unmounting logic based on the mount point type:

- **Single-module mount points** (`orchestrator`, `context`, `module-source-resolver`): Sets the mount point to `None`, effectively clearing it
- **Multi-module mount points** (`providers`, `tools`, `agents`): Requires a name parameter and removes only the specified named module from the registry
- **Invalid mount points**: Raises `ValueError` for unrecognized mount point names

**Usage Example:**
```python
# Unmount single modules
await coordinator.unmount('orchestrator')
await coordinator.unmount('context')

# Unmount specific named modules
await coordinator.unmount('providers', 'openai')
await coordinator.unmount('tools', 'filesystem')

# Error cases
await coordinator.unmount('providers')  # ValueError: Name required
await coordinator.unmount('invalid')    # ValueError: Unknown mount point
```

The method logs successful unmounts with the mount point and name (if applicable) for debugging and audit purposes. Missing names for multi-module mount points or attempts to unmount non-existent modules raise `ValueError` exceptions.

#### get

Retrieves a mounted module or collection of modules from a specified mount point within the coordinator's module registry. This method provides unified access to both single-module mount points and multi-module collections with flexible return behavior.

**Method Signature:**
```python
def get(self, mount_point: str, name: str | None = None) -> Any
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mount_point` | `str` | Yes | Mount point to retrieve from ('orchestrator', 'providers', 'tools', 'context', 'hooks', 'module-source-resolver') |
| `name` | `str \| None` | Optional | Specific module name for multi-module mount points; ignored for single-module mount points |

**Return Value:** `Any` - Returns the mounted module, dictionary of modules, or `None` if not found

**Execution Behavior:**

The method validates the mount point and returns different data types based on the mount point type and name parameter:

- **Single-module mount points** (`orchestrator`, `context`, `hooks`, `module-source-resolver`): Returns the mounted module directly, ignoring the name parameter
- **Multi-module mount points** (`providers`, `tools`, `agents`): 
  - With `name`: Returns the specific named module or `None` if not found
  - Without `name`: Returns the entire dictionary of all mounted modules at that mount point
- **Invalid mount points**: Raises `ValueError` for unrecognized mount point names

**Usage Example:**
```python
# Get single modules
orchestrator = coordinator.get('orchestrator')
context_mgr = coordinator.get('context')
hook_registry = coordinator.get('hooks')

# Get specific named modules
openai_provider = coordinator.get('providers', 'openai')
fs_tool = coordinator.get('tools', 'filesystem')

# Get all modules at a mount point
all_providers = coordinator.get('providers')  # Returns: {'openai': provider, 'anthropic': provider}
all_tools = coordinator.get('tools')          # Returns: {'filesystem': tool, 'web': tool}

# Handle missing modules
missing = coordinator.get('providers', 'nonexistent')  # Returns: None
```

The method provides immediate access to mounted modules without logging, making it suitable for frequent access patterns during module execution and inter-module communication.

#### register_cleanup

Registers a cleanup function to be executed during coordinator shutdown. Cleanup functions are stored in a list and executed in LIFO (Last In, First Out) order during the cleanup process, ensuring proper teardown sequence for dependent resources.

**Method Signature:**
```python
def register_cleanup(self, cleanup_fn) -> None
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cleanup_fn` | `Callable` | Yes | Function to execute during cleanup; can be sync, async, or return a coroutine |

**Return Value:** `None`

**Execution Behavior:**

The method appends the cleanup function to an internal list without validation or immediate execution. During coordinator shutdown, registered cleanup functions are executed in reverse order (LIFO) with comprehensive error handling:

- **Async functions**: Awaited directly using `await cleanup_fn()`
- **Sync functions**: Called normally, with coroutine results awaited if returned
- **Error handling**: Individual cleanup failures are logged but don't prevent other cleanups from executing
- **Execution order**: Most recently registered functions execute first, allowing dependent resources to clean up before their dependencies

**Usage Example:**
```python
# Register various cleanup types
coordinator.register_cleanup(lambda: print("Simple cleanup"))
coordinator.register_cleanup(async_database_close)
coordinator.register_cleanup(file_handle.close)

# Cleanup with resource dependencies
coordinator.register_cleanup(connection_pool.close)  # Registered first
coordinator.register_cleanup(database.disconnect)    # Executes first (LIFO)

# During coordinator.cleanup(), database disconnects before pool closes
```

This method is essential for proper resource management, ensuring that modules can register teardown logic that executes reliably during session cleanup, even if individual cleanup functions encounter errors.

#### register_capability

Registers a capability that other modules can access for inter-module communication. Capabilities provide a decoupled mechanism for modules to expose functionality without creating direct dependencies between modules.

**Method Signature:**
```python
def register_capability(self, name: str, value: Any) -> None
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | Yes | Capability name using dot notation (e.g., 'agents.list', 'agents.get') |
| `value` | `Any` | Yes | The capability value, typically a callable function or method |

**Return Value:** `None`

**Execution Behavior:**

The method stores the capability in an internal registry dictionary and logs the registration at debug level. Capabilities are immediately available to other modules via `get_capability()`. The naming convention uses dot notation to create logical namespaces, preventing conflicts between modules providing similar functionality.

**Usage Example:**
```python
# Register agent management capabilities
coordinator.register_capability('agents.list', lambda: list(agent_registry.keys()))
coordinator.register_capability('agents.get', agent_registry.get)
coordinator.register_capability('agents.spawn', spawn_child_agent)

# Register tool capabilities
coordinator.register_capability('tools.filesystem.read', read_file_function)
coordinator.register_capability('tools.web.fetch', fetch_url_function)

# Other modules can access these capabilities
list_agents = coordinator.get_capability('agents.list')
available_agents = list_agents() if list_agents else []
```

This capability registry enables loose coupling between modules, allowing them to discover and use each other's functionality without requiring direct imports or references. The dot notation naming convention helps organize capabilities by module and function type.

#### get_capability

Retrieves a registered capability by name, returning the capability value if found or `None` if not registered. This method provides the lookup mechanism for the inter-module capability system, allowing modules to discover and access functionality exposed by other modules.

**Method Signature:**
```python
def get_capability(self, name: str) -> Any | None
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | Yes | Capability name to retrieve (e.g., 'agents.list', 'tools.filesystem.read') |

**Return Value:** `Any | None` - The registered capability value if found, `None` if the capability name is not registered

**Execution Behavior:**

The method performs a simple dictionary lookup in the internal capability registry without logging or side effects. It returns `None` for unregistered capability names rather than raising exceptions, allowing modules to gracefully handle missing capabilities and implement fallback behavior.

**Usage Example:**
```python
# Check for and use agent management capabilities
list_agents_fn = coordinator.get_capability('agents.list')
if list_agents_fn:
    available_agents = list_agents_fn()
    print(f"Available agents: {available_agents}")
else:
    print("Agent listing not available")

# Safe capability access with fallback
spawn_agent = coordinator.get_capability('agents.spawn')
if spawn_agent:
    new_agent = spawn_agent('task-executor', config={'timeout': 300})
else:
    # Fallback to direct instantiation
    new_agent = TaskExecutor(timeout=300)

# Batch capability checking
required_caps = ['tools.filesystem.read', 'tools.web.fetch', 'agents.get']
missing_caps = [cap for cap in required_caps if coordinator.get_capability(cap) is None]
```

This method enables defensive programming patterns where modules can check for capability availability before attempting to use inter-module functionality, promoting robust operation even when optional modules are not loaded.

#### register_contributor

Registers a contributor to a named channel for pull-based aggregation. This method enables modules to participate in contribution channels where multiple modules can provide data that consumers collect on demand. The kernel coordinates registration and collection but does not interpret the payload format or content.

**Method Signature:**
```python
def register_contributor(
    self,
    channel: str,
    name: str,
    callback: Callable[[], Any] | Callable[[], Awaitable[Any]],
) -> None
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | `str` | Yes | Channel identifier using dot notation (e.g., 'observability.events', 'capabilities') |
| `name` | `str` | Yes | Module name for debugging and diagnostics |
| `callback` | `Callable[[], Any] \| Callable[[], Awaitable[Any]]` | Yes | Sync or async function returning contribution data, or `None` to skip |

**Return Value:** `None`

**Execution Behavior:**

The method creates the channel if it doesn't exist and appends the contributor to the channel's registration list. Contributors are stored with their name and callback for later collection. The callback can be synchronous or asynchronous - the collection mechanism handles both types automatically. Registration order is preserved, and the same name can be registered multiple times on the same channel.

**Usage Example:**
```python
# Register event declarations
coordinator.register_contributor(
    'observability.events',
    'tool-filesystem',
    lambda: ['filesystem:read', 'filesystem:write', 'filesystem:delete']
)

# Register async capability provider
async def get_agent_capabilities():
    return {'spawn': spawn_agent, 'list': list_agents}

coordinator.register_contributor(
    'capabilities',
    'agent-manager',
    get_agent_capabilities
)

# Dynamic contribution based on runtime state
coordinator.register_contributor(
    'session.metadata',
    'context-manager',
    lambda: {'message_count': len(messages)} if messages else None
)
```

Contributors are collected later via `collect_contributions()` when consumers need the aggregated data. Failed callbacks are logged and skipped without affecting other contributors, ensuring non-interfering operation across modules.

#### collect_contributions

Collects contributions from all registered contributors on a specified channel. This method provides the pull-based aggregation mechanism for contribution channels, executing callbacks in registration order and returning their results. The kernel handles both synchronous and asynchronous callbacks automatically while providing non-interfering failure handling.

**Method Signature:**
```python
async def collect_contributions(self, channel: str) -> list[Any]
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | `str` | Yes | Channel name to collect from (e.g., 'observability.events', 'capabilities') |

**Return Value:** `list[Any]` - List of contributions with `None` values filtered out, empty list if no contributors registered

**Execution Behavior:**

The method iterates through contributors in registration order, executing each callback and collecting results. It automatically detects whether callbacks are synchronous functions, async functions, or functions that return coroutines, handling each appropriately. When a contributor callback raises an exception, the error is logged with the contributor name and channel, then collection continues with remaining contributors. Callbacks returning `None` are filtered from the final results, allowing contributors to conditionally skip contributions based on runtime state.

**Usage Example:**
```python
# Collect event declarations from all modules
events = await coordinator.collect_contributions('observability.events')
# Returns: [['filesystem:read', 'filesystem:write'], ['agent:spawn', 'agent:stop']]

# Flatten collected contributions
all_events = []
for contribution in events:
    if isinstance(contribution, list):
        all_events.extend(contribution)

# Collect capabilities with error handling
capabilities = await coordinator.collect_contributions('capabilities')
merged_caps = {}
for cap_dict in capabilities:
    if isinstance(cap_dict, dict):
        merged_caps.update(cap_dict)
```

The method preserves registration order and provides predictable aggregation behavior, making it suitable for scenarios where contribution sequence matters or where consumers need to process results from specific modules in a defined order.

#### process_hook_result

Processes HookResult objects and routes their actions to appropriate subsystems. This method serves as the central dispatcher for hook-generated actions, handling context injection, approval requests, user messages, and output control. It enforces policy constraints like injection budgets and size limits while providing comprehensive audit logging.

**Method Signature:**
```python
async def process_hook_result(self, result: HookResult, event: str, hook_name: str = "unknown") -> HookResult
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `result` | `HookResult` | Yes | Hook result containing action and associated data |
| `event` | `str` | Yes | Event name that triggered the hook (for audit logging) |
| `hook_name` | `str` | No | Hook identifier for logging and debugging (defaults to "unknown") |

**Return Value:** `HookResult` - The processed result, potentially modified by approval flow (e.g., converted to "deny" action if user rejects approval request)

**Execution Behavior:**

The method processes HookResult actions in sequence: context injection is validated against size limits and budget constraints before being routed to the context manager with provenance metadata; approval requests are delegated to the approval system with timeout handling and default fallback behavior; user messages are routed to the display system or logged if no display system is available; output suppression flags are logged for orchestrator consumption. Each action type is handled independently, allowing HookResults to combine multiple actions (e.g., inject context AND show user message). Failed operations log errors but don't prevent processing of other actions within the same result.

**Usage Example:**
```python
# Hook returns complex result with multiple actions
hook_result = HookResult(
    action="inject_context",
    context_injection="Linter found 3 issues in file.py",
    user_message="Code analysis complete",
    suppress_output=True
)

# Process and route to subsystems
processed = await coordinator.process_hook_result(
    result=hook_result,
    event="tool.filesystem.write",
    hook_name="code-quality-checker"
)

# Approval request example
approval_result = await coordinator.process_hook_result(
    HookResult(action="ask_user", approval_prompt="Delete production file?"),
    event="tool.filesystem.delete",
    hook_name="safety-guard"
)
# Returns: HookResult(action="deny") if user rejects
```

The method enforces session-configured policies for injection limits while maintaining audit trails for all hook actions, enabling both automated agent enhancement and human oversight of sensitive operations.

#### cleanup

Executes all registered cleanup functions in reverse order during coordinator shutdown. This method provides deterministic resource cleanup by calling functions in LIFO order (last registered, first executed), ensuring proper dependency teardown. The coordinator handles both synchronous and asynchronous cleanup functions automatically while providing non-interfering error handling.

**Method Signature:**
```python
async def cleanup(self) -> None
```

**Parameters:** None

**Return Value:** `None`

**Execution Behavior:**

The method iterates through cleanup functions in reverse registration order, executing each function and handling both sync/async variants automatically. When a cleanup function is callable, the method detects whether it's an async function, sync function, or sync function returning a coroutine, then executes it appropriately. If any cleanup function raises an exception, the error is logged and execution continues with remaining functions, ensuring partial failures don't prevent other resources from being cleaned up properly.

**Usage Example:**
```python
# Register cleanup functions during module initialization
coordinator.register_cleanup(lambda: print("Cleanup step 1"))
coordinator.register_cleanup(async_database_close)
coordinator.register_cleanup(file_handle.close)

# Execute all cleanup functions (typically called by session)
await coordinator.cleanup()
# Output: Functions execute in reverse order with error isolation
```

The method ensures reliable resource cleanup even when individual cleanup operations fail, making it suitable for session teardown and graceful shutdown scenarios where multiple modules need to release resources in dependency order.

#### reset_turn

Resets per-turn tracking counters used in injection budget enforcement. This method should be called at turn boundaries to reset token consumption tracking, allowing fresh budget allocation for the next conversational turn. The coordinator maintains internal counters for injection budget enforcement that accumulate throughout a turn and need periodic reset.

**Method Signature:**
```python
def reset_turn(self) -> None
```

**Parameters:** None

**Return Value:** `None`

**Execution Behavior:**

The method resets the internal `_current_turn_injections` counter to zero, clearing accumulated token usage from context injections performed during the current turn. This counter tracks approximate token consumption from hook-generated context injections and is used to enforce the `injection_budget_per_turn` policy limit configured in session settings. The reset operation is immediate and does not affect other coordinator state or mounted modules.

**Usage Example:**
```python
# During turn processing, hooks inject context
await coordinator.process_hook_result(
    HookResult(action="inject_context", context_injection="Analysis complete"),
    event="tool.complete"
)
# coordinator._current_turn_injections now > 0

# At turn boundary, reset tracking
coordinator.reset_turn()
# coordinator._current_turn_injections now == 0

# Next turn starts with fresh budget
```

This method is typically called by the orchestrator or session manager at natural turn boundaries (e.g., after processing user input and generating response) to ensure injection budgets apply per conversational turn rather than accumulating across the entire session.

### Hook Result Processing

The coordinator provides specialized processing for HookResult actions through the `process_hook_result` method, which routes different action types to appropriate subsystems. This processing pipeline enables hooks to inject context, request approvals, display messages, and control output visibility through a unified interface.

**Processing Pipeline Example:**

```python
# Hook returns multi-action result
hook_result = HookResult(
    action="inject_context",
    context_injection="Security scan found 2 vulnerabilities in dependencies",
    context_injection_role="system",
    user_message="Security analysis complete - issues found",
    user_message_level="warning",
    suppress_output=True,
    ephemeral=False
)

# Coordinator processes all actions in sequence
processed_result = await coordinator.process_hook_result(
    result=hook_result,
    event="tool.package.install", 
    hook_name="security-scanner"
)

# Pipeline execution:
# 1. Context injection → routed to context manager with metadata
# 2. User message → routed to display system  
# 3. Output suppression → logged for orchestrator consumption
# 4. Returns original result (unless modified by approval flow)
```

**Subsystem Routing Table:**

| Action Type | Routing Destination | Processing Behavior | Failure Handling |
|-------------|-------------------|-------------------|------------------|
| `inject_context` | Context manager via `add_message()` | Validates size/budget limits, adds provenance metadata, tracks token usage | Raises ValueError on limit exceeded |
| `ask_user` | Approval system via `request_approval()` | Delegates to approval UI, handles timeout/default, returns modified result | Returns deny result if no approval system |
| `user_message` | Display system via `show_message()` | Routes to UI with severity level and source attribution | Falls back to logging if no display system |
| `suppress_output` | Orchestrator (via result flag) | Logs suppression request, sets flag for orchestrator filtering | No failure case - flag always set |
| `continue`/`deny`/`modify` | No routing | Passes through unchanged for orchestrator handling | No failure case - direct passthrough |

**Approval Flow Processing:**

```python
# Approval request with timeout handling
approval_result = HookResult(
    action="ask_user",
    approval_prompt="Allow network access to external API?",
    approval_options=["Allow once", "Allow always", "Deny"],
    approval_timeout=60.0,
    approval_default="deny"
)

processed = await coordinator.process_hook_result(
    approval_result, "tool.http.request", "network-policy"
)

# Possible return values:
# HookResult(action="continue") - user approved
# HookResult(action="deny", reason="User denied: Allow network access...") - user denied
# HookResult(action="deny", reason="Approval timeout - denied by default...") - timeout
```

**Context Injection with Budget Enforcement:**

```python
# Budget tracking across multiple injections in same turn
coordinator.reset_turn()  # Start fresh turn

# First injection
await coordinator.process_hook_result(
    HookResult(action="inject_context", context_injection="Step 1 complete"),
    "tool.step1", "progress-tracker"
)
# coordinator._current_turn_injections = ~3 tokens

# Second injection - budget check performed
await coordinator.process_hook_result(
    HookResult(action="inject_context", context_injection="Step 2 failed with error X"),
    "tool.step2", "error-reporter"  
)
# coordinator._current_turn_injections = ~9 tokens

# If session config has injection_budget_per_turn=10, next injection warns but proceeds
# If injection_size_limit=50 bytes, oversized injections raise ValueError
```

The processing pipeline handles each action type independently, allowing HookResults to combine multiple actions safely. Failed subsystem operations (like missing approval system) are logged and handled gracefully without preventing other actions from processing, ensuring robust hook execution even in partially configured environments.

### Capability System

The coordinator provides a capability registry system that enables inter-module communication without direct dependencies. Modules can register capabilities (typically functions or data) that other modules can discover and use, creating a loosely-coupled plugin architecture.

**Core Registry Methods:**

| Method | Purpose | Parameters | Returns |
|--------|---------|------------|---------|
| `register_capability(name, value)` | Register a capability for other modules to access | `name`: string identifier, `value`: any object (typically callable) | None |
| `get_capability(name)` | Retrieve a registered capability | `name`: string identifier | The capability object or None if not found |

**Capability Pattern - Provider and Consumer:**

```python
# Provider module registers capabilities during initialization
class AgentManager:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.agents = {}
        
        # Register capabilities for other modules to use
        coordinator.register_capability('agents.list', self.list_agents)
        coordinator.register_capability('agents.get', self.get_agent)
        coordinator.register_capability('agents.spawn', self.spawn_agent)
    
    def list_agents(self):
        return list(self.agents.keys())
    
    def get_agent(self, agent_id):
        return self.agents.get(agent_id)
    
    async def spawn_agent(self, config):
        # Implementation details...
        return agent_instance

# Consumer module uses capabilities without direct imports
class TaskTool:
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    async def execute_with_agent(self, task_config):
        # Discover and use agent capabilities
        spawn_agent = self.coordinator.get_capability('agents.spawn')
        if spawn_agent is None:
            raise RuntimeError("Agent spawning not available")
        
        agent = await spawn_agent(task_config['agent_config'])
        return await agent.execute(task_config['task'])
    
    def get_available_agents(self):
        list_agents = self.coordinator.get_capability('agents.list')
        return list_agents() if list_agents else []
```

**Dynamic Capability Discovery:**

```python
# Check capability availability before use
class FlexibleOrchestrator:
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    async def process_request(self, request):
        # Adapt behavior based on available capabilities
        capabilities = []
        
        # Check for optional capabilities
        if self.coordinator.get_capability('memory.search'):
            capabilities.append('semantic_search')
        
        if self.coordinator.get_capability('agents.spawn'):
            capabilities.append('agent_delegation')
        
        if self.coordinator.get_capability('tools.web.browse'):
            capabilities.append('web_research')
        
        # Route request based on available capabilities
        return await self._route_request(request, capabilities)
```

**Common Capability Patterns:**

| Pattern | Naming Convention | Example Capabilities | Use Case |
|---------|------------------|---------------------|----------|
| **Service Interface** | `service.action` | `agents.spawn`, `memory.store`, `tools.execute` | Core module functionality |
| **Data Access** | `data.operation` | `context.get_messages`, `session.get_config` | Read-only data access |
| **Event Handlers** | `events.event_name` | `events.tool_complete`, `events.agent_spawned` | Decoupled event processing |
| **Validation** | `validate.type` | `validate.tool_call`, `validate.agent_config` | Input validation services |
| **Transformation** | `transform.format` | `transform.markdown`, `transform.json_schema` | Data format conversion |
| **Query Interface** | `query.scope` | `query.available_tools`, `query.active_agents` | Discovery and introspection |

**Capability Lifecycle Management:**

```python
# Capabilities can be updated or removed during runtime
class DynamicProvider:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.active_services = {}
    
    def enable_service(self, service_name, implementation):
        self.active_services[service_name] = implementation
        self.coordinator.register_capability(
            f'services.{service_name}', 
            implementation
        )
    
    def disable_service(self, service_name):
        if service_name in self.active_services:
            del self.active_services[service_name]
            # Overwrite with None to indicate unavailability
            self.coordinator.register_capability(
                f'services.{service_name}', 
                None
            )
```

**Error Handling Best Practices:**

```python
# Robust capability consumption with fallbacks
class ResilientConsumer:
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    async def process_with_fallback(self, data):
        # Try preferred capability first
        advanced_processor = self.coordinator.get_capability('process.advanced')
        if advanced_processor:
            try:
                return await advanced_processor(data)
            except Exception as e:
                logger.warning(f"Advanced processing failed: {e}")
        
        # Fall back to basic capability
        basic_processor = self.coordinator.get_capability('process.basic')
        if basic_processor:
            return await basic_processor(data)
        
        # Final fallback to built-in processing
        return self._builtin_process(data)
```

The capability system enables flexible module composition where functionality can be discovered at runtime, modules can gracefully degrade when optional capabilities are unavailable, and new capabilities can be added without modifying existing consumer code. This pattern is particularly useful for plugin architectures and optional feature integration.

### Examples

The following examples demonstrate common patterns for working with the ModuleCoordinator in real-world scenarios. These examples show how to mount modules, register capabilities, process hook results, and leverage the coordinator's infrastructure features for building robust amplifier-core applications.

Each example focuses on practical implementation patterns you'll encounter when developing modules or integrating the coordinator into your application architecture. The examples progress from basic mounting operations to more advanced features like contribution channels and child session management.

**Key Example Categories:**

| Category | Focus | Common Use Cases |
|----------|-------|------------------|
| **Module Mounting** | Attaching modules to mount points | Setting up orchestrators, providers, tools |
| **Multi-Module Access** | Working with collections of modules | Managing multiple providers or tools |
| **Capability Registration** | Inter-module communication | Service discovery, loose coupling |
| **Hook Processing** | Handling hook results and actions | Context injection, approval flows |
| **Contribution Channels** | Aggregating module contributions | Event collection, capability discovery |
| **Session Management** | Spawning and managing child sessions | Agent delegation, sub-task processing |

These examples assume you have a configured ModuleCoordinator instance and focus on the interaction patterns rather than initial setup. Error handling and logging are included where relevant to demonstrate production-ready code patterns.

#### Basic Module Mounting

The basic module mounting pattern follows a standard lifecycle: create the module instance, access infrastructure context from the coordinator, mount the module at the appropriate mount point, and register any necessary cleanup functions.

```python
# Basic mounting pattern for a single-instance module
class CustomOrchestrator:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.active_tasks = []
    
    async def cleanup(self):
        # Clean up any resources
        self.active_tasks.clear()

# Mount the module
orchestrator = CustomOrchestrator(coordinator)
await coordinator.mount('orchestrator', orchestrator)

# Register cleanup for proper shutdown
coordinator.register_cleanup(orchestrator.cleanup)

# Access infrastructure context within the module
session_id = coordinator.session_id
config = coordinator.config.get('orchestrator', {})
```

This pattern demonstrates the core mounting workflow where modules receive the coordinator instance for infrastructure access, get mounted at their designated mount point, and register cleanup functions for resource management. The coordinator provides session identity, configuration access, and cleanup coordination without modules needing direct session references.

For multi-module mount points like providers and tools, the pattern includes a name parameter:

```python
# Multi-module mounting with explicit naming
file_tool = FileSystemTool(coordinator)
await coordinator.mount('tools', file_tool, name='filesystem')

web_tool = WebBrowserTool(coordinator) 
await coordinator.mount('tools', web_tool, name='browser')

# Access mounted tools
all_tools = coordinator.get('tools')  # Returns dict of all tools
file_tool = coordinator.get('tools', 'filesystem')  # Returns specific tool
```

The mounting system automatically handles module replacement warnings and maintains the mount point registry for later access and cleanup operations.

#### Multi-Module Access

When modules need to interact with other mounted modules, they use the coordinator's `get()` method to access mount points safely. This pattern enables loose coupling between modules while providing runtime integration capabilities.

```python
class SmartOrchestrator:
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    async def process_request(self, user_input):
        # Access other mounted modules safely
        context = self.coordinator.get('context')
        tools = self.coordinator.get('tools')  # Returns dict of all tools
        file_tool = self.coordinator.get('tools', 'filesystem')  # Specific tool
        
        # Always check for None - modules may not be mounted
        if context is None:
            return "No context manager available"
        
        if file_tool is None:
            return "Filesystem tool not available"
        
        # Use other modules in processing
        current_context = await context.get_messages()
        file_result = await file_tool.list_files("/workspace")
        
        return f"Found {len(file_result)} files in context of {len(current_context)} messages"

# Hook handlers commonly access other modules
async def integration_hook(event_data, coordinator):
    providers = coordinator.get('providers')
    
    # Check if specific provider is available
    if 'openai' in providers:
        result = await providers['openai'].generate("Analyze this event")
        return HookResult(context_injection=result)
    
    return HookResult(action="continue")
```

The key pattern is defensive programming: always check for `None` since modules may not be mounted, use the two-parameter form of `get()` for named modules in collections, and access the coordinator reference that modules store during initialization. This enables modules to discover and integrate with other system components at runtime without hard dependencies.

#### Capability Registration

The capability registration system enables modules to expose services that other modules can discover and use without direct dependencies. This is particularly useful for agent management where multiple modules need to coordinate child session spawning.

```python
class AgentManager:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.agent_configs = {}
    
    async def mount(self):
        # Register capabilities for other modules to use
        self.coordinator.register_capability('agents.list', self.list_agents)
        self.coordinator.register_capability('agents.get', self.get_agent_config)
        self.coordinator.register_capability('agents.spawn', self.spawn_agent)
    
    def list_agents(self):
        """Return available agent types."""
        return list(self.agent_configs.keys())
    
    def get_agent_config(self, agent_type):
        """Get configuration for specific agent type."""
        return self.agent_configs.get(agent_type)
    
    async def spawn_agent(self, agent_type, task_prompt):
        """Spawn child session with agent configuration."""
        base_config = self.coordinator.config
        agent_overlay = self.agent_configs.get(agent_type, {})
        
        # Merge base config with agent-specific overlay
        child_config = self._merge_configs(base_config, agent_overlay)
        
        # Create child session with parent lineage
        from amplifier_core import AmplifierSession
        child_session = AmplifierSession(
            config=child_config,
            parent_id=self.coordinator.session_id,  # Track parent
            approval_system=self.coordinator.approval_system,
            display_system=self.coordinator.display_system
        )
        
        # Execute task in child session
        async with child_session:
            result = await child_session.execute(task_prompt)
            return result

# Other modules can discover and use these capabilities
async def task_hook(event_data, coordinator):
    # Discover available agents
    list_agents = coordinator.get_capability('agents.list')
    spawn_agent = coordinator.get_capability('agents.spawn')
    
    if list_agents and spawn_agent and 'research' in list_agents():
        result = await spawn_agent('research', "Analyze this topic")
        return HookResult(context_injection=f"Research result: {result}")
    
    return HookResult(action="continue")
```

The pattern follows three steps: register capabilities during module mounting using descriptive dot-notation names, implement the capability functions with proper error handling and session management, and consume capabilities by checking for availability before use. Child sessions automatically inherit the parent's session ID for lineage tracking and emit `session:fork` events during initialization.

#### Hook Result Processing

The coordinator's `process_hook_result()` method handles the complete hook workflow, routing actions to appropriate subsystems and managing the orchestrator's response to hook decisions. Here's the typical orchestrator pattern:

```python
class SmartOrchestrator:
    async def execute(self, user_input):
        # 1. Emit pre-execution hooks
        pre_results = await self.coordinator.hooks.emit(
            'orchestrator:pre_execute', 
            {'input': user_input, 'context': await self._get_context()}
        )
        
        # 2. Process each hook result
        for result in pre_results:
            processed = await self.coordinator.process_hook_result(
                result, 'orchestrator:pre_execute', result.hook_name
            )
            
            # 3. Handle deny/modify actions
            if processed.action == 'deny':
                return f"Operation denied: {processed.reason}"
            elif processed.action == 'modify_input':
                user_input = processed.modified_input
        
        # 4. Execute main logic
        response = await self._generate_response(user_input)
        
        # 5. Emit post-execution hooks
        post_results = await self.coordinator.hooks.emit(
            'orchestrator:post_execute',
            {'input': user_input, 'response': response}
        )
        
        # 6. Process post-hooks (may suppress output)
        suppress_output = False
        for result in post_results:
            processed = await self.coordinator.process_hook_result(
                result, 'orchestrator:post_execute', result.hook_name
            )
            if processed.suppress_output:
                suppress_output = True
        
        return None if suppress_output else response
```

The `process_hook_result()` method automatically handles context injection (routing to the context manager), approval requests (delegating to the approval system), user messages (routing to the display system), and sets flags for output suppression. The orchestrator only needs to check the returned action and respond appropriately - the coordinator handles all the subsystem routing, budget validation, and audit logging internally.

#### Contribution Channel

The contribution channel system provides a generic aggregation mechanism where multiple modules can contribute data to named channels, and any module can collect all contributions from a channel. This enables loose coupling for features like capability discovery and event aggregation.

```python
# Module registration - each module contributes to channels
class FileSystemTool:
    async def mount(self, coordinator):
        # Register capabilities this tool provides
        coordinator.register_contributor(
            'capabilities', 
            'tool-filesystem',
            lambda: ['file:read', 'file:write', 'file:list']
        )
        
        # Register events this tool can emit
        coordinator.register_contributor(
            'observability.events',
            'tool-filesystem', 
            lambda: ['file:accessed', 'file:modified']
        )

class TaskTool:
    async def mount(self, coordinator):
        coordinator.register_contributor(
            'capabilities',
            'tool-task',
            lambda: ['task:create', 'task:status', 'task:complete']
        )

# Collection - any module can gather all contributions
class CapabilityManager:
    async def list_all_capabilities(self, coordinator):
        # Collect from all registered contributors
        capability_lists = await coordinator.collect_contributions('capabilities')
        # Returns: [['file:read', 'file:write', 'file:list'], ['task:create', 'task:status', 'task:complete']]
        
        # Flatten into single list
        all_capabilities = []
        for cap_list in capability_lists:
            all_capabilities.extend(cap_list)
        
        return all_capabilities
```

The pattern separates registration (modules declare what they contribute) from collection (modules gather contributions when needed). Contributors can return `None` to skip contributing, and failed contributors are logged but don't break collection. The coordinator handles both sync and async contributor callbacks automatically.

#### Child Session Spawning

Child sessions enable delegation to specialized agents or sub-workflows while maintaining lineage tracking. The parent session reference in the coordinator provides the infrastructure for spawning children with merged configurations:

```python
# In a tool or hook that needs to delegate work
async def delegate_to_research_agent(coordinator, query):
    # 1. Access parent session through coordinator
    parent_session = coordinator.session
    
    # 2. Get agent config overlay from mount plan
    agent_configs = coordinator.config.get('agents', {})
    research_config = agent_configs.get('research', {})
    
    # 3. Merge parent config with agent overlay
    child_config = parent_session._merge_configs(
        parent_session.config, 
        research_config
    )
    
    # 4. Create child session with parent_id for lineage
    child_session = AmplifierSession(
        config=child_config,
        parent_id=parent_session.session_id,  # Links to parent
        approval_system=coordinator.approval_system,
        display_system=coordinator.display_system
    )
    
    # 5. Execute delegation and cleanup
    async with child_session:
        result = await child_session.execute(query)
        return result
```

The pattern leverages the session's `_merge_configs()` method to overlay agent-specific configuration onto the parent's base configuration, ensuring the child inherits providers and tools while customizing orchestrator behavior or context settings. The `parent_id` parameter automatically enables lineage tracking - the child session will emit a `session:fork` event during initialization and include the parent ID in all subsequent events for audit trails and debugging.

## See Also

**Core API Documentation:**
- [Session API](session.py) - Main entry point for creating and managing Amplifier sessions
- [Hooks API](hooks.py) - Event system for lifecycle hooks with priority ordering and deterministic execution
- [Module Interfaces](interfaces.py) - Protocol definitions for Provider, Tool, Orchestrator, ContextManager, and HookHandler

**Configuration and Setup:**
- [Mount Plan Specification](docs/specs/MOUNT_PLAN_SPECIFICATION.md) - Complete schema for session configuration including module loading and agent overlays
- [Capability Registry](docs/CAPABILITY_REGISTRY.md) - Inversion of control pattern for module-to-app communication without direct dependencies
- [Contribution Channels](docs/specs/CONTRIBUTION_CHANNELS.md) - Pull-based aggregation mechanism for collecting data across multiple modules

**Advanced Features:**
- [Session Fork Specification](docs/SESSION_FORK_SPECIFICATION.md) - Child session creation with lineage tracking for delegation workflows
- [Module Source Protocol](docs/MODULE_SOURCE_PROTOCOL.md) - Custom module loading strategies and source resolution mechanisms
- [Event Taxonomy](events.py) - Canonical event names for hooks and observability including session, provider, tool, and context events

**Architecture and Philosophy:**
- [Design Philosophy](docs/DESIGN_PHILOSOPHY.md) - Core principles of mechanism vs policy, kernel boundaries, and the Linux kernel decision framework