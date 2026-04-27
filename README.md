# Agent Sandbox

Welcome to my experimental sandbox for CLI-based tools, AI agents, and workflow automations. This repository is dedicated to exploring the capabilities and scaling possibilities of various command-line interfaces and their associated "skills" or "mcp" integrations.

## Core Focus

This repository explores the intersection of AI and command-line interfaces. Key areas of experimentation include:

- **Claude Code:** Harnessing agentic AI for automated code generation, refactoring, and complex problem-solving directly within the terminal.
- **Gemini CLI:** Automating complex workflows and data processing tasks by scripting interactions with Google's Gemini models.
- **n8n Workflows:** Building and documenting robust, event-driven automations to connect APIs and services with minimal code.
- **Excalidraw Diagrams:** Creating clear, maintainable diagrams of system architecture, workflows, and infrastructure for planning and documentation.
- **Open Code:** Exploring the potential of open-source, CLI-driven development tools.
- **DESIGN.md System:** Brand design documentation for consistent UI generation across projects.

## Goals

The primary goal of this repository is to serve as a personal knowledge base and a testbed for cutting-edge CLI and AI-driven development techniques. Key objectives include:

- **Mastery:** Deepen expertise in using agentic CLI tools.
- **Automation:** Document scalable patterns for automating repetitive software development tasks.
- **Integration:** Explore seamless integrations between different AI services and development tools.
- **Visualization:** Develop clear and effective methods for documenting complex systems.
- **Design Consistency:** Create reusable brand design documentation that AI agents can reference.
- **Memory:** Enable persistent context across sessions via Claude Code memory system.
- **Standards:** Enforce consistent code quality through documented conventions.

## Skills

This repository includes specialized AI agent skills for various tasks. Each skill is designed to be invoked through the Claude Code Skill system.

