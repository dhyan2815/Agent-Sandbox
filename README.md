# Agent Sandbox

> **Experimental CLI tools & AI agents workspace.** Tests capabilities of Claude Code, Gemini CLI, n8n, and integrations for content creation, automation, and AI-assisted development.

<p align="center">
  <img src="https://img.shields.io/badge/Claude-Code-purple?style=flat-square&logo=anthropic" alt="Claude Code">
  <img src="https://img.shields.io/badge/Gemini-CLI-blue?style=flat-square&logo=google" alt="Gemini CLI">
  <img src="https://img.shields.io/badge/Codex-CLI-orange?style=flat-square&logo=openai" alt="Codex CLI">
  <img src="https://img.shields.io/badge/n8n-Workflow%20Automation-ff6e4c?style=flat-square&logo=n8n" alt="n8n">
  <img src="https://img.shields.io/badge/Status-Experimental-orange?style=flat-square" alt="Status">
</p>

## What is This?

A structured playground for experimenting with AI agents and CLI automation tools. Built for rapid prototyping, content generation, machine learning practice, and workflow automation using Claude Code, Gemini CLI, Codex CLI, and n8n.

### Core Focus Areas

| Tool / Directory | Purpose | Docs / Path |
|------------------|---------|-------------|
| **Claude Code** | Agentic AI for code generation, refactoring, automation | [CLAUDE.md](./CLAUDE.md) |
| **Gemini CLI** | Workflow automation via Google Gemini models | [GEMINI.md](./GEMINI.md) |
| **Codex CLI** | OpenAI's CLI for code tasks and agentic workflows | [references/codex-tools.md](./references/codex-tools.md) |
| **n8n Workflows** | Event-driven API & service automations | [`n8n-workflows/`](./n8n-workflows/) |
| **Higgsfield AI** | AI image, video, 3D, audio, and full-stack web generation | [`.agents/skills/`](./.agents/skills/) |
| **ML & Python Playground** | Jupyter notebooks & scripts for ML, Pandas, NumPy, and algorithms | [`playground/`](./playground/) |
| **Excalidraw & Visuals** | Architecture & workflow diagrams | [`visuals/`](./visuals/) |
| **DESIGN.md** | Brand-consistent UI generation system | [`designs/DESIGN.md`](./designs/DESIGN.md) |

---

## Directory Structure & Workspace Layout

```
Agent Sandbox/
├── .agents/skills/      # Higgsfield AI generation & full-stack web skills (5 skills)
├── .claude/skills/      # Modular AI instruction skills across 5 domains (52 skills)
├── designs/             # DESIGN.md brand UI specifications & templates
├── docs/                # Experiment logs, MCP server specs & technical documentation
├── linkedin-data/       # Cached analytics & reference data for LinkedIn automation
├── mcp/                 # Custom Model Context Protocol (MCP) server implementations
├── n8n-workflows/       # Exported n8n workflow blueprints (Chatbots, Document Assistants)
├── notebooks/           # Jupyter notebooks for NLP (Empathy Detection), ML intro, and practice
├── openwiki/            # Open source repo documentation agent workspace
├── playground/          # Machine learning (Pandas/NumPy) & Python interview notebooks
├── scripts/             # Automation scripts (GitHub profile quote updater, CLI utilities)
└── visuals/             # Excalidraw architecture & cross-tool workflow diagrams
```

---

## Skills System

> Invoke via `/skill-name` or agent CLI tools

Skills are modular AI instruction sets stored in [`.claude/skills/`](./.claude/skills/) and [`.agents/skills/`](./.agents/skills/). Each skill contains specialized workflows, prompts, and references for specific tasks.

Skills are organized into 5 core categories across 57 specialized skills:

### Content Creation

