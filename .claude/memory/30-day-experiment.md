---
name: 30-day-ai-cli-experiment
description: 30-day AI CLI experimentation plan tracking
type: project
---

# 30-Day AI CLI Experiment

**Started:** 2026-05-16
**Target:** Minimum 7 commits in 30 days

## Experiment Focus

| Tool | Purpose |
|------|---------|
| Claude Code | Primary agent, skill invocation |
| Gemini CLI | Workflow automation |
| Codex CLI | Code execution |
| n8n | Automation workflows |
| MCP | Protocol integration |

## Weekly Breakdown

- **Week 1:** Foundation + MCP exploration (2-3 commits)
- **Week 2:** Automation + integration (2-3 commits)
- **Week 3-4:** Developer tools + advanced integration (3-4 commits)

## Day 1 Status: COMPLETE

- [x] Repository scan complete
- [x] Memory system reviewed
- [x] Experiment document created: `docs/experiments/claude-code-scan-2026-05-16.md`
- [x] Memory entry created

**Commit:** First one (this scan doc)

## Day 2 Status: COMPLETE

- [x] HuggingFace MCP server tested with `hub_repo_search`
- [x] MCP capabilities documented in `docs/experiments/mcp-exploration-2026-05-17.md`
- [x] Available tools enumerated (model search, image gen, docs, papers)

**Commit:** Day 2 - MCP exploration

## Day 4 Status: COMPLETE

- [x] Planned custom Agent Memory & Reflection MCP server
- [x] Created spec document `docs/mcp/custom-mcp-server-spec.md`

## Day 5 Status: COMPLETE

- [x] Set up project structure for `custom-mcp-server`
- [x] Implemented basic server with `stdio` transport
- [x] Added `echo` and `get_timestamp` tools

## Day 6 Status: COMPLETE

- [x] Implemented `add_memory_entry` tool in the custom MCP server
- [x] Added `fs` and `path` logic for file writing
- [x] Updated `GEMINI.md` changelog

**Commit:** Day 6 - Agent Memory MCP server capabilities