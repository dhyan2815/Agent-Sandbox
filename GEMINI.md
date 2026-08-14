# GEMINI.md

This file provides guidance to the Gemini CLI when working with code in this repository.

## Common Commands
- **Build**: No build step defined.
- **Lint**: No linter configured.
- **Run Tests**: No test suite detected.

## High-Level Architecture
This repository is an experimental playground for CLI tools and does not contain traditional source code.
- **Project Layout**: The repository is organized into:
  - `workflows/` - n8n automation definitions
  - `visuals/` - Excalidraw diagrams and architecture visuals
  - `designs/` - Brand design documentation (DESIGN.md system)
  - `docs/` - Project documentation
  - `memories/` - Session knowledge base
  - `content/` - Content assets (carousels, templates)
  - `.claude/` - Claude Code knowledge base (memory, docs, rules)
- **Core Focus**: Experiments with Claude Code, Gemini CLI, n8n, and other CLI-based tools.

## Changelog
- **2026-04-21**: Initialized Claude Code configuration and command personas.
    - Updated `.claude/settings.json` with secure permissions.
    - Defined agent personas: Planner, Coder, Reviewer, Tester, Orchestrator.
    - Created context templates for tracking Plans, Changes, Reviews, and Test Results.
    - Synchronized master templates in `.claude/files/`.
- **2026-04-22**: Modified `linkedin-profile-optimizer` skill to use LinkedIn URL as primary input.
    - Updated `SKILL.md` to remove PDF/pasted text dependencies.
    - Refined input handling to prioritize browser-based profile extraction from URLs.
- **2026-05-24**: Day 4 of AI CLI Experimentation Plan.
    - Planned custom Agent Memory & Reflection MCP server.
    - Created spec document `docs/mcp/custom-mcp-server-spec.md`.

- **2026-05-25**: Day 5 of AI CLI Experimentation Plan.
    - Set up project structure for `custom-mcp-server`.
    - Implemented basic server with `stdio` transport.
    - Added `echo` and `get_timestamp` tools.

- **2026-05-26**: Day 6 of AI CLI Experimentation Plan.
    - Implemented `add_memory_entry` tool in the custom MCP server for file-based memory updates.
    - Setup `fs` and `path` logic for file writing to repository root.

- **2026-05-27**: Day 6 & Day 7 of AI CLI Experimentation Plan.
    - Conducted an audit of existing n8n workflows and created `docs/workflow-audit.md`.
    - Enhanced the `DP Job Application - ChatBot.json` n8n workflow by swapping the Gemini 2.5 Flash node with a Claude 3 Haiku node.

- **2026-05-29**: Day 8 of AI CLI Experimentation Plan.
    - Explored Gemini CLI v0.42.0 capabilities: subcommands, approval modes, skills, extensions, MCP management.
    - Tested headless prompt execution (`-p` flag) with basic arithmetic and repo summarization.
    - Documented findings in `docs/experiments/gemini-cli-setup.md`.

- **2026-05-31**: Day 9 of AI CLI Experimentation Plan.
    - Created a simple repetitive task automation script utilizing the Gemini CLI's headless mode (`-p` flag).
    - Created `scripts/gemini-summarize.ps1` for automating markdown file summarization.
    - Documented workflow in `docs/workflows/gemini-automation.md`.

- **2026-06-05**: Updated LinkedIn Data Cache README and Main Repository README.
    - Updated `linkedin-data/README.md` to remove obsolete reference to root-level post cache file.
    - Refined refresh instructions to match the latest `post-scorer` skill configurations.
    - Updated main `README.md` to reference `.claude/skills/` instead of `skills/` at root, and included the 7 new specialized skills (`pdf-reading`, `gog`, `gh-issues`, `ui-design-system`, `canvas-design`, `readme-generator`, `media-type-suggestor`) in their respective categories.
    - Documented and saved changes in the repository.

- **2026-06-06**: Installed `pptx` skill for PowerPoint presentation generation.
    - Committed 112 files across 12 structured commits covering license, skill definition, documentation, OOXML schemas, validation scripts, slide manipulation utilities, and office helpers.
    - Skill located at `.claude/skills/pptx/`.

- **2026-06-22**: Day 13 of AI CLI Experimentation Plan.
    - Enhanced `linkedin-comment-generator` skill by adding a new "Analytical Connector" variant.
    - Updated `SKILL.md` to support data-driven comments for quantitative posts and trend predictions.

