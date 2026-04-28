---
name: issue-workflow
description: |
  This project uses a custom GitHub Issues workflow with specific conventions that differ from defaults — you must consult this skill rather than giving generic advice. Contains: required issue body template (Problem/Approach/Acceptance Criteria/Tasks/Notes), mandatory branch naming format (issue/{N}-{desc}), label rules (only blocked/stale/pinned allowed), issue sizing with checklists, zombie detection (30-day stale, 44-day auto-close), and triage decision framework. Trigger whenever the conversation touches: creating/structuring issues, branch naming, backlog organization, triage, stale/zombie issues, closing workflow, PR closing keywords, label strategy, issue sizing, blocked issues, or work tracking — even without the word "issue".
version: 0.1.0
---

# GitHub Issues Workflow Methodology

An opinionated, lightweight issue tracking methodology for solo developers and small teams. Issues exist to track work, not to create work — if maintaining your issue tracker takes more than 5 minutes per week, you're doing it wrong.

**Personal repos note:** Native Issue Types and some features are org-only on GitHub. On personal repos, this workflow uses `type:task`, `type:bug`, and `type:feature` labels as fallback. The `/issue-workflow:setup` command detects this automatically.

## Issue Types

| Type | When to Use | Example |
|------|-------------|---------|
| **Task** | Technical work, refactors, maintenance | "Refactor error handling pattern" |
| **Bug** | Something is broken | "Race condition in auto-completion" |
| **Feature** | New functionality | "Allow unlimited paused stints" |

## Issue Sizing

Issues represent a logical chunk of work, not atomic tasks. Group related work with checklists.

**Too granular:** 3 separate issues for 3 empty states
**Right-sized:** 1 issue "Dashboard polish — empty states & error handling" with a checklist

Don't create issues for: sub-tasks (use checklists), work you'll do in the next hour, future phases months away, or things already completed.

## Issue Structure

```markdown
## Problem
[What's broken or missing — the "why"]

## Approach
[How to solve it, or "TBD" if undecided]

## Acceptance Criteria
- [ ] Specific, testable condition
- [ ] Another verifiable outcome

## Tasks
- [ ] Sub-task 1
- [ ] Sub-task 2

## Notes
[Links, constraints, context — omit if none]
```

**Title convention:** `{Area}: {Clear, actionable description}`
- "Dashboard: Add empty states for no-data scenarios"
- "Auth: Handle expired sessions gracefully"

## Labels

Three workflow labels only:

| Label | Purpose |
|-------|---------|
| `blocked` | Can't proceed, waiting on something |
| `stale` | Auto-applied by zombie detection |
| `pinned` | Exempt from stale detection |

Don't use labels for categorization, priority, or assignment — that's overhead that doesn't pay for itself at small scale.

## Branch Naming

```
issue/{NUMBER}-{short-description}
```

Always include issue number, lowercase, hyphens, keep it short. The `issue/` prefix is universal — the issue itself classifies work type.

Examples: `issue/42-dashboard-empty-states`, `issue/15-auth-session-expiry`

## Closing Issues

1. **Via PR:** Include `Closes #XX` or `Fixes #XX` in PR description (auto-closes on merge)
2. **Manual:** `gh issue close {N} --comment "reason" --reason completed`

Before closing, verify all checklist items are completed or explicitly deferred.

## Zombie Issue Management

Issues inactive 30+ days are zombies. The automated stale workflow handles this:
- **Day 30:** Labeled `stale`, comment posted
- **Day 44:** Auto-closed if no activity

Issues with `blocked` or `pinned` labels are exempt.

**Triage questions** — if any answer is "yes", close the issue:
1. Would I mass-close this if I had 100 issues?
2. If this disappeared, would I NOT recreate it?
3. Can I not describe the next concrete step?

## Anti-Patterns

- **Issue inflation** — creating issues "just in case" (close if untouched 3 months)
- **Label obsession** — more than 3 workflow labels means you're overcomplicating it
- **Roadmap duplication** — status in both roadmap doc AND issues
- **Future hoarding** — issues for work months away (put it in a roadmap doc instead)
- **Zombie tolerance** — letting old issues sit open indefinitely