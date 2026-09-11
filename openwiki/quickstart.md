# Agent Sandbox

> Experimental CLI tools & AI agents workspace. Tests capabilities of Claude Code, Gemini CLI, Codex CLI, n8n, and integrations for content creation, automation, and AI-assisted development.

## What is This?

A structured playground for experimenting with AI agents and CLI automation tools. Built for rapid prototyping, content generation, machine learning practice, and workflow automation using Claude Code, Gemini CLI, Codex CLI, and n8n.

### Core Focus Areas

| Tool / Directory | Purpose | Docs / Path |
|------------------|---------|-------------|
| **Claude Code** | Agentic AI for code generation, refactoring, automation | [CLAUDE.md](../CLAUDE.md) |
| **Gemini CLI** | Workflow automation via Google Gemini models | [GEMINI.md](../GEMINI.md) |
| **Codex CLI** | OpenAI's CLI for code tasks and agentic workflows | [references/codex-tools.md](../references/codex-tools.md) |
| **n8n Workflows** | Event-driven API & service automations | [`n8n-workflows/`](../n8n-workflows/) |
| **Higgsfield AI** | AI image, video, 3D, audio, and full-stack web generation | [`.agents/skills/`](../.agents/skills/) |
| **ML & Python Playground** | Jupyter notebooks & scripts for ML, Pandas, NumPy, and algorithms | [`playground/`](../playground/) |
| **Excalidraw & Visuals** | Architecture & workflow diagrams | [`visuals/`](../visuals/) |
| **DESIGN.md** | Brand-consistent UI generation system | [`designs/DESIGN.md`](../designs/DESIGN.md) |

---

## Directory Structure

```
Agent Sandbox/
├── .agents/skills/      # Higgsfield AI generation & full-stack web skills (5 skills)
├── .claude/skills/      # Modular AI instruction skills across 5 domains (52 skills)
├── .codex/              # Codex CLI memory, docs, and rules
├── .opencode/           # OpenCode configuration
├── architecture/        # Architecture documentation and diagrams
├── content/             # Content templates and planning documents
├── designs/             # DESIGN.md brand UI specifications & templates
├── docs/                # Experiment logs, MCP server specs & technical documentation
├── linkedin-data/       # Cached analytics & reference data for LinkedIn automation
├── mcp/                 # Custom Model Context Protocol (MCP) server implementations
├── n8n-workflows/       # Exported n8n workflow blueprints (Chatbots, Document Assistants)
├── notebooks/           # Jupyter notebooks for NLP (Empathy Detection), ML intro, and practice
├── openwiki/            # OpenWiki documentation (you are here)
├── playground/          # Machine learning (Pandas/NumPy) & Python interview notebooks
├── references/          # Reference documentation (Codex tools, etc.)
├── researches/          # Research documents
├── scripts/             # Automation scripts (GitHub profile quote updater, CLI utilities)
└── visuals/             # Excalidraw architecture & cross-tool workflow diagrams
```

---

## Wiki Sections

- [Skills System](skills.md) — 57 modular AI instruction skills organized by category
- [Content Creation](content.md) — LinkedIn automation, post writing, graphics, and voice profiling
- [Developer Tools](developer-tools.md) — MCP servers, CLI tools, and development aids
- [ML Playground](ml-playground.md) — Jupyter notebooks, NLP, and coding practice
- [Automation](automation.md) — n8n workflows, scripts, and GitHub Actions
- [Architecture](architecture.md) — MCP server architecture and system design
- [Experiments](experiments.md) — 30-day AI CLI experimentation logs
- [Visualizations](visualizations.md) — Excalidraw and Mermaid diagram creation

---

## Getting Started

1. **Skills**: Browse `.claude/skills/` or `.agents/skills/` for available skills. Skills are invoked via `/skill-name` or agent CLI tools.
2. **Content Creation**: Use content skills in `.claude/skills/` for LinkedIn posts, carousels, and graphics. See `voice.md` for voice profiling.
3. **Development**: Explore `mcp/` for custom MCP server implementations. The `playground/` directory has Python notebooks for ML practice.
4. **Automation**: Check `n8n-workflows/` for workflow blueprints and `scripts/` for automation scripts.
5. **Experiments**: Review `docs/experiments/` for 30-day AI CLI experimentation logs.
6. **Visualizations**: Examine `visuals/` for Excalidraw diagrams and `docs/architecture/` for Mermaid diagrams.

---

## Key Configuration Files

- `.env` / `.env.example` — Environment variables (API keys, tokens). See `.env.example` for required variables.
- `skills-lock.json` — Skills inventory and metadata
- `brand-kit.md` — Brand guidelines and visual identity
- `voice.md` — Personal voice profile for content writing
- `GEMINI.md` — Gemini CLI documentation and changelog
- `CLAUDE.md` — Claude Code guidance and memory system
- `AGENTS.md` — Codex guidance and memory system
- `.mcp.json` — MCP server configuration

---

## Agent Instruction Files

- [CLAUDE.md](../CLAUDE.md) — Claude Code guidance: commands, architecture, memory system, coding standards
- [AGENTS.md](../AGENTS.md) — Codex guidance: commands, architecture, memory system, coding standards
- [GEMINI.md](../GEMINI.md) — Gemini CLI documentation and changelog