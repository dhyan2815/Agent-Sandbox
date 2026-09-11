# Skills System

The Agent Sandbox features a comprehensive skills system with 57 specialized AI instruction modules organized into 5 core categories. Skills are stored in `.claude/skills/` (52 skills) and `.agents/skills/` (5 Higgsfield AI skills) directories and can be invoked via `/skill-name` or through agent CLI tools.

Each skill contains specialized workflows, prompts, and references for specific tasks, enabling rapid prototyping and consistent output quality across different domains.

## Skill Categories

### 1. Content Creation (15 skills)

Skills focused on generating various types of content for social media, marketing, and professional communication.

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

### 2. LinkedIn Tools (9 skills)

Skills specifically designed for LinkedIn optimization, engagement, and automation.

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

### 3. Developer Tools (16 skills)

Technical skills for development workflows, automation, and code manipulation.

| Skill | Function |
|-------|----------|
| `visual-explainer` | HTML diagrams, slides, diff/plan reviews, data tables |
| `skills-mcp-builder` | Build MCP servers ([reference](https://modelcontextprotocol.io/)) |
| `read-codebase` | Analyze repository structure and dependencies |
| `issue-workflow` | GitHub issue management automation |
| `pr-comment` | Automated pull request comments |
| `creating-pr` | Pull request creation workflow |
| `apify-actor-development` | Apify actor development and deployment |
| `apify-content-analysis` | Content analysis and performance tracking |
| `apify-lead-generation` | Lead generation through automated scraping |
| `apify-market-research` | Automated market research and competitor analysis |
| `apify-trend-analysis` | Trend analysis using web scraping |
| `use-tinyfish` | TinyFish integration for data processing |
| `pdf-reading` | PDF text extraction and analysis |
| `pdf/` | PDF manipulation and generation tools |
| `pptx/` | PowerPoint presentation generation |
| `excalidraw-diagram-generator` | Automated Excalidraw diagram creation |
| `design-doc-mermaid` | Mermaid diagram generation for technical documentation |
| `web-design-reviewer` | Website design review and feedback |
| `website-to-hyperframes` | Convert websites to hyperframe presentations |

### 4. Productivity (9 skills)

Skills for task management, communication, and workflow optimization.

| Skill | Function |
|-------|----------|
| `meeting-summarizer` | Summarize meeting notes and action items |
| `email-writer` | Professional email generation and templates |
| `task-decomposer` | Break down complex tasks into manageable steps |
| `gh-issues` | GitHub issue tracking and management |
| `gog` | Game of Goals productivity system |
| `readme-generator` | Automated README generation for projects |
| `project-idea-validator` | Validate project ideas and feasibility |
| `skills-md-to-pdf-converter` | Convert skills documentation to PDF format |
| `ui-design-system` | Create and manage UI design systems |

### 5. Research (8 skills)

Skills for information gathering, analysis, and synthesis.

| Skill | Function |
|-------|----------|
| `deep-search` | Multi-source research synthesis and analysis |
| `research-synthesizer` | Academic paper analysis and literature review |
| `trend-spotter` | Identify emerging trends and patterns |
| `apify-market-research` | Automated market research and competitor analysis |
| `apify-trend-analysis` | Trend analysis using web scraping |
| `apify-lead-generation` | Lead generation through automated scraping |
| `apify-content-analysis` | Content analysis and performance tracking |
| `analytics-dashboard` | Interactive performance metrics dashboard |
| `media-type-suggestor` | Suggest optimal content formats for platforms |
| `niche-research` | Research trending topics in specific niches |

## Skill Storage Structure

```
.claude/skills/
├── content-creation/          # Content writing, graphics, social media
├── linkedin-tools/            # LinkedIn optimization and automation
├── developer-tools/           # Coding, automation, technical workflows
├── productivity/              # Task management, communication, workflows
└── research/                  # Information gathering and analysis

.agents/skills/
├── higgsfield-image/          # AI image generation
├── higgsfield-video/          # AI video generation
├── higgsfield-3d/             # AI 3D model generation
├── higgsfield-audio/          # AI audio generation
└── higgsfield-fullstack/      # Full-stack web generation
```

## Using Skills

Skills are invoked through agent CLI tools using the format:
```
/skill-name [parameters]
```

For example:
- `/linkedin-post-writer "topic: AI trends"`
- `/gemini-carousel "topic: MCP servers"`
- `/visual-explainer "architecture diagram of MCP server"`
- `/read-codebase "path: .claude/skills/"`

Many skills require additional configuration files:
- `voice.md` - Personal voice profile for content writing skills
- `.env` - API keys and tokens for external services
- `designs/DESIGN.md` - Brand guidelines for visual skills

## Skill Dependencies

Some skills depend on others or require specific files:
- `post-writer` requires `voice.md` for authentic voice generation
- Graphic design skills may reference `brand-kit.md` for styling
- LinkedIn skills work best with populated `linkedin-data/` directory
- MCP-related skills reference the `mcp/` directory for implementations

## Related Documentation

- [Content Creation](content.md) - Detailed workflows for content generation
- [Developer Tools](developer-tools.md) - Technical skills for development
- [CLAUDE.md](../CLAUDE.md) - Claude Code guidance on skills usage
- [AGENTS.md](../AGENTS.md) - Codex guidance on skills usage
- [skills-lock.json](../skills-lock.json) - Skills inventory and metadata