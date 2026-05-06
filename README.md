# Agent Sandbox

> **Experimental CLI tools & AI agents workspace.** Tests capabilities of Claude Code, Gemini CLI, n8n, and integrations for content creation, automation, and AI-assisted development.

<p align="center">
  <img src="https://img.shields.io/badge/Claude-Code-purple?style=flat-square&logo=anthropic" alt="Claude Code">
  <img src="https://img.shields.io/badge/Gemini-CLI-blue?style=flat-square&logo=google" alt="Gemini CLI">
  <img src="https://img.shields.io/badge/n8n-Workflow%20Automation-ff6e4c?style=flat-square&logo=n8n" alt="n8n">
  <img src="https://img.shields.io/badge/Status-Experimental-orange?style=flat-square" alt="Status">
</p>

## What is This?

A structured playground for experimenting with AI agents and CLI automation tools. Built for rapid prototyping, content generation, and workflow automation using modern agentic AI systems.

### Core Focus Areas

| Tool | Purpose | Docs |
|------|---------|------|
| **Claude Code** | Agentic AI for code generation, refactoring, automation | [CLAUDE.md](./CLAUDE.md) |
| **Gemini CLI** | Workflow automation via Google Gemini models | [GEMINI.md](./GEMINI.md) |
| **n8n** | Event-driven API/service automations | [`workflows/`](./workflows/) |
| **Excalidraw** | Architecture & workflow diagrams | [`visuals/`](./visuals/) |
| **DESIGN.md** | Brand-consistent UI generation system | [`designs/DESIGN.md`](./designs/DESIGN.md) |

---

## Skills System

> Invoke via `/skill-name` or Claude Code Skill tool

Skills are modular AI instruction sets stored in [`skills/`](./skills/). Each skill contains specialized workflows, prompts, and references for specific tasks.

Skills are organized into 5 categories:

### [.skills/content/](.skills/content/) — Content Creation

| Skill | Function |
|-------|----------|
| `voice-builder` | Build personal voice profile from samples |
| `post-writer` | Write in your authentic voice (requires voice.md) |
| `post-formatter` | Apply PAS/AIDA/STAR/SLAY frameworks |
| `hook-generator` | 6 viral hook variations |
| `post-scorer` | Score against performance data |
| `content-matrix` | 32 post ideas from content pillars |
| `graphic-designer` | HTML/CSS or AI-generated visuals |
| `gemini-carousel` | LinkedIn carousels (1080×1350) |
| `gemini-infographic` | Whiteboard-style images |
| `quote-post` | Quote graphics + Gemini prompts |
| `youtube-thumbnail` | CTR-optimized thumbnails |
| `reels-scripting` | Reel scripts from reference content |
| `newsletter-voice` | Newsletter-specific voice profiling |
| `humanizer` | Remove signs of AI-generated writing from text |

### [.skills/linkedin/](.skills/linkedin/) — LinkedIn Tools

| Skill | Function |
|-------|----------|
| `linkedin-profile-optimizer` | Rewrite profile for conversions |
| `linkedin-comment-generator` | Non-generic engagement comments |
| `pinned-comment` | Signature pinned comments |
| `analytics-dashboard` | Interactive performance dashboard |
| `niche-research` | 20 trending stories (7 days) |
| `profile-optimizer` | Full profile rebuild with image prompts |
| `writing-linkedin-posts` | LinkedIn post creation |
| `linkedin-sequence` | 2-message DM sequence after connection accepted |

### [.skills/developer/](.skills/developer/) — Developer Tools