- **2026-06-23**: Day 14 of AI CLI Experimentation Plan.
    - Enhanced `graphic-designer` skill by adding a new SVG Vector Graphic format (Path C).
    - Updated `SKILL.md` with SVG constraints, templates, and selection options.
    - Created a sample SVG graphic for "3 Pillars of Modern Agentic Workflows".
    - Documented the enhancement in `docs/experiments/graphic-designer-svg-enhancement.md`.

- **2026-06-30**: Day 15 of AI CLI Experimentation Plan.
    - Reviewed `mcp_best_practices.md` and applied patterns to custom MCP server.
    - Added structured JSON logging (stderr), centralized error handling, and input validation helpers.
    - Implemented two new complex tools: `mcp_repo_list_files` and `mcp_repo_search_content`.
    - Added MCP tool annotations (readOnlyHint, destructiveHint, idempotentHint, openWorldHint) to all tools.
    - Renamed tools with `mcp_` service prefix per naming conventions.
    - Updated test client and verified all 5 tools plus error handling.
    - Documented findings in `docs/experiments/mcp-server-advanced-features.md`.

- **2026-07-01**: Day 16 of AI CLI Experimentation Plan.
    - Reviewed `excalidraw-diagram-generator` skill (9 diagram types, JSON format, color conventions).
    - Generated MCP server architecture diagram (`visuals/mcp-server-architecture.excalidraw`).
    - Generated cross-tool workflow diagram (`visuals/cross-tool-workflow.excalidraw`).
    - Documented findings in `docs/experiments/excalidraw-diagram-generation.md`.

- **2026-07-02**: Day 17 of AI CLI Experimentation Plan.
    - Reviewed `design-doc-mermaid` skill (4 diagram types, Unicode symbols, resilient workflow, Python utilities).
    - Created MCP server architecture diagram with Mermaid (`docs/architecture/mcp-server-architecture.md`).
    - Created 4 sequence diagrams for tool interactions (`docs/architecture/mcp-server-sequences.md`).
    - Documented findings in `docs/experiments/mermaid-diagram-generation.md`.

- **2026-07-04**: Day 18 of AI CLI Experimentation Plan.
    - Tested `humanizer` skill with AI-generated cybersecurity text.
    - Identified gaps (rhetorical questions, adverb transitions, redundant word pairs) and added them to `SKILL.md` (Categories 30, 31, 32).
    - Documented test cases, analysis of tells, and humanized output in `docs/experiments/humanizer-testing-and-refinement.md`.

- **2026-07-05**: Day 19 of AI CLI Experimentation Plan.
    - Reviewed `apify-lead-generation` skill (10+ Actors, 5-step workflow, run_actor.js script).
    - Designed a concrete lead generation workflow targeting tech startups in Mumbai via Google Places Actor.
    - Documented skill architecture, planned workflow, setup checklist, and key learnings in `docs/experiments/apify-lead-gen-test.md`.

- **2026-07-06**: Automated profile README quote updates and integrated Higgsfield skills.
    - Created `scripts/update-profile-quote.ps1` to pick random programming/motivational quotes, update the capsule-render banner in `dhyan2815/README.md` locally, and push the changes via Git/GitHub CLI.
    - Ran the script, successfully updating the quote to "One of my most productive days was throwing away 1000 lines of code. - Ken Thompson" and pushing it to the remote repository.
    - Ran the script again, updating the quote to "Simplicity is the ultimate sophistication. - Leonardo da Vinci" and pushing it to the remote repository.
    - Integrated Higgsfield skills (`higgsfield-generate`, `higgsfield-marketplace-cards`, `higgsfield-product-photoshoot`, `higgsfield-soul-id`, `higgsfield-websites`) with 42 total files committed across 13 structured commits.

- **2026-07-07**: Updated profile README quote script and executed it.
    - Updated `scripts/update-profile-quote.ps1` to replace long quotes with a curated list of short quotes (under 42 characters) to prevent capsule-render banner cutting off on mobile/narrow viewports.
    - Ran the script, successfully updating the quote to "Be yourself; everyone else is taken. - Oscar Wilde" and pushed the changes to the GitHub repository.
    - Refined `scripts/update-profile-quote.ps1` to exclusively feature tech-motivated quotes by famous tech authors and computer scientists, and fixed encoding/character parsing bugs.
    - Ran the script again, updating the quote to "Write programs to work together. - Doug McIlroy".