| Skill | Description | Use Case Example |
|-------|-------------|-----------------|
| **analytics-dashboard** | Turn a LinkedIn Analytics export into an interactive dark-themed React dashboard plus a written strategic analysis with 5 data-backed content recommendations. | Analyzing LinkedIn performance data to create visual dashboards and actionable content strategies. |
| **content-matrix** | Generate 32+ LinkedIn post ideas in a single table by pairing the user's content pillars with 8 proven content formats. | Creating a month's worth of content ideas based on personal expertise and proven content frameworks. |
| **design-doc-mermaid** | Create Mermaid diagrams (activity, deployment, sequence, architecture) from text descriptions or source code. | Documenting system architecture, API workflows, or business processes using Mermaid syntax. |
| **excalidraw-diagram-generator** | Generate Excalidraw diagrams from natural language descriptions. Supports flowcharts, relationship diagrams, mind maps, and system architecture diagrams. | Creating visual explanations of complex systems, processes, or concepts that can be edited in Excalidraw. |
| **gemini-carousel** | Generate a branded slide-by-slide LinkedIn carousel using Gemini. Takes source content, builds a design brief, waits for approval, then outputs per-slide image generation prompts. | Turning a blog post or article into an engaging LinkedIn carousel with consistent branding. |
| **gemini-infographic** | Generate the hand-drawn whiteboard infographic prompt that pulled 480k impressions across 3 posts. Takes source content and returns a complete Gemini image generation prompt. | Creating educational or informative visuals that perform well on LinkedIn by mimicking successful whiteboard-style content. |
| **graphic-designer** | Create LinkedIn post graphics. Decides between an HTML/CSS structured graphic or an AI-generated infographic based on the post content. | Producing professional visuals to accompany LinkedIn posts, choosing the best format for the content type. |
| **hook-generator** | Generate 6 clickbait-style LinkedIn hook variations for any topic. Two-line hooks built on the formula: a 40-char opening line, a 40-char bold contrast line. | Crafting attention-grabbing openings for LinkedIn posts to increase engagement and reach. |
| **linkedin-comment-generator** | Generate authentic, non-generic LinkedIn comments that spark real micro-conversations. | Engaging meaningfully with others' LinkedIn posts to build relationships and visibility. |
| **linkedin-profile-optimizer** | Audits and rewrites LinkedIn profiles using a structured strategist framework to maximize visibility, credibility, and conversions. | Improving a LinkedIn profile to attract recruiters, clients, or followers through strategic content optimization. |
| **newsletter-voice** | Build newsletter writing instructions inside a Cowork project. Runs after voice-builder. Produces newsletter-voice.md, a single file Claude references when drafting newsletters in the user's voice. | Creating a consistent voice and style guide for newsletter writing that matches the author's personality and expertise. |
| **niche-research** | Surface the 20 most relevant stories in a niche from the last 7 days using Claude for Chrome. Verified dates, real links, shareable angles. | Finding trending topics and news in a specific industry to inform content creation and stay current. |
| **pinned-comment** | Write LinkedIn pinned comments AND image generation prompts in Charlie Hills' signature style. Use when Charlie or his team asks for a pinned comment, pin comment, or first comment for a LinkedIn post. | Creating memorable first comments on LinkedIn posts that increase engagement through humor and personality. |
| **post-formatter** | Turn a topic into a ready-to-publish LinkedIn post using PAS, AIDA, BAB, STAR, or SLAY frameworks. 200 to 250 words, 20 lines max, mobile-formatted with blank lines between sentences. | Structuring LinkedIn content using proven copywriting frameworks for maximum impact and readability. |
| **post-scorer** | Score a LinkedIn post using real performance data. Pulls the user's own post history via Apify (or uses cached data) to identify what actually performs, then scores the draft against those patterns. | Getting data-driven feedback on LinkedIn content before publishing to improve engagement and reach. |
| **post-writer** | Write LinkedIn posts that match the user's voice system (about-me.md and voice.md). Use this skill whenever the user says "write a post", "draft a post", "LinkedIn post", "post about [topic]", "content idea", or wants help writing any LinkedIn content. | Creating LinkedIn content that authentically represents the user's voice and expertise. |
| **profile-optimizer** | Rebuild a LinkedIn profile for maximum conversions. Produces new headline options, about section, experience section, featured section strategy, and 4 image generation prompts (banner, profile picture, 2 featured tiles). | Completely redesigning a LinkedIn presence to align with business goals and target audience. |
| **quote-post** | Two-step workflow for creating quote posts on LinkedIn. Claude generates viral motivational quotes to accompany a caption, then produces a Gemini prompt that recreates a reference image with the chosen quote baked in. | Creating visually appealing quote graphics for LinkedIn that combine inspirational text with compelling imagery. |
| **skills-mcp-builder** | Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK). | Building custom integrations between AI assistants and external services like GitHub, Slack, or databases. |
| **skills-md-to-pdf-converter** | Converts Markdown (.md) files into professional, high-fidelity PDF reports. Preserves tables, bold/italic text, headers (H1–H4), bullet lists, code blocks, and horizontal rules. | Transforming technical documentation or reports from Markdown to polished PDF format for sharing or printing. |
| **voice-builder** | Build a personalised voice profile inside a Cowork project from a short interview plus 3 to 5 sample pieces of writing. Works for any content format: LinkedIn posts, newsletters, essays, emails, blog posts, tweets, or any other published writing. | Creating a foundation for AI-assisted writing that matches the user's unique communication style and expertise. |
| **web-design-reviewer** | This skill enables visual inspection of websites running locally or remotely to identify and fix design issues. Triggers on requests like "review website design", "check the UI", "fix the layout", "find design problems". Detects issues with responsive design, accessibility, visual consistency, and layout breakage, then performs fixes at the source code level. | Improving the user experience and visual appeal of websites by identifying and correcting design flaws. |
| **writing-linkedin-posts** | Create engaging, authentic LinkedIn posts like a Top Voice. Use this skill when asked to write LinkedIn content, social media posts for LinkedIn, professional thought leadership content, or help with LinkedIn engagement strategy. Triggers include requests for LinkedIn posts, professional social content, thought leadership pieces, or viral/engaging LinkedIn content. | Crafting LinkedIn content that builds authority, engages the target audience, and achieves specific communication goals. |
| **youtube-thumbnail** | Generate YouTube thumbnail concepts optimized for click-through rate and visual appeal. | Creating compelling visual representations of YouTube video content to increase views and engagement. |

### Invoking Skills

To use a skill, invoke it through Claude Code's Skill tool:

```
/skill-name  (using slash command)
```

Or use the Skill tool directly with the skill name.

This enables long-term memory of project decisions and user preferences.

## Documentation System

The `.claude/docs/` directory contains Claude-specific documentation:
- **ARCHITECTURE.md**: System design and component relationships
- **GLOSSARY.md**: Terminology definitions
- **QUICK_START.md**: Getting started guide for new contexts

## Coding Standards

Project-wide standards in `.claude/rules/`:
- **coding_standards.md**: Universal principles + language-specific guides (Python, JS/TS, Go, Java, C)
- **naming_conventions.md**: File, class, function, variable, database, and API naming patterns

## Design System

Inspired by [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md), this repository uses the DESIGN.md concept. Each brand/project gets its own `DESIGN.md` file containing:

- Visual theme and atmosphere
- Color palette with semantic roles
- Typography rules and hierarchy
- Component styles and specifications
- Layout principles
- Depth and elevation guidelines
- Do's and don'ts
- Responsive behavior
- Agent prompt references

These files serve as a single source of truth for AI agents to generate brand-consistent UI.

## Experimental Nature

Everything in this repository is highly experimental. I use this space to push the boundaries of what CLI tools can do in a modern software engineering environment.

---

*Created and maintained by [dhyan2815](https://github.com/dhyan2815).*