# Claude Code Project Structure & Organization Guide

## Overview
This guide provides a token-efficient, scalable directory structure for your Claude Code projects. The structure optimizes for fast onboarding, reduced context reloads, and efficient token consumption across sessions.

---

## Recommended Directory Structure

```
.
├── .claude/
│   ├── agents/                      # AI agent definitions & behaviors
│   │   ├── README.md               # Agent reference index
│   │   ├── system_prompts.md       # Shared system instructions
│   │   └── [agent-name]/
│   │       ├── behavior.md         # Agent's core behavior & rules
│   │       ├── capabilities.json   # Agent capabilities metadata
│   │       └── examples.md         # Example inputs & outputs
│   │
│   ├── rules/                      # Project rules, constraints & guidelines
│   │   ├── README.md               # Rules overview
│   │   ├── coding_standards.md     # Code style & best practices
│   │   ├── naming_conventions.md   # Naming schemes for consistency
│   │   ├── api_contracts.md        # API/interface expectations
│   │   ├── performance.md          # Performance targets & constraints
│   │   └── security.md             # Security & compliance rules
│   │
│   ├── commands/                   # Reusable workflows & command sequences
│   │   ├── README.md               # Command reference
│   │   ├── setup.sh                # Project initialization
│   │   ├── test.sh                 # Test suite runner
│   │   ├── build.sh                # Build process
│   │   └── deploy.sh               # Deployment workflow
│   │
│   ├── memory/                     # Session memory & context
│   │   ├── README.md               # Memory system guide
│   │   ├── project_state.json      # Current project status
│   │   ├── decision_log.md         # Architecture decisions & why
│   │   ├── issues_tracker.md       # Known bugs & TODOs
│   │   ├── progress.md             # Development progress tracking
│   │   └── session_context.md      # Last session summary
│   │
│   ├── patterns/                   # Design patterns & templates
│   │   ├── README.md               # Pattern reference
│   │   ├── component_template.ts   # Component boilerplate
│   │   ├── api_handler.ts          # API handler pattern
│   │   └── error_handling.md       # Error handling patterns
│   │
│   ├── docs/                       # Quick reference documentation
│   │   ├── QUICK_START.md          # 2-minute project intro
│   │   ├── API.md                  # API surface reference
│   │   ├── ARCHITECTURE.md         # System architecture overview
│   │   └── GLOSSARY.md             # Project terminology
│   │
│   └── config.md                   # Project-wide configuration reference
│
├── .opencode                       # (From your current structure)
├── .skills                         # (From your current structure)
├── content/                        # (From your current structure)
├── designs/                        # (From your current structure)
├── docs/                           # (From your current structure)
├── interfaces/                     # (From your current structure)
├── visuals/                        # (From your current structure)
├── workflows/                      # (From your current structure)
├── .env.example                    # (From your current structure)
├── .gitignore                      # (From your current structure)
├── .gitkeep                        # (From your current structure)
├── CLAUDE.md                       # (From your current structure)
├── Changelog.md                    # (From your current structure)
├── GEMINI.md                       # (From your current structure)
├── README.md                       # (From your current structure)
└── n8n_MCP_GUIDE.md               # (From your current structure)
```

---

## Folder-by-Folder Purpose

### `.claude/agents/`
**Purpose:** Define AI behavior, capabilities, and expected outputs for different agents/roles.

**When to use:** When you need Claude Code to:
- Take on specific personas or roles
- Follow consistent behavior patterns across sessions
- Understand its scope and limitations

**Example content:**
```yaml
# agents/code_analyzer/behavior.md
## Role: Code Analyzer

### Responsibilities
- Analyze code for bugs, performance issues
- Suggest optimizations
- Identify security vulnerabilities

### Constraints
- Only analyze, don't modify without explicit approval
- Flag uncertain areas for human review
- Prioritize security over performance

### Output Format
- JSON with severity levels
- Code snippets with line references
```

---

### `.claude/rules/`
**Purpose:** Explicit constraints, standards, and guidelines that Claude Code should follow.

**When to use:** Define consistent behavior across all projects:
- Code style requirements
- Naming conventions
- API contracts
- Performance targets

**Example content:**
```markdown
# rules/naming_conventions.md

## Files & Folders
- kebab-case for files: `user-service.ts`
- PascalCase for classes: `UserService`
- camelCase for functions/variables: `getUserData()`

## Database
- snake_case for columns: `user_id`, `created_at`
- Plural table names: `users`, `transactions`
```

