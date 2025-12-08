# Changelog

All notable changes to the Amplifier documentation will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- **Foundation Developer Guide** (`docs/developer_guides/foundation/`) - Comprehensive guide for working with amplifier-core and foundation libraries. Covers using the kernel programmatically, library integration, and contributing to the foundation.

- **Application Developer Guide** (`docs/developer_guides/applications/`) - Complete guide for building applications on amplifier-core. Includes step-by-step tutorial, best practices, and advanced topics.

- **CLI Application Case Study** (`docs/developer_guides/applications/cli_case_study.md`) - Real-world architectural walkthrough of how amplifier-app-cli is built. Shows production patterns for application development.

- **"For Different Audiences" section** in Architecture Overview - Clear navigation paths based on user intent (use, extend, build, contribute).

### Changed

- **User Guide** - Explicitly scoped to amplifier-app-cli with info box linking to other developer guides.

- **Developer Guide** - Renamed to "Module Developer Guide" and clarified scope as extending Amplifier with custom modules, not general development.

- **Navigation structure** - Reorganized "Developer Guide" into "Developer Guides" with three sections: Foundation, Applications, and Modules.

### Fixed

- Documentation gap between "using the CLI" and "extending with modules" - now covers foundation and application development.

- Confusion about whether "Developer Guide" applies to amplifier-app-cli - now clearly separated into Foundation (core/libraries), Applications (building apps), and Modules (extensions).

## Context

This release addresses feedback that documentation didn't distinguish between:
- Using amplifier-app-cli (an application)
- Building applications on amplifier-core (foundation usage)
- Extending with modules (module development)
- Contributing to the foundation (core/libraries)

Documentation now aligns with the actual architecture: Applications → Libraries → Kernel → Modules