| Skill | Function |
|-------|----------|
| `voice-builder` | Build personal voice profile from samples |
| `post-writer` | Write in your authentic voice (requires voice.md) |
| `post-formatter` | Apply PAS/AIDA/STAR/SLAY frameworks |
| `hook-generator` | 6 viral hook variations |
| `post-scorer` | Score against performance data |
| `content-matrix` | 32 post ideas from content pillars |
| `graphic-designer` | HTML/CSS, AI-generated visuals, and SVG vector graphics |
| `gemini-carousel` | LinkedIn carousels (1080×1350) |
| `gemini-infographic` | Whiteboard-style images |
| `quote-post` | Quote graphics + Gemini prompts |
| `youtube-thumbnail` | CTR-optimized thumbnails |
| `reels-scripting` | Reel scripts from reference content |
| `newsletter-voice` | Newsletter-specific voice profiling |
| `humanizer` | Remove signs of AI-generated writing from text |
| `canvas-design` | Create visual art in .png and .pdf using design philosophy |
| `chatgpt-image-ad` | Meta ad creative generation for Arcads & GPT-Image-2 |

### LinkedIn Tools

| Skill | Function |
|-------|----------|
| `linkedin-profile-optimizer` | Rewrite profile for conversions (URL-based extraction) |
| `linkedin-comment-generator` | Non-generic engagement comments (15 variants: mood, humor & Analytical Connector) |
| `pinned-comment` | Signature pinned comments |
| `analytics-dashboard` | Interactive performance dashboard |
| `niche-research` | 20 trending stories (7 days) |
| `profile-optimizer` | Full profile rebuild with image prompts |
| `writing-linkedin-posts` | LinkedIn post creation |
| `linkedin-sequence` | 2-message DM sequence after connection accepted |
| `media-type-suggestor` | Suggest LinkedIn media types based on post content |

### Developer Tools

