# Developer Guides

This directory contains documentation for different types of developers working with Amplifier.

## Structure

### Foundation (`foundation/`)
For developers working with **amplifier-core** and the foundation libraries:
- Using amplifier-core programmatically
- Integrating libraries (profiles, collections, config, module-resolution)
- Contributing to core/libraries
- Understanding kernel internals

**Audience:** Core contributors, application builders, advanced users

### Applications (`applications/`)
For developers building **applications on amplifier-core**:
- Building custom UIs (CLI, web, GUI, API)
- Session lifecycle management
- Mount plan creation
- Case study: How amplifier-app-cli works

**Audience:** Anyone building apps on the Amplifier foundation

### Modules (`../developer/`)
For developers **extending Amplifier with modules**:
- Creating providers, tools, hooks, orchestrators, contexts
- Module contracts and interfaces
- Publishing modules

**Audience:** Anyone adding new capabilities to Amplifier

## Quick Navigation

- **I want to use Amplifier CLI** → [User Guide](../user_guide/)
- **I want to build applications** → [Applications Guide](applications/)
- **I want to extend with modules** → [Modules Guide](../developer/)
- **I want to contribute to core** → [Foundation Guide](foundation/)

## Architecture Context

These guides assume you understand the [Architecture](../architecture/overview.md). If you're new, start there to understand:
- The Linux kernel analogy
- Kernel vs libraries vs applications vs modules
- Mechanism vs policy separation