- **2026-07-08**: Updated primary Agent Sandbox repository README.
    - Analyzed recent commit history and directory structure changes across `n8n-workflows/`, `playground/`, `scripts/`, `mcp/`, and multi-root skills (`.claude/skills/` and `.agents/skills/`).
    - Updated `README.md` to document the full inventory of 55 specialized skills across all 5 domains plus Higgsfield AI suites (`higgsfield-generate`, `higgsfield-marketplace-cards`, `higgsfield-product-photoshoot`, `higgsfield-soul-id`, `higgsfield-websites`).
    - Added a clear Directory Structure & Workspace Layout diagram and refreshed Recent Additions and Core Focus Areas.

- **2026-07-08**: Updated personal profile README quote.
    - Ran the script `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "Code never lies, comments sometimes do. - Ron Jeffries".

- **2026-07-09**: Updated personal profile README quote, and automated LinkedIn insights.
    - Ran the script `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "No Silver Bullet. - Fred Brooks".
    - Automated LinkedIn data retrieval via Apify, performed performance data analysis for the last 7 days, and saved the markdown report.
    - Created a Notion sub-page under 'Task List > To Do's > LinkedIn: Data Insights & Analytics' and uploaded the complete report as enhanced markdown.
    - Fixed a bug in the analytics script where nested fields (`stats` and `posted_at`) from the live Apify response returned 0 metrics. Re-generated the corrected report and updated the Notion sub-page accordingly.

- **2026-07-10**: Updated personal profile README quote, and executed LinkedIn daily insights automation.
    - Ran the script `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "Complexity is the enemy of reliability. - Tony Hoare".
    - Executed the LinkedIn daily insights automation pipeline (`scripts/linkedin_insights.py`), fetching latest profile post metrics from Apify (Dataset ID: `6vEaroWyHdgw538hc`) and generating a 7-day performance report in IST.
    - Pushed/updated the Notion sub-page "LinkedIn Insights — 2026-07-10" under "Task List > To Do's > LinkedIn: Data Insights & Analytics" with the latest report.

- **2026-07-11**: Executed LinkedIn daily insights automation pipeline and updated personal profile README quote.
    - Executed the LinkedIn daily insights automation pipeline (`scripts/linkedin_insights.py`), triggering the Apify scraper to retrieve the latest profile post metrics and generating the 7-day performance report in IST.
    - Created and populated the Notion sub-page "LinkedIn Insights — 2026-07-11" under "Task List > To Do's > LinkedIn: Data Insights & Analytics" with the latest report using Notion MCP tools.
    - Ran the script `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "We must design for change. - David Parnas".

- **2026-07-12**: Executed LinkedIn daily insights automation pipeline and updated personal profile README quote.
    - Executed the LinkedIn daily insights automation pipeline (`scripts/linkedin_insights.py`), triggering the Apify scraper to retrieve the latest profile post metrics (Run ID: `p7Vy8hvwCRtBDhPFL`, Dataset ID: `FzgdAf9QQN9mRqPZe`) and generating the 7-day performance report in IST.
    - Created and populated the Notion sub-page "LinkedIn Insights — 2026-07-12" under "Task List > To Do's > LinkedIn: Data Insights & Analytics" with the latest report using Notion MCP tools.
    - Ran the script `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "Talk is cheap. Show me the code. - Linus Torvalds".
    - Ran the script `scripts/update-profile-quote.ps1` again.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "Good code is its own best documentation. - Steve McConnell".

- **2026-07-13**: Executed LinkedIn daily insights automation pipeline and updated personal profile README quote.
    - Executed the LinkedIn daily insights automation pipeline (`scripts/linkedin_insights.py`), triggering the Apify scraper to retrieve the latest profile post metrics (Run ID: `vnlUqwLzy7Y0AlHv1`, Dataset ID: `Kw8YqxF35ZeRLAf4M`) and generating the 7-day performance report in IST.
    - Created and populated the Notion sub-page "LinkedIn Insights — 2026-07-13" under "Task List > To Do's > LinkedIn: Data Insights & Analytics" with the latest report using Notion MCP tools.
    - Ran the script `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "Write code that is easy to delete. - Tef".
    - Ran the script `scripts/update-profile-quote.ps1` again.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "Copying code is a design error. - David Parnas".

