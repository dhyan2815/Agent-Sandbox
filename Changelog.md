# Changelog

This file tracks significant setup and configuration changes for the CLI experiments repository.

### 2026-03-21
- Created `project markdowns/automated_job_discovery_plan.md`: A detailed, node-by-node plan for building an n8n workflow to automate job discovery.

### 2026-03-16
- Fixed n8n MCP connection issues for Claude Code.
- Identified that Claude Code looks for MCP configuration in `~/.claude.json` (project section) instead of `settings.json`.
- Migrated n8n HTTP MCP configuration from `~/.claude/settings.json` to the correct location using `claude mcp add`.
- Verified connection status with `claude mcp list` (status: Connected).
- Cleaned up redundant `mcpServers` entry from `~/.claude/settings.json`.
- Deleted `n8n_MCP_TROUBLESHOOTING.md` after successful resolution.

### 2026-03-15
- Initialized project with `GEMINI.md` (now `Changelog.md`).
- Created `n8n_MCP_GUIDE.md`: A comprehensive guide for connecting n8n instance-level MCP to Claude Code and Gemini CLI.