---

### `.claude/commands/`
**Purpose:** Reusable shell scripts and workflows to avoid repeating instructions.

**When to use:** Automate repetitive tasks:
- Project setup
- Test execution
- Build processes
- Deployment workflows

**Benefits:**
- One-liner execution (`bash .claude/commands/test.sh`)
- Consistency across team members
- Reduced token usage by replacing manual step-by-step instructions

**Example:**
```bash
# .claude/commands/test.sh
#!/bin/bash
echo "Running type checking..."
tsc --noEmit

echo "Running unit tests..."
npm test -- --coverage

echo "Running linter..."
npm run lint
```

---

### `.claude/memory/`
**Purpose:** Persistent context that carries between sessions, reducing re-explanation.

**When to use:** Store information that Claude Code needs to understand your project:
- Current project state
- Architecture decisions and rationale
- Known issues and workarounds
- Progress tracking
- Session summaries

**Files:**
- **project_state.json** - Current status, active features, blockers
- **decision_log.md** - Why you chose certain architectures/patterns
- **issues_tracker.md** - Known bugs, TODOs, limitations
- **progress.md** - What's completed, what's next
- **session_context.md** - Summary from previous session

**Benefits:**
- Claude Code remembers context without re-reading entire codebase
- Faster onboarding in new sessions
- Reduced token consumption (reference instead of explain)

**Example:**
```json
// memory/project_state.json
{
  "project_name": "Fortiv AI Automation",
  "current_focus": "n8n email workflow optimization",
  "active_features": [
    "SendGrid integration",
    "Webhook payload processing",
    "CAN-SPAM compliance"
  ],
  "blockers": [
    "Unsubscribe mechanism in Zones C, D, F pending implementation"
  ],
  "last_updated": "2025-04-16T10:30:00Z"
}
```

---

### `.claude/patterns/`
**Purpose:** Reusable code templates and architectural patterns.

**When to use:** Standardize how common tasks are implemented:
- Component templates
- Error handling patterns
- API client setup
- Database query patterns

**Benefits:**
- Consistent code style without instructions
- Faster development (copy-paste templates)
- Single source of truth for best practices

**Example:**
```typescript
// patterns/error_handling.md

## Standardized Error Response Pattern

All API errors should return:
\`\`\`typescript
interface ErrorResponse {
  success: false;
  error: {
    code: string;        // e.g., "INVALID_EMAIL"
    message: string;     // User-friendly message
    details?: Record<string, unknown>;
    timestamp: ISO8601;
  };
}
\`\`\`
```

---

### `.claude/docs/`
**Purpose:** Quick reference documentation to avoid re-explaining the project.

**Key files:**
- **QUICK_START.md** - 2-min project summary (what it does, how to run it)
- **API.md** - API endpoints, parameters, responses
- **ARCHITECTURE.md** - System design, data flow, dependencies
- **GLOSSARY.md** - Project-specific terminology

**Benefits:**
- Claude Code reads these first to understand scope
- No token waste re-explaining architecture
- New team members onboard faster

---

## Token Optimization Strategies

### 1. **Reference Instead of Explain**
**Bad (wastes tokens):**
```
Hey Claude, my project has a SendGrid email system with webhooks 
that process events, and we need to add unsubscribe handling...
```

**Good (token-efficient):**
```
Reference: .claude/memory/project_state.json
Next task: Implement unsubscribe handling in Zones C, D, F
See: .claude/docs/ARCHITECTURE.md for system design
```

### 2. **Use Decision Log Instead of Re-discussing**
Once you decide on an architecture, document it:
```markdown
# memory/decision_log.md

## Decision: SendGrid over competing email providers
**Date:** 2025-04-10
**Reason:** Built-in webhook event handling, cost-effective, good n8n integration
**Trade-offs:** Limited customization vs ease of use
**Status:** Implemented, no regrets
```

Next time you reference it, Claude Code knows the context without re-explaining.

### 3. **Organize by Scope**
Place frequently-accessed info in smaller files:
- `.claude/rules/naming_conventions.md` (quick ref)
- `.claude/docs/QUICK_START.md` (first read)
- `.claude/memory/session_context.md` (session summary)

Larger docs go into the main `README.md` or separate `/docs` folder.

