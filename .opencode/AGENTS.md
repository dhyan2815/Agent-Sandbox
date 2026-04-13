# AGENTS.md - Agentic Guidelines for General Project

This document provides essential context, standards, and commands for AI agents (like Claude Code, Gemini CLI, etc.) operating within this repository. It is designed to ensure consistency, safety, and efficiency when performing automated tasks.

## 0. Session Memory System (CRITICAL - READ FIRST)

### Auto-Fetch Protocol
At the start of **every session** (new or existing), the agent MUST:
1. Read `memories/SESSION_MEMORY.md` immediately after loading this file
2. Check the **Session Index** (Section 1) for the most recent session
3. Review any relevant context from **Section 4 (Historical Sessions)**
4. Check **Section 5 (Key Decisions & Outcomes)** for established patterns

### Memory Update Protocol
After each session concludes:
1. Append session record to Section 4 following the template
2. Update the Session Index table in Section 1
3. Update Section 5 with any new decisions made
4. Update Section 7 with any future intentions discussed

### File Locations
- **Session Memory**: `memories/SESSION_MEMORY.md` (versioned, NOT gitignored)
- **Career Info**: `memories/CAREER.md` (gitignored - contains sensitive job search data)
- **This File**: `.opencode/AGENTS.md`

### Why This Matters
The SESSION_MEMORY.md file is the primary second brain for this codebase. It stores:
- All conversation history and context
- Key decisions and outcomes
- User profile and preferences
- Project evolution over time

Reading this file first optimizes token usage by avoiding redundant context retrieval.

---

## 1. Project Overview & Mission
This repository is a central hub for **n8n automation workflows**, **MCP (Model Context Protocol) configurations**, and **system architecture documentation**. The primary goal is to bridge the gap between AI assistants and automated business processes (e.g., Loan Consulting System, Lead Generation, CRM enrichment).

### Core Technologies
- **n8n**: Primary workflow automation platform.
- **MCP**: Protocol for connecting AI to tools and workflows.
- **Markdown**: For high-fidelity documentation and changelogs.
- **Excalidraw**: For visual representations of complex logic and architecture.
- **Node.js/npm**: Used for utility scripts and local validation.
- **Python**: Used in `.skills/skills-mcp-builder/scripts/` for MCP server development.

---

## 2. Build, Lint, and Test Commands

### 2.1 Python Scripts (MCP Builder)
- **Install Dependencies**: `pip install -r .skills/skills-mcp-builder/scripts/requirements.txt`
- **Run Script**: `python .skills/skills-mcp-builder/scripts/<script_name>.py`
- **Lint Python**: `ruff check .` or `ruff check <file.py>`
- **Format Python**: `ruff format .`
- **Run Single Test**: `pytest tests/<test_file>::<TestClass>::<test_method>` (if pytest configured)
- **Run All Tests**: `pytest` or `pytest tests/`

### 2.2 Node.js Scripts
- **Install Dependencies**: `npm install` (in `.opencode/` directory)
- **Validate JSON**: `node -e "JSON.parse(require('fs').readFileSync('filename.json'))"`
- **Validate All Workflows**: `node -e "fs.readdirSync('workflows/').forEach(f => JSON.parse(fs.readFileSync('workflows/'+f)))"`

### 2.3 n8n Workflow Execution
- **Execute Local Workflow**: If n8n is running locally, use `n8n execute:workflow --file <path>`.
- **Trigger Remote Workflow**: Use `mcp__n8n-mcp__n8n_execute_workflow --id <workflow_id>`.
- **Run Single Node**: Via n8n UI or by isolating nodes in temporary workflows.

---

## 3. Code Style Guidelines

### 3.1 Python Style
- **Standard**: PEP 8 compliance. Use `ruff` for linting.
- **Formatting**: 100 char line limit. Use `ruff format .`
- **Imports**: Group in order: Standard Library, Third-Party, Local. Alphabetical within groups.
  ```python
  import os
  import sys
  from pathlib import Path
  
  import requests
  from fastapi import FastAPI
  
  from . import local_module
  ```
- **Types**: Required for function signatures and return types.
  ```python
  def process_data(items: list[str]) -> dict[str, int]:
      ...
  ```
- **Naming**:
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private methods: `_private_method`
- **Error Handling**: Use `try/except` with explicit logging. Never bare `except:`.
  ```python
  try:
      result = risky_operation()
  except ValueError as e:
      logger.error(f"Invalid value: {e}")
      raise
  ```

