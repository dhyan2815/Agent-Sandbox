# Codex Agentic Workflow - Day 11

**Date:** 2026-06-03
**Day:** 11 of 30-Day AI CLI Experimentation Plan
**Focus:** Codex CLI agentic workflow

## Goal

Use Codex in an agentic, multi-step coding task and document the workflow with a concrete artifact.

## Task Chosen

I created a small CLI utility that scans `docs/experiments/` and generates a markdown report of the experiment docs.

Why this task:

- It is small enough to finish in one session.
- It has a clear implementation path and a useful output.
- It produces a reusable tool for the rest of the 30-day plan.

## What I Built

File: `scripts/codex-agentic-report.py`

The script:

- Scans `docs/experiments/` for markdown files
- Extracts title, date, day, and session metadata when present
- Produces a markdown table summarizing the experiment docs
- Prints to stdout or writes to a file with `--output`

## Workflow Followed

1. Reviewed the Day 11 requirements from `docs/30-day-ai-cli-experimentation-plan.md`
2. Inspected existing experiment docs and the existing Codex reference notes
3. Chose a useful CLI utility instead of a throwaway demo
4. Implemented the script in Python
5. Ran the script against the current repo data
6. Fixed the parser so it handled blockquoted metadata and session fields
7. Re-ran the script to confirm the report output was accurate

## Results

The script found four experiment documents in `docs/experiments/` and generated a compact summary table for them.

Observed data quality notes:

- Some docs use `**Day:**`
- Some docs use `**Session:**`
- Some docs place metadata inside blockquotes
- The parser now handles those patterns without manual cleanup

## Comparison With Claude Code

### Codex CLI

- Better suited here for direct code execution and file editing inside the current workspace
- Worked well for an implementation-first workflow: inspect, build, validate, document
- Useful for a narrow, concrete task where the output is a script and a report

### Claude Code

- More tightly integrated with the repo-specific memory and skill system in this project
- Better positioned for slash-command workflows and persistent project context
- Feels stronger for large context handling and repo-aware guidance

### My takeaway

For this repo, Codex is strongest when the task is a self-contained coding job with a clear artifact. Claude Code looks better for long-lived context, memory, and project-specific workflows. The two are complementary rather than interchangeable.

## Files Created

- `scripts/codex-agentic-report.py`
- `docs/experiments/codex-agentic-workflow-2026-06-03.md`