### 4. **Use Commands for Repetitive Tasks**
Instead of:
```
Can you run: npm test, then npm run lint, then build?
```

Create `.claude/commands/test.sh`:
```bash
npm test && npm run lint && npm build
```

Then: `bash .claude/commands/test.sh` (8 tokens vs. 50+ tokens)

### 5. **Session Summaries**
Before ending a session, update `.claude/memory/session_context.md`:
```markdown
# Session Summary: 2025-04-16

## What Got Done
- ✅ Fixed SendGrid webhook parsing
- ✅ Added error logging
- ⏳ Unsubscribe mechanism (50% complete)

## Next Steps
1. Implement unsubscribe guard in Zone C
2. Test with real SendGrid events
3. Add to deployment checklist

## Blockers
- Zone D validation pending API response

## Files Modified
- `workflows/email_campaign.ts`
- `integrations/sendgrid.ts`
```

Next session, Claude Code reads this in seconds instead of re-reading the entire workflow.

---

## Implementation Plan

### Phase 1: Setup (First Session)
```bash
mkdir -p .claude/{agents,rules,commands,memory,patterns,docs}
touch .claude/{agents,rules,commands,memory,patterns,docs}/README.md
```

### Phase 2: Populate Structure (First Week)
1. Write `.claude/docs/QUICK_START.md`
2. Document current architecture in `.claude/docs/ARCHITECTURE.md`
3. Create `.claude/rules/coding_standards.md`
4. Write `.claude/memory/project_state.json`
5. Create useful shell scripts in `.claude/commands/`

### Phase 3: Maintain (Ongoing)
- Update `.claude/memory/session_context.md` at end of each session
- Add decisions to `.claude/memory/decision_log.md` as you make them
- Add patterns to `.claude/patterns/` as they stabilize
- Refine rules as your project matures

---

## Example: Your n8n Email Campaign Project

```
.claude/
├── agents/
│   └── email_workflow_specialist/
│       ├── behavior.md
│       └── capabilities.json
├── rules/
│   ├── coding_standards.md    # n8n node patterns
│   ├── can_spam.md            # Compliance rules
│   └── webhook_contracts.md   # Payload formats
├── commands/
│   ├── test_webhook.sh        # Simulate webhook events
│   └── validate_compliance.sh  # Check CAN-SPAM
├── memory/
│   ├── project_state.json     # "Zones A-H, SendGrid configured, Zone C-F pending unsubscribe"
│   ├── decision_log.md        # "Why SendGrid, why Zone structure"
│   └── issues_tracker.md      # "Unsubscribe guard pending, Zone D validation issue"
├── docs/
│   ├── QUICK_START.md         # "Email campaign automation with SendGrid"
│   ├── ARCHITECTURE.md        # "8 zones, webhook flow, Google Sheets sync"
│   └── API.md                 # Webhook payload schemas
└── patterns/
    ├── zone_node_template.json
    └── sendgrid_event_handler.js
```

---

## Checklist: Is Your Structure Optimized?

- [ ] Session context written in `.claude/memory/` before ending session?
- [ ] Decision log updated when making architectural choices?
- [ ] Repetitive instructions converted to scripts in `.claude/commands/`?
- [ ] New patterns documented in `.claude/patterns/` once stable?
- [ ] Rules explicitly written in `.claude/rules/` (not just understood)?
- [ ] QUICK_START.md is 1-2 minutes to read?
- [ ] All file references use `.claude/` shortcuts instead of re-explaining?

---

## Files to Create First (Priority Order)

1. `.claude/docs/QUICK_START.md` - Describe your project in 100 words
2. `.claude/memory/project_state.json` - Current status, active features, blockers
3. `.claude/rules/coding_standards.md` - Code style you follow
4. `.claude/memory/session_context.md` - Summary from last session
5. `.claude/docs/ARCHITECTURE.md` - How the system works (with diagram reference)

These 5 files will optimize 80% of token waste.

---

## Pro Tip: Claude Code Prompt Template

Start each Claude Code session with:

```
Reference context:
- QUICK_START: .claude/docs/QUICK_START.md
- Current state: .claude/memory/project_state.json
- Architecture: .claude/docs/ARCHITECTURE.md

Task: [Your specific task]
See blocking issues in: .claude/memory/issues_tracker.md
```

This loads context in one instruction instead of 10.