| Skill | Function |
|-------|----------|
| `visual-explainer` | HTML diagrams, slides, diff/plan reviews, data tables |
| `skills-mcp-builder` | Build MCP servers ([reference](https://modelcontextprotocol.io/)) |
| `skills-md-to-pdf-converter` | Markdown → PDF reports |
| `design-doc-mermaid` | Mermaid diagrams |
| `excalidraw-diagram-generator` | Excalidraw diagrams |
| `web-design-reviewer` | UI/UX audit & automated fixes |
| `use-tinyfish` | Web scraping and automation with natural language |
| `project-idea-validator` | Research project ideas against live data |
| `creating-pr` | GitHub PR creation workflow |
| `issue-workflow` | GitHub Issues management |
| `gh-issues` | Auto-fix GitHub issues using parallel sub-agents |
| `pr-comment` | Post comments on PRs |
| `ai-wrapper-product` | AI wrapper product development guide |
| `gog` | Google Workspace CLI for Gmail, Calendar, Drive, Contacts, Sheets, and Docs |
| `pdf-reading` | Read, inspect, or extract content from PDF files |
| `pdf` | Comprehensive PDF processing (merge, split, OCR, forms, watermark) |
| `readme-generator` | Generates comprehensive README.md files by analyzing codebase structure |
| `ui-design-system` | UI design system toolkit with design token generation |
| `humanize-code` | Remove robotic AI structures and patterns from code and text |
| `code-refactoring` | Automated code refactoring & clean code transformations |

### Graphics, Video & Higgsfield AI

| Skill | Function |
|-------|----------|
| `higgsfield-generate` | Generate images, videos, 3D assets, and audio via Higgsfield AI |
| `higgsfield-marketplace-cards` | Generate e-commerce compliant product cards & A+ content |
| `higgsfield-product-photoshoot` | Generate professional brand and studio product photography |
| `higgsfield-soul-id` | Train identity-faithful Soul Character facial models |
| `higgsfield-websites` | Build, edit & deploy full-stack React 19 + TanStack Start web apps |
| `website-to-hyperframes` | Convert websites to HyperFrames videos |
| `pptx` | Generate and validate professional OOXML PowerPoint presentations |

### Apify Automation

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
| Architecture Docs | [`.claude/docs/ARCHITECTURE.md`](./.claude/docs/ARCHITECTURE.md) |
| Coding Standards | [`.claude/rules/`](./.claude/rules/) |
| n8n Workflows | [`n8n-workflows/`](./n8n-workflows/) |
| Visual Diagrams | [`visuals/`](./visuals/) |
| Brand Designs | [`designs/`](./designs/) |
| ML & NLP Notebooks | [`notebooks/`](./notebooks/) |
| ML & Python Playground | [`playground/`](./playground/) |
| Automation Scripts | [`scripts/`](./scripts/) |

---

## Key Features

- **57 Specialized AI Skills** — Distributed across `.claude/skills/` and `.agents/skills/`, covering content creation, LinkedIn optimization, ad creative generation, developer utilities, Apify scraping, presentations, and Higgsfield AI generation.
- **Higgsfield AI & Full-Stack Web Suite** — Multi-modal generation for studio product photography, marketplace cards, Soul identity training, and full-stack React 19 + TanStack Start web deployment on Cloudflare Workers.
- **ML, NLP & Python Practice Playground** — Structured notebooks in `notebooks/` (Empathy Detection NLP) and `playground/` for Pandas data manipulation, NumPy arrays, SQL, and Python interview algorithms.
- **Automated Profile & Scripting Workflows** — Native GitHub Actions workflows and PowerShell scripts (`scripts/update-profile-quote.ps1`, `gemini-summarize.ps1`) for daily GitHub profile README quote rotation and headless CLI summarization.
- **Custom MCP Server Suite** — Advanced Model Context Protocol server implementations in `mcp/` featuring persistent memory entries, repository file search, and structured logging.
- **n8n Workflow Automation** — Event-driven automations in `n8n-workflows/` for Telegram chatbots, AI document assistants, and lead generation.
- **Brand Design System** — DESIGN.md templates in `designs/` for brand-consistent UI generation across Apple, Vercel, Spotify, Nike, and more.
- **Visual & Diagrammatic Docs** — Excalidraw and Mermaid architecture diagrams in `visuals/` and `docs/`.

---

## Architecture Highlights

### DESIGN.md System

Inspired by [Google Stitch's design language concept](https://github.com/VoltAgent/awesome-design-md), DESIGN.md files enable brand-consistent UI generation:

> *"A document where an experienced designer explains a brand's visual language to a developer who's seeing it for the first time."*

The system includes 9 standard sections: visual theme, color palette, typography, components, layout, depth, do's/don'ts, responsive behavior, and agent prompts.

### Multi-Root Skill & Agent Structure

The repository organizes AI agent instructions across two customization roots:
- `.claude/skills/` — Task-specific skills for content creation, code manipulation, document processing, and workflows.
- `.agents/skills/` — Domain-specific Higgsfield AI suites for creative generation and web app deployment.

Each skill follows a consistent pattern:
- `SKILL.md` — Core instructions & workflows with YAML frontmatter
- `references/` & `scripts/` — Supporting templates, prompt references, and automation scripts

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

- **ChatGPT Image Ad Skill (`.claude/skills/chatgpt-image-ad`)** — Integrated Arcads / GPT-Image-2 ad creative generation skill for high-converting Meta & paid-social ads.
- **NLP & Machine Learning Notebooks (`notebooks/`)** — Added `LL_Empathy_Detection.ipynb` for NLP empathy detection modeling along with ML introduction and practice notebooks.
- **Native GitHub Action Automation** — Migrated profile README quote rotation natively into GitHub Actions for automated daily execution across repositories.
- **Higgsfield AI Skill Suite (`.agents/skills/`)** — Integrated 5 full-stack Higgsfield skills: `higgsfield-generate`, `higgsfield-marketplace-cards`, `higgsfield-product-photoshoot`, `higgsfield-soul-id`, and `higgsfield-websites` (React 19 + TanStack Start SSR deployment).
- **Skill Suite Expansion (57 Total Skills)** — Added `chatgpt-image-ad`, `code-refactoring`, PowerPoint OOXML generator (`pptx`), full PDF processing suite (`pdf`), AI code de-roboticizer (`humanize-code`), and SVG vector support in `graphic-designer`.

---

<p align="center">
  <a href="https://github.com/dhyan2815">GitHub</a> · 
  <a href="https://linkedin.com/in/dhyan2815">LinkedIn</a>
</p>