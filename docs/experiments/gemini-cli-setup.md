# Gemini CLI: Explore & Configure — Day 8 Experiment

> **Date:** 2026-05-29
> **Focus:** Set up Gemini CLI and understand its capabilities.
> **Plan Reference:** Day 8 of the [30-Day AI CLI Experimentation Plan](../30-day-ai-cli-experimentation-plan.md)

---

## 1. Environment Overview

| Item | Value |
|------|-------|
| **Gemini CLI Version** | `0.42.0` |
| **Auth Method** | OAuth Personal (`oauth-personal`) |
| **Config Location** | `~/.gemini/config/config.json` |
| **MCP Config** | `~/.gemini/config/mcp_config.json` |
| **Global Memory** | `~/.gemini/GEMINI.md` |
| **Project Memory** | `GEMINI.md` (repo root) |
| **Theme** | Inherits system (`THEME_MODE_INHERIT`) |

Gemini CLI is fully installed and authenticated via Google OAuth. No API key setup was required — the `oauth-personal` flow handles auth automatically.

---

## 2. GEMINI.md Review

The project already has a `GEMINI.md` at the repo root that:
- Describes the high-level architecture of this experimental playground repo.
- Maintains a running **Changelog** of every session (Days 1-7 already logged).
- Documents the memory system (`.claude/memory/` for Claude Code sessions).
- Provides startup guidance for the Gemini agent.

The global `~/.gemini/GEMINI.md` contains persistent user-level rules:
- Always maintain `GEMINI.md` in project root with a changelog.
- Ignore hook execution warnings permanently.

---

## 3. CLI Capabilities & Subcommands

### Core Modes

| Mode | Flag | Description |
|------|------|-------------|
| Interactive | *(default)* | Opens a REPL-style chat session inside the terminal |
| Non-interactive (headless) | `-p / --prompt` | Executes a single prompt and exits |
| Interactive with initial prompt | `-i / --prompt-interactive` | Sends an initial prompt, then drops into interactive mode |
| Plan (read-only) | `--approval-mode plan` | Reads and analyzes code without making changes |
| YOLO | `-y / --yolo` | Auto-approves all tool actions (file edits, commands, etc.) |
| Auto-Edit | `--approval-mode auto_edit` | Auto-approves file edits, prompts for other tools |

### Subcommands

| Subcommand | Purpose |
|------------|---------|
| `gemini mcp` | Manage MCP servers (add, remove, list, enable, disable) |
| `gemini extensions` | Manage extensions (install, uninstall, list, update, link, new, validate, config) |
| `gemini skills` | Manage agent skills (list, enable, disable, install, link, uninstall) |
| `gemini hooks` | Manage hooks (currently: `migrate` from Claude Code) |
| `gemini gemma` | Manage local Gemma model routing for offline use |

### Useful Flags

| Flag | Purpose |
|------|---------|
| `-m / --model` | Override the default model (e.g., `gemini-2.5-pro`) |
| `-o / --output-format` | Output as `text`, `json`, or `stream-json` |
| `-w / --worktree` | Run in an isolated git worktree |
| `-s / --sandbox` | Run in a sandbox environment |
| `-r / --resume` | Resume a previous session (by index or "latest") |
| `--list-sessions` | List available resumable sessions |
| `--include-directories` | Add extra directories to the workspace |
| `--policy` | Load additional policy files |

---

## 4. Configuration Deep-Dive

### Global Permission Grants (`config.json`)

```json
{
  "userSettings": {
    "globalPermissionGrants": {
      "allow": [
        "command(git status)",
        "mcp(supabase/apply_migration)",
        "command(git add)"
      ]
    },
    "themeMode": "THEME_MODE_INHERIT"
  }
}
```

Pre-approved actions: `git status`, `git add`, and Supabase MCP migrations run without confirmation prompts.

### MCP Servers (`mcp_config.json`)

| Server | Transport | Purpose |
|--------|-----------|---------|
| **StitchMCP** | HTTP (via `mcp-remote`) | Google Stitch design tool integration |
| **notion-mcp-server** | stdio (via `npx`) | Notion API access for databases, pages, blocks |

### Extensions

| Extension | Version | Source | Status |
|-----------|---------|--------|--------|
| **Stitch** | 0.1.4 | `gemini-cli-extensions/stitch` (GitHub Release) | ✅ Enabled |

---

## 5. Skills Ecosystem

Gemini CLI discovered **40+ skills** across two locations:
- `~/.gemini/skills/` — built-in/default skills
- `~/.agents/skills/` — user-installed skills (these override defaults on conflict)

### Key Skill Categories