- **2026-07-14**: Updated personal profile README quote.
    - Ran the script `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "Software is eating the world. - Marc Andreessen".

- **2026-07-15**: Updated personal profile README quote.
    - Ran the script `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "Don't repeat yourself. - Andy Hunt".

- **2026-07-16**: Updated personal profile README quote.
    - Ran the script `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "We must design for change. - David Parnas".

- **2026-07-18**: Updated personal profile README quote.
    - Updated the capsule-render banner in `dhyan2815/README.md` to display Andrew Ng's quote: "AI Is The New Electricity".
    - Committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.

- **2026-07-19**: Updated personal profile README quote.
    - Ran the script `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "If it hurts, do it more often. - Martin Fowler".

- **2026-07-20**: Executed 30-day LinkedIn Weekly Insights automation.
    - Created `scripts/linkedin_weekly_insights.py` to scrape 100 posts from Apify (Run ID: `77cAI8ZrwZbxYiPbl`, Dataset ID: `ZKoPa8JQ2vPk5n2QX`), parse nested metrics, and segment performance over a 30-day window into 4 weekly blocks.
    - Generated a comprehensive 30-day weekly report with format, topic, day-of-week, 4-week breakdown, and week-over-week comparison tables formatted in IST.
    - Created and populated the Notion sub-page "LinkedIn Weekly Insights — 2026-06-20 to 2026-07-20" under "Task List > To Do's > LinkedIn: Data Insights & Analytics".

- **2026-07-20**: Updated personal profile README quote.
    - Ran `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "No Silver Bullet. - Fred Brooks".


## Repository-Specific Rules
- Refer to the `README.md` for a detailed explanation of the project's purpose and structure.
- The `Changelog.md` file tracks significant setup and configuration changes.
- The `.claude/memory/` directory contains persistent context for Claude Code sessions.

## Memory System
- Claude Code maintains a persistent memory system in `.claude/memory/`:
  - **decision_log.md**: Key architectural decisions and rationale
  - **issues_tracker.md**: Bug tracking and technical debt
  - **progress.md**: Project milestones and goals
  - **session_context.md**: Context preserved across sessions

## How Gemini Should Use This File
- Scan this file on startup to understand the repository's unconventional structure and purpose.
- Use this context to inform your analysis of workflows, diagrams, and documentation.

- **2026-07-21**: Curated profile README quote list in `scripts/update-profile-quote.ps1`.
    - Removed 9 obscure/awkward quotes (Alan Perlis x2, Tef, Jack Reeves, Al Alcorn, etc.).
    - Added 6 widely-cited, iconic quotes: "The only way to go fast is to go well." (Robert C. Martin), "Premature optimization is the root of all evil." (Donald Knuth), "First, solve the problem. Then, write the code." (John Johnson), "AI is the new electricity." (Andrew Ng), "Innovation distinguishes a leader from a follower." (Steve Jobs).
    - Total quotes reduced from 29 to 25, all well-known and meaningful.

- **2026-07-21**: Updated personal profile README quote.
    - Ran `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically committed and pushed the changes to the `dhyan2815/dhyan2815` repository using Git/GitHub CLI.
    - The new quote is: "Elegance is not an optional luxury. - Bjarne Stroustrup".

