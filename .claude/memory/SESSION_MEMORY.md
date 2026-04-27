# SESSION_MEMORY.md — Conversation History & Context Bank

> **Purpose**: This file is the primary second brain for all AI agent sessions in this codebase. Every conversation, decision, and context should be logged here to optimize token usage and enable seamless context retrieval across sessions.
> 
> **Auto-Fetch**: AI agents (OpenCode, Claude Code) should read this file at session start before any other operations.
> 
> **Last Updated**: April 13, 2026

---

## Table of Contents

1. [Session Index](#1-session-index)
2. [Repository Overview](#2-repository-overview)
3. [User Profile & Context](#3-user-profile--context)
4. [Historical Sessions](#4-historical-sessions)
5. [Key Decisions & Outcomes](#5-key-decisions--outcomes)
6. [Current Session State](#6-current-session-state)
7. [Future Intentions](#7-future-intentions)
8. [Appending New Sessions](#8-appending-new-sessions)

---

## 1. Session Index

| Session ID | Date | Summary | Key Actions |
|------------|------|---------|-------------|
| SESSION-001 | 2026-04-13 | Memory System Setup & .gitignore Configuration | Added memories/CAREER.md to .gitignore; Created SESSION_MEMORY.md |
| SESSION-002 | — | (Future sessions will be logged here) | — |

---

## 2. Repository Overview

**Repository Name**: Agent Sandbox
**Path**: `C:\Users\dhyan\Documents\DP Code's\AI\Agent Sandbox`
**GitHub**: https://github.com/dhyan2815/agent-sandbox

### Purpose
An experimental sandbox for CLI-based tools, AI agents, and workflow automations. The repository explores the intersection of AI and command-line interfaces with a focus on:
- Claude Code (agentic AI for code generation)
- Gemini CLI (workflow automation)
- n8n Workflows (event-driven automations)
- Excalidraw Diagrams (system architecture visualization)
- Open Code (CLI-driven development tools)
- DESIGN.md System (brand design documentation)

### Key Directories
```
├── designs/              # Brand design documentation (DESIGN.md system)
├── docs/                 # Agent superpowers & capabilities
├── excalidraw diagrams/  # System architecture & workflow diagrams
├── project markdowns/    # Documentation, plans, and guides
├── workflows/            # n8n workflow definitions (JSON)
├── memories/             # Personal memory files (CAREER.md, SESSION_MEMORY.md)
├── .claude/              # Claude Code configuration
├── .opencode/            # Open Code configuration
│   └── AGENTS.md         # Agentic guidelines for the project
├── CLAUDE.md             # Claude Code instructions
├── GEMINI.md             # Gemini CLI instructions
└── n8n_MCP_GUIDE.md     # n8n MCP integration guide
```

### Core Technologies
- **n8n**: Primary workflow automation platform
- **MCP**: Protocol for connecting AI to tools and workflows
- **Markdown**: For documentation and changelogs
- **Excalidraw**: Visual representations of architecture
- **Node.js/npm**: Utility scripts and local validation
- **Python**: MCP server development (`.skills/skills-mcp-builder/scripts/`)

---

## 3. User Profile & Context

### User Identity
- **Name**: Dhyan Patel
- **Email**: dhyan.work.2815@gmail.com
- **Location**: Gandhinagar, Gujarat, India
- **GitHub**: https://github.com/dhyan2815

### Professional Background
- Final-year Computer Engineering student at Ahmedabad Institute of Technology
- CGPA: 9.05/10
- Title: AI/ML Engineer & Full-Stack Developer
- **Active Job Seeker** (as of April 2026)

### Key Projects
1. **SmokeSignal AI** — Wildfire Detection CNN (72% reduction in false positives, 36k+ images)
2. **Yield Metrics** — Crop Prediction Platform (89% accuracy)
3. **AuraOne** — AI Workspace with custom LLM integration

### Skills & Tech Stack
- **Languages**: Python, JavaScript, TypeScript
- **Frameworks**: React, Node.js, TensorFlow, Scikit-Learn
- **AI/ML**: n8n, LangChain, OpenAI API, RAG pipelines, CNN
- **Tools**: Git, Docker, Firebase
- **Cloud**: AWS, GCP

### Work Experience
- **AI Automation Intern** @ Fortiv Solutions (Jan–Mar 2026)
- **Web Design Intern** @ Sparks To Ideas (May–Jun 2025)
- **Frontend Developer Intern** @ VirtuNexa (Feb–Mar 2025)

---

## 4. Historical Sessions

### SESSION-001 — April 13, 2026

**Agent Used**: OpenCode
**Session Duration**: Single conversation

#### Context
This was the first formal session establishing the memory system for this repository.

#### User Request
1. User wanted to add `memories/CAREER.md` to `.gitignore` to prevent sensitive career information from being exposed in commits
2. User wanted to create a `SESSION_MEMORY.md` file inside `memories/` folder that serves as a second brain
3. User wanted to modify the `.opencode/AGENTS.md` to auto-fetch this memory file during new/existing sessions

#### Actions Taken
1. **Read `.gitignore`** — Found existing entries for .env, .claude/settings.local.json, node_modules/, *.tmp, temp/
2. **Added `memories/CAREER.md`** to `.gitignore` — Prevents sensitive career data from being committed
3. **Read `memories/CAREER.md`** — Confirmed it contains sensitive career information (job search strategy, interview prep, personal goals)
4. **Read `.opencode/AGENTS.md`** — Understood the existing agent configuration
5. **Retrieved git commit history** — Identified 20+ commits showing repository evolution
6. **Created `SESSION_MEMORY.md`** — Comprehensive session memory file with:
   - Session index for chronological tracking
   - Repository overview
   - User profile context
   - This historical session record
   - Key decisions/outcomes
   - Current session state
   - Future intentions
   - Guidelines for appending new sessions

#### Decisions Made
| Decision | Rationale |
|----------|-----------|
| Add memories/CAREER.md to .gitignore | Sensitive personal data (job search, salary targets, interview prep) must not be committed |
| Create SESSION_MEMORY.md (NOT gitignored) | Session memory should be versioned for long-term context |
| Add AGENTS.md instruction to auto-fetch | Ensures LLM always has context without forcing token-heavy retrieval |

---

## 5. Key Decisions & Outcomes

### Code Quality & Style
- **Python**: PEP 8, use `ruff` for linting, 100 char line limit
- **JavaScript**: ES6+ modules, `const`/`let` only, 100 char line limit
- **n8n Workflows**: Error handling mandatory, 3 retries with exponential backoff

### Documentation Standards
- GitHub-flavored Markdown
- Header hierarchy: `#`, `##`, `###` (no skipping)
- Excalidraw diagrams: `UPPER_SNAKE_CASE.excalidraw` in `excalidraw diagrams/`
- Color coding for diagrams: Blue (triggers), Green (actions), Yellow (conditions), Red (errors)

### Safety & Security
- **CRITICAL**: Never commit `.env`, API keys, or plain-text tokens
- Scan for "Bearer", "API_KEY", "SECRET" before pushing
- Never delete workflows/docs without explicit request

### Git Workflow
- Commits: Imperative mood (e.g., "Add Lead Intake workflow")
- Atomic commits: One workflow or doc change per commit
- Feature branches for major changes (`feature/crm-integration`)

---

## 6. Current Session State

**Current Date**: April 13, 2026
**Session ID**: SESSION-001 (Complete)

### Active Context
- Memory system has been established
- `.gitignore` updated with `memories/CAREER.md`
- `SESSION_MEMORY.md` created and versioned
- `.opencode/AGENTS.md` being updated with auto-fetch instructions

### Pending Actions
1. ✅ Create SESSION_MEMORY.md
2. ✅ Update .opencode/AGENTS.md with auto-fetch instructions
3. ✅ Verify SESSION_MEMORY.md is tracked by git (not gitignored)

---

## 7. Future Intentions

### Known Future Sessions
- User is actively job hunting and may use this codebase for:
  - Resume/CV optimization with AI
  - Cover letter generation
  - Interview preparation documentation
  - Project portfolio management

### Repository Evolution Goals
Based on git commit history, the repository has evolved through:
1. Initial setup with README and workflows
2. Addition of n8n workflow plans
3. Excalidraw diagrams for job application chatbot
4. Design system documentation (DESIGN.md)
5. Dependency graph superpowers documentation
6. Skill development (MCP builder, MD to PDF converter)
7. Memory system establishment (current session)

### Recommended Future Sessions to Log
- Any new workflow creation or significant code change
- Job application strategy discussions
- Resume/portfolio reviews
- Interview preparation sessions
- Project planning or architecture decisions

---

## 8. Appending New Sessions

### How to Add a New Session

When a new session occurs, append to this file following this template:

```markdown
### SESSION-XXX — YYYY-MM-DD

**Agent Used**: [OpenCode/Claude Code/Gemini CLI/etc.]
**Session Duration**: [Duration or "Single conversation"]

#### Context
[Brief description of why this session started]

#### User Request
1. [Request 1]
2. [Request 2]
...

#### Actions Taken
1. [Action 1] — [Brief outcome]
2. [Action 2] — [Brief outcome]
...

#### Decisions Made
| Decision | Rationale |
|----------|-----------|
| [Decision] | [Why this was chosen] |

#### Key Outputs
- [Output file 1]
- [Output file 2]
```

### Session ID Convention
- Format: `SESSION-XXX` where XXX is a 3-digit number
- Next session should be: `SESSION-002`
- Increment sequentially: 003, 004, etc.

### Update Index
When adding a new session, update the **Session Index** table in Section 1.

---

## Quick Reference for AI Agents

### Startup Protocol
1. Read this file (`memories/SESSION_MEMORY.md`) immediately
2. Check Session Index for most recent session
3. Read any referenced files from recent sessions
4. Proceed with user's request

### Memory Update Protocol
After each session:
1. Append session record to Section 4
2. Update Session Index in Section 1
3. Note any new decisions in Section 5
4. Add any future intentions in Section 7

### Token Optimization
This file is designed to minimize token usage by:
- Providing structured, searchable sections
- Linking to detailed content rather than duplicating
- Using tables for quick reference
- Maintaining clear hierarchy for navigation

---

*This file is maintained by AI agents operating in this codebase.*
*Last Major Update: April 13, 2026*
*Version: 1.0*