| Category | Skills |
|----------|--------|
| **Content Creation** | `writing-linkedin-posts`, `linkedin-comment-generator-humor`, `reels-scripting`, `youtube-thumbnail`, `voice-builder`, `humanizer` |
| **Development** | `frontend-design`, `ui-ux-pro-max`, `web-artifacts-builder`, `web-design-reviewer`, `test-driven-development`, `systematic-debugging` |
| **Document Tools** | `pdf`, `docx`, `md-to-pdf-converter`, `excalidraw-diagram-generator` |
| **Automation** | `mcp-builder`, `skill-builder`, `project-idea-validator`, `job-search-assistant`, `use-tinyfish` |
| **Workflow** | `writing-plans`, `subagent-driven-development`, `using-git-worktrees`, `verification-before-completion` |

> **Notable Observation:** 18 skill conflicts were detected between `~/.gemini/skills/` and `~/.agents/skills/`. The `~/.agents/skills/` versions take precedence. This is expected when skills are installed in both locations.

---

## 6. Prompt Execution Tests

### Test 1: Basic Arithmetic (headless mode)

```bash
gemini -p "What is 2+2? Reply with just the number." -o text
```

**Result:** `4` ✅
- Correctly answered in plain text mode.
- Startup warnings included: 256-color support, ripgrep fallback, skill conflicts.
- Latency: ~15 seconds (includes cold startup, MCP server init, skill discovery).

### Test 2: Repository Summarization (headless mode)

```bash
gemini -p "Summarize this repository in 2 sentences." -o text
```

**Result:**
> "This repository is an experimental playground dedicated to AI CLI tools, n8n automations, and custom MCP servers, prioritizing workflow orchestration over traditional software development. It features a structured memory system and specialized configurations for agents like Claude Code and Gemini CLI, alongside a collection of AI-driven design, documentation, and content assets."

✅ Correctly read `GEMINI.md` and repo structure to produce an accurate, context-aware summary.

---

## 7. Key Observations & Findings

### Strengths
1. **Workspace-Aware:** Gemini CLI automatically reads `GEMINI.md` from the repo root for project context — no manual setup needed.
2. **Rich Skill System:** 40+ skills available out of the box covering content, development, automation, and workflow orchestration.
3. **MCP Integration:** First-class MCP server management via `gemini mcp` subcommands. Currently connected to Stitch and Notion.
4. **Session Persistence:** `--resume` and `--list-sessions` allow picking up where you left off.
5. **Flexible Approval Modes:** From full manual approval to YOLO mode, giving fine-grained control over trust levels.
6. **Headless Mode:** `-p` flag enables scripting and piping — perfect for automation workflows and CI/CD.

### Issues Noticed
1. **Skill Conflicts:** 18 skills are duplicated between `~/.gemini/skills/` and `~/.agents/skills/`. Consider cleaning up one location.
2. **Ripgrep Missing:** Gemini CLI warns that ripgrep is not available and falls back to GrepTool. Installing ripgrep (`winget install BurntSushi.ripgrep.MSVC`) would improve search performance.
3. **256-Color Support:** Terminal doesn't report 256-color support. Using Windows Terminal or a modern terminal emulator would fix this.
4. **Cold Start Latency:** ~15s cold start due to MCP server initialization and skill discovery. Subsequent prompts in interactive mode are faster.

### Comparison with Claude Code

| Feature | Gemini CLI | Claude Code |
|---------|-----------|-------------|
| Memory System | `GEMINI.md` (project root) | `.claude/memory/` (multi-file) |
| Auth | OAuth Personal | API Key |
| Skills | `~/.gemini/skills/` + `~/.agents/skills/` | `skills/` in repo |
| MCP | Built-in `gemini mcp` management | `.mcp.json` config file |
| Extensions | First-class `gemini extensions` system | N/A |
| Approval Modes | 4 modes (default, auto_edit, yolo, plan) | suggest, auto-edit, full-auto |
| Session Resume | `--resume` flag | `/resume` command |
| Headless/Scripting | `-p` flag with output formats | `-p` flag |
| Git Worktrees | Built-in `-w` flag | Manual setup |

---

## 8. Next Steps (Day 9 Preview)

- Create a Gemini CLI automation script using headless mode (`-p`) for a repetitive task (e.g., automated content generation or code review).
- Explore piping input to Gemini CLI via stdin for batch processing.
- Test model override with `-m` flag to compare different Gemini model versions.
- Document the automation workflow in `docs/workflows/gemini-automation.md`.

---

*Experiment conducted as part of the [30-Day AI CLI Experimentation Plan](../30-day-ai-cli-experimentation-plan.md).*