| Skill | Function |
|-------|----------|
| `skills-mcp-builder` | Build MCP servers ([reference](https://modelcontextprotocol.io/)) |
| `skills-md-to-pdf-converter` | Markdown → PDF reports |
| `design-doc-mermaid` | Mermaid diagrams |
| `excalidraw-diagram-generator` | Excalidraw diagrams |
| `web-design-reviewer` | UI/UX audit & automated fixes |
| `use-tinyfish` | Web scraping and automation with natural language |
| `project-idea-validator` | Research project ideas against live data |
| `creating-pr` | GitHub PR creation workflow |
| `issue-workflow` | GitHub Issues management |
| `pr-comment` | Post comments on PRs |
| `ai-wrapper-product` | AI wrapper product development guide |

### [.skills/graphics/](.skills/graphics/) — Graphics & Video

| Skill | Function |
|-------|----------|
| `website-to-hyperframes` | Convert websites to HyperFrames videos |

### [.skills/apify/](.skills/apify/) — Apify Automation

| Skill | Function |
|-------|----------|
| `apify-actor-development` | Build & deploy Apify actors (with full schema references) |
| `apify-content-analysis` | Analyze content using Apify actors |
| `apify-lead-generation` | Automated lead generation via Apify |
| `apify-market-research` | Market research using Apify datasets |
| `apify-trend-analysis` | Trend analysis with Apify actors |

---

### Quick Links

| Resource | Location |
|----------|----------|
| Architecture Docs | [`.claude/docs/ARCHITECTURE.md`](./.claude/docs/) |
| Coding Standards | [`.claude/rules/`](./.claude/rules/) |
| Workflow Examples | [`workflows/`](./workflows/) |
| Visual Diagrams | [`visuals/`](./visuals/) |
| Brand Designs | [`designs/`](./designs/) |

---

## Key Features

- **36+ Specialized Skills** — Content, LinkedIn, developer, Apify automation, and creative tools including web scraping, video generation, and idea validation
- **n8n Workflow Automation** — Telegram chatbots, document assistants, lead generation
- **Brand Design System** — DESIGN.md templates for Apple, Vercel, Spotify, Nike, and more
- **Visual Documentation** — Excalidraw diagrams for workflows and architecture
- **Persistent Memory** — Cross-session context for Claude Code via `.claude/memory/`
- **Learning Resources** — ML guides, prompts, and strategy documentation
- **Project Showcase** — Real-world examples like AuraOne product launch clips

---

## Architecture Highlights

### DESIGN.md System

Inspired by [Google Stitch's design language concept](https://github.com/VoltAgent/awesome-design-md), DESIGN.md files enable brand-consistent UI generation:

> *"A document where an experienced designer explains a brand's visual language to a developer who's seeing it for the first time."*

The system includes 9 standard sections: visual theme, color palette, typography, components, layout, depth, do's/don'ts, responsive behavior, and agent prompts.

### Skill Structure

Each skill follows a consistent pattern:
- `SKILL.md` — Core instructions & workflows
- `references/` — Examples, hooks, templates
- Version tracking for iterations

---

## References & Credits

| Resource | Link |
|----------|------|
| Claude Code | [claude.ai/code](https://claude.ai/code) |
| Gemini CLI | [ai.google.dev/gemini-api/docs](https://ai.google.dev/gemini-api/docs) |
| n8n | [n8n.io](https://n8n.io) |
| MCP Protocol | [modelcontextprotocol.io](https://modelcontextprotocol.io) |
| DESIGN.md Concept | [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) |
| Excalidraw | [excalidraw.com](https://excalidraw.com) |

---

*Experimental playground. Not production-ready. Built for learning and rapid prototyping.*

---

## Recent Additions

- **Apify skills** (5) — Actor development, content analysis, lead generation, market research, trend analysis with full reference docs and actor scripts
- **ai-wrapper-product** skill for AI wrapper product development
- **website-to-hyperframes** skill for converting websites to promotional videos
- **project-idea-validator** skill for researching project ideas against live data
- **use-tinyfish** skill for web scraping and automation using natural language
- **AuraOne Product Launch** demonstration workflow showing video creation capabilities

---

<p align="center">
  <a href="https://github.com/dhyan2815">GitHub</a> · 
  <a href="https://linkedin.com/in/dhyan2815">LinkedIn</a>
</p>