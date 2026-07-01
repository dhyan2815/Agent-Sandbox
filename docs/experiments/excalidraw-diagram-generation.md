# Day 16 Experiment: Excalidraw Diagram Generation

## Objective

Use the `excalidraw-diagram-generator` skill to create visual architecture and workflow diagrams for the Agent Sandbox project, covering both the custom MCP server internals and the cross-tool integration pattern.

## Skill Review

The `excalidraw-diagram-generator` skill supports 9 diagram types (flowchart, relationship, mind map, architecture, DFD, swimlane, class, sequence, ER). Key takeaways from the skill review:

- Output format is raw `.excalidraw` JSON, directly openable in [excalidraw.com](https://excalidraw.com) or the VS Code extension.
- Element types: `rectangle`, `ellipse`, `diamond`, `arrow`, `text`.
- Color coding convention: primary (`#a5d8ff`), secondary (`#b2f2bb`), important (`#ffd43b`), alerts (`#ffc9c9`).
- All text must use `fontFamily: 5` (Excalifont) for visual consistency.

## Diagrams Created

### 1. MCP Server Architecture (`visuals/mcp-server-architecture.excalidraw`)

**Type:** Architecture Diagram

**Components visualized:**
- **AI CLI Client** (yellow) — Claude Code or Gemini CLI sending JSON-RPC requests
- **StdioServerTransport** (blue) — MCP SDK transport layer over stdin/stdout
- **MCP Server Core** (green) — request dispatcher, input validation, structured logging, error handler, tool annotations
- **5 Registered Tools** — color-coded by read-only (purple) vs. write (red):
  - `mcp_echo` (read-only)
  - `mcp_get_timestamp` (read-only)
  - `mcp_add_memory_entry` (write, file-system)
  - `mcp_repo_list_files` (read-only, recursive)
  - `mcp_repo_search_content` (read-only, full-text)
- **Repository FS** (yellow) — REPO_ROOT-scoped file system access
- **Structured Logger** (orange) — JSON output to stderr

### 2. Cross-Tool Workflow (`visuals/cross-tool-workflow.excalidraw`)

**Type:** Architecture / Relationship Diagram

**Components visualized:**
- **Developer** (center, yellow ellipse) — the human operator
- **Claude Code** (blue) — primary agentic interface for skills, memory, and code generation
- **Gemini CLI** (green) — headless automation and batch summarization
- **Custom MCP Server** (purple) — shared context layer for both CLIs via stdio
- **Agent Sandbox Repo** (yellow) — central repository with skills, docs, workflows, and memory files
- **n8n Workflows** (red) — webhook and chatbot automations
- **GitHub** (gray) — remote origin for version control

**Key insight:** Both Claude Code and Gemini CLI connect to the same MCP server via stdio, creating a shared context layer that allows either tool to read/write memory and search the repository through a unified interface.

## How to View

1. Open [excalidraw.com](https://excalidraw.com)
2. Click **Open** and select the `.excalidraw` file
3. Or install the **Excalidraw** VS Code extension and open directly in the editor
