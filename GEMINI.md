# GEMINI.md

This file provides guidance to the Gemini CLI when working with code in this repository.

## Common Commands
- **Build**: No build step defined.
- **Lint**: No linter configured.
- **Run Tests**: No test suite detected.

## High-Level Architecture
This repository is an experimental playground for CLI tools and does not contain traditional source code.
- **Project Layout**: The repository is organized into:
  - `workflows/` - n8n automation definitions
  - `visuals/` - Excalidraw diagrams and architecture visuals
  - `designs/` - Brand design documentation (DESIGN.md system)
  - `docs/` - Project documentation
  - `memories/` - Session knowledge base
  - `content/` - Content assets (carousels, templates)
  - `.claude/` - Claude Code knowledge base (memory, docs, rules)
- **Core Focus**: Experiments with Claude Code, Gemini CLI, n8n, and other CLI-based tools.

## Changelog
- **2026-04-21**: Initialized Claude Code configuration and command personas.
    - Updated `.claude/settings.json` with secure permissions.
    - Defined agent personas: Planner, Coder, Reviewer, Tester, Orchestrator.
    - Created context templates for tracking Plans, Changes, Reviews, and Test Results.
    - Synchronized master templates in `.claude/files/`.
- **2026-04-22**: Modified `linkedin-profile-optimizer` skill to use LinkedIn URL as primary input.
    - Updated `SKILL.md` to remove PDF/pasted text dependencies.
    - Refined input handling to prioritize browser-based profile extraction from URLs.

## Repository-Specific Rules
- Refer to the `README.md` for a detailed explanation of the project's purpose and structure.
- The `Changelog.md` file tracks significant setup and configuration changes.
- The `.claude/memory/` directory contains persistent context for Claude Code sessions.

## Memory System
- Claude Code maintains a persistent memory system in `.claude/memory/`:
  - **decision_log.md**: Key architectural decisions and rationale
  - **issues_tracker.md**: Bug tracking and technical debt
  - **progress.md**: Project milestones and goals
  - **session_context.md**: Context preserved across sessions

## How Gemini Should Use This File
- Scan this file on startup to understand the repository's unconventional structure and purpose.
- Use this context to inform your analysis of workflows, diagrams, and documentation.