- **2026-07-21**: Overhauled profile README quote list to be tech-stack aligned.
    - Completely replaced all 25 quotes in `scripts/update-profile-quote.ps1` with quotes grouped by category: AI/LLMs/Agents, Automation/Workflows, Python/Data, Full-Stack/Web/JS, Engineering Principles, and Vision/Leadership.
    - New quotes include: Andrew Ng, Alan Turing, Stephen Hawking, Karim Lakhani, Al Sweigart, Bruce Eckel, Clive Humby, W. Edwards Deming, Jeff Atwood (Atwood's Law), John Gage, Alan Kay, and more.
    - Updated personal profile README with new quote: "First, solve the problem. Then, write the code. - John Johnson".
    - Automatically committed and pushed to `dhyan2815/dhyan2815` using Git/GitHub CLI.

- **2026-07-24**: Executed GitHub profile README quote update via CLI automation script.
    - Executed `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Automatically updated the quote to: `"Data is the new oil. - Clive Humby"`.
    - Committed (`86fdabc`) and pushed changes to `dhyan2815/dhyan2815` remote repository via Git/GitHub CLI.
    - Verified repository status using `gh repo view dhyan2815/dhyan2815`.

- **2026-07-26**: Added dynamic font size scaling to `scripts/update-profile-quote.ps1`.
    - Implemented length-based font scaling (ranging from `fontSize=42` down to `fontSize=17`) to prevent long quotes from overflowing or clipping on the GitHub profile banner.
    - Updated regex in `update-profile-quote.ps1` to replace `fontSize` in the capsule-render URL along with `text` and `desc`.
    - Executed script (`32db67b`), updated README banner quote to `"Make it work, make it right, make it fast. - Kent Beck"` with calculated `fontSize=23`, and pushed changes to GitHub.
- **2026-07-28**: Onboarding & daily task automation with Notion and Python labs.
    - Used Notion MCP to fetch "LinearLoop" and parsed today's task database.
    - Created a comprehensive Python practice laboratory `notebooks/numpy_pandas_practice.py` covering NumPy creation, modification, math, stats, filtering, and Pandas equivalents.
    - Checked off tasks on the Notion Pandas & NumPy learning page.
    - Added a template Hugging Face transformers check script at `playground/huggingface_demo.py`.
- **2026-07-28**: Executed GitHub profile README quote update via CLI automation script.
    - Executed `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Selected quote: `"Premature optimization is the root of all evil. - Donald Knuth"` with fitted `fontSize=20`.
    - Committed (`63b2214`) and pushed changes to remote `dhyan2815/dhyan2815` repository using Git/GitHub CLI credentials.
    - Verified live repository view using `gh repo view dhyan2815/dhyan2815`.
- **2026-07-30**: Playwright task exploration & sub-task blueprint rendering in Notion.
    - Located today's task "W1: To Do - Explore Playwright" (ID `3ac097dd-d30d-8058-a931-c009c2e85f69`) under the LinearLoop Task List database via Notion MCP.
    - Designed and rendered a complete Sub-Task Execution Blueprint for scraping hospitals in Ahmedabad and Surat using Playwright Python/Chromium.
    - Added sections covering city zone targeting, inputs/outputs schema, architectural approaches (DOM scroll vs Network interception), anti-blocking strategies, deduplication pipelines, and an executable async Playwright script.
- **2026-08-01**: Executed GitHub profile README quote update via CLI automation script.
    - Executed `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Selected quote: `"The best code is no code at all. - Jeff Atwood"` with fitted `fontSize=28`.
    - Committed (`a8ff5c3`) and pushed changes to remote `dhyan2815/dhyan2815` repository using Git/GitHub CLI credentials.
- **2026-08-03**: Executed GitHub profile README quote update via CLI automation script.
    - Executed `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Selected quote: `"Making some sort of digital superintelligence seems like it could be dangerous. - Elon Musk"` with fitted `fontSize=17`.
    - Committed (`118b477`) and pushed changes to remote `dhyan2815/dhyan2815` repository using Git/GitHub CLI credentials.
    - Verified live repository view using `gh repo view dhyan2815/dhyan2815`.
- **2026-08-05**: Executed GitHub profile README quote update via CLI automation script.
    - Executed `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Selected quote: `"Don't repeat yourself. - Andy Hunt"` with fitted `fontSize=36`.
    - Committed (`0a6b027`) and pushed changes to remote `dhyan2815/dhyan2815` repository using Git/GitHub CLI credentials.
    - Verified live repository view using `gh repo view dhyan2815/dhyan2815`.
- **2026-08-06**: Executed GitHub profile README quote update via CLI automation script.
    - Executed `scripts/update-profile-quote.ps1` to update the quote on the capsule-render banner in `dhyan2815/README.md`.
    - Selected quote: `"Automate the boring stuff. - Al Sweigart"` with fitted `fontSize=32`.
    - Committed (`f4ac968`) and pushed changes to remote `dhyan2815/dhyan2815` repository using Git/GitHub CLI credentials.
    - Verified live repository view using `gh repo view dhyan2815/dhyan2815`.
- **2026-08-14**: Completely removed the `dhyan2815` sub-repository from the codebase.
