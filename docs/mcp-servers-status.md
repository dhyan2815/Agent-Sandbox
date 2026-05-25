# MCP Servers Status

> **Last Updated:** 2026-05-18
> **Purpose:** Track connected MCP servers and their capabilities

---

## Connected MCP Servers

### hf-mcp-server (HuggingFace MCP)

**Status:** Active

**Configuration:**
```json
{
  "type": "http",
  "url": "https://huggingface.co/mcp?login"
}
```

**Authentication:** Authenticated as `dhyann2815`

**Available Tools:**

| Tool | Purpose |
|------|---------|
| `hub_repo_search` | Search HuggingFace Hub (models, datasets, spaces) |
| `hub_repo_details` | Get details for specific repos |
| `gr1_z_image_turbo_generate` | Generate images using Z-Image model |
| `hf_doc_search` | Search HuggingFace/Gradio documentation |
| `hf_doc_fetch` | Fetch specific documentation pages |
| `paper_search` | Find ML research papers on HuggingFace Hub |
| `dynamic_space` | Perform tasks with HuggingFace Spaces |
| `space_search` | Search for Spaces (semantic) |
| `hf_hub_query` | Hub navigator for discovery and lookups |
| `hf_whoami` | Get current authenticated user info |

**Test Results:** Passed (Day 2 - 2026-05-17)
- Successfully queried model repository
- Image generation tested with `gr1_z_image_turbo_generate`

---

## Not Configured

The following MCP servers are NOT currently configured but may be useful:

| Server | Purpose | Setup Required |
|--------|---------|----------------|
| Notion MCP | Page/database operations | API token |
| GitHub MCP | PR automation, issue management | Personal access token |
| Filesystem MCP | Local file operations | Built-in or custom |
| Slack MCP | Messaging integration | API token |

---

## Planned MCP Additions

1. **Notion MCP** - For content publishing workflow
2. **GitHub MCP** - For PR automation and issue tracking

---

## References

- Config: `.mcp.json`
- Day 2 Exploration: `docs/experiments/mcp-exploration-2026-05-17.md`
