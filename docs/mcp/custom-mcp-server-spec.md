# Custom MCP Server Specification: Agent Memory & Reflection MCP

## 1. Overview
The "Agent Memory & Reflection MCP" is a custom Model Context Protocol (MCP) server designed specifically for the Agent Sandbox repository. Its primary purpose is to provide a structured, robust interface for AI CLI tools (like Claude Code, Gemini CLI, Codex CLI) to read, write, update, and search the repository's file-based memory system without needing to perform manual markdown file parsing and text manipulation.

## 2. Motivation
Currently, AI tools operating in this sandbox maintain long-term memory and context by appending text to markdown files like `GEMINI.md`, `MEMORY.md`, and session logs in `.claude/memory/`. 
While functional, relying on plain text file edits is prone to formatting errors, inconsistencies, and context loss during long sessions. A dedicated MCP server will abstract these operations into reliable, typed tools.

## 3. Architecture

### Technology Stack
- **Language**: TypeScript / Node.js
- **Framework**: `@modelcontextprotocol/sdk`
- **Storage**: Local File System (interacting with `.claude/memory/`, `.codex/memory/`, and repository root docs).
- **Transport**: `stdio` (Standard input/output, ideal for local CLI agent integration).

### Core Components
1. **File I/O Module**: Safe wrapper for reading/writing markdown and JSON files.
2. **Markdown Parser/Generator**: Utility to convert structured memory objects into markdown format (e.g., Markdown tables for changelogs).
3. **Search Engine**: Simple text or regex-based search over memory files.
4. **MCP Server Core**: Tool registration and `stdio` server lifecycle management.

## 4. Proposed Tools

The server will expose the following tools to the LLMs:

### `add_memory_entry`
- **Description**: Appends a new entry to a specified memory file (e.g., a new changelog item in `GEMINI.md` or a decision in `decision_log.md`).
- **Parameters**:
  - `file_target` (string): Enum/path representing the target file (e.g., `gemini_changelog`, `claude_decision_log`).
  - `content` (string): The actual memory or changelog text.
  - `date` (string, optional): ISO date string. Defaults to current date.

### `read_session_context`
- **Description**: Reads and aggregates the current active session context across the various memory directories.
- **Parameters**: 
  - `agent_type` (string): e.g., `gemini`, `claude`, `codex`.

### `search_past_decisions`
- **Description**: Searches through past decision logs and progress tracking documents for specific keywords or topics.
- **Parameters**:
  - `query` (string): The search query.

### `update_project_rules`
- **Description**: Proposes updates to standard rule files (like `coding_standards.md` or `AGENTS.md`), ensuring that structural integrity is maintained.
- **Parameters**:
  - `rule_section` (string): Section to update.
  - `new_rule` (string): New rule to append.

## 5. Implementation Plan (Next Steps)
1. Initialize a new Node.js project in `mcp/memory-manager-server/`.
2. Install the MCP SDK.
3. Implement the `add_memory_entry` tool as a proof of concept.
4. Test locally using Claude Code or Gemini CLI via `stdio` transport.