### 3.2 JavaScript/TypeScript Style
- **Standard**: ES6+ modules. No `var`, only `const`/`let`.
- **Formatting**: 100 char line limit.
- **Imports**: Use named imports where possible.
  ```javascript
  import { readFileSync } from 'fs';
  import { someFunction } from './local-module';
  ```
- **Types**: Use TypeScript types for all function signatures.
- **Naming**:
  - Functions/variables: `camelCase`
  - Classes/Types: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
- **Error Handling**: Use `try/catch` with explicit error logging.

### 3.3 n8n Workflow Design (JSON)
- **File Naming**: `[System Name] - [Function].json` (e.g., `Loan Consulting - Lead Intake.json`).
- **Node Naming**: Descriptive, unique names (e.g., `HTTP: Fetch CRM Data`).
- **Error Handling (Mandatory)**: Every production workflow must connect to an "Error Trigger" node.
- **Retries**: Minimum 3 retries with exponential backoff on HTTP nodes.
- **Complexity**: Break workflows exceeding 20 nodes into sub-workflows.
- **Variables**: Use `{{ $env.VARIABLE_NAME }}`, never hardcode secrets.

---

## 4. Documentation Standards

### 4.1 Markdown
- Use GitHub-flavored Markdown.
- Headers follow `#`, `##`, `###` hierarchy (no level skipping).
- Bold UI elements, backticks for technical terms.
- Update `GEMINI.md` for changes: `### YYYY-MM-DD\n- [Action Verb] Description`

### 4.2 Excalidraw Diagrams
- Store in `excalidraw diagrams/`
- Naming: `UPPER_SNAKE_CASE_DIAGRAM.excalidraw`
- Color coding: Blue (triggers), Green (actions), Yellow (conditions), Red (errors)

---

## 5. Repository Structure
- `/`: Root with workflows, docs (`CLAUDE.md`, `GEMINI.md`, `n8n_MCP_GUIDE.md`)
- `/workflows/`: n8n workflow JSON exports
- `/excalidraw diagrams/`: Visual architecture diagrams
- `/.opencode/`: OpenCode configuration and utilities
- `/.skills/`: Claude Code skill definitions

---

## 6. Safety & Security

### 6.1 Secret Management
- **CRITICAL**: Never commit `.env`, API keys, or plain-text tokens.
- **Scan**: Run `grep` for "Bearer", "API_KEY", "SECRET" before pushing.

### 6.2 Destructive Actions
- Do not delete workflows or documents without explicit user request.
- Create backups (`.bak`) before modifying JSON if not using Git.

### 6.3 Verification
- After JSON edits, validate syntax.
- After MCP updates, run `claude mcp list` to verify connection.

---

## 7. Interaction Guidelines
- **Tone**: Professional, technical, concise.
- **Response Length**: Under 5 lines unless explaining complex architecture.
- **Proactiveness**: Offer to update docs after workflow changes.
- **Clarification**: Ask if target n8n instance is ambiguous.

---

## 8. Agent-Specific Tool Usage
- Prefer `mcp__n8n` tools over static file editing when possible.
- Use `grep`/`glob` to find relevant context before proposing changes.

---

## 9. Git Guidelines
- **Commits**: Imperative mood (e.g., "Add Lead Intake workflow").
- **Atomic Commits**: One workflow or doc change per commit.
- **Branching**: Feature branches for major changes (`feature/crm-integration`).
- **Review**: Use `git diff` before committing to check for secrets.

---

## 10. External References
- **n8n Docs**: [docs.n8n.io](https://docs.n8n.io)
- **MCP Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **Project Guide**: `n8n_MCP_GUIDE.md` for connection strings

---

## 11. Advanced Patterns
- **Modular Workflows**: Use "Execute Workflow" node for sub-workflows.
- **Dynamic Expressions**: JavaScript in expressions: `{{ $json.data.map(i => i.id).join(",") }}`
- **Global State**: Use HTTP nodes to call central database/CRM.
- **AI-Native Nodes**: Prefer "AI Agent" or "Basic LLM Chain" for NLP tasks.

---
*Last Updated: 2026-04-13*
*Memory System: SESSION_MEMORY.md (memories/SESSION_MEMORY.md)*
*Targeted Audience: AI Coding Agents (Claude Code, Gemini CLI, OpenCode, etc.)*