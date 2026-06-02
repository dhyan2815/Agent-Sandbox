# Codex CLI Exploration

> **Date:** 2026-06-02
> **Day:** 10 of 30-Day AI CLI Experimentation Plan

## Summary

Explored Codex CLI from OpenAI. Successfully installed but requires paid subscription for model access.

## Installation

Successfully installed Codex CLI v0.136.0 via npm:

```bash
npm install -g @openai/codex
```

## Setup & Configuration

### Authentication Status
- Device auth flow available: `codex login --device-auth`
- Doctor check shows auth configured with ChatGPT tokens
- **Issue:** Model access requires Codex subscription (not free ChatGPT)

### Doctor Output
- Version: 0.136.0
- 3 MCP servers configured
- Sandbox: restricted fs + restricted network
- 26 feature flags enabled
- Working directory detected correctly

### Model Access
| Model | Status |
|-------|--------|
| gpt-5.3-codex | Requires paid subscription |
| gpt-4o | Requires paid subscription |
| Local (Ollama/LM Studio) | Available with `--oss` flag |

## Capabilities (From Documentation)

1. **Interactive Mode** - `codex` starts TUI session
2. **Non-interactive** - `codex exec` for CLI automation
3. **Code Review** - `codex review` for automated reviews
4. **MCP Integration** - Built-in MCP server management
5. **Sandbox Mode** - Read-only, workspace-write, or danger-full-access

## Key Commands

```bash
codex --version              # Check version
codex doctor                # Diagnose setup
codex exec "prompt"         # Run non-interactive
codex mcp list              # List MCP servers
codex logout                # Clear auth
codex login --device-auth    # Re-authenticate
```

## Limitations Found

1. **Paid Subscription Required** - Free ChatGPT accounts cannot use Codex models
2. **Interactive Only** - Cannot run without TTY (needs terminal for interactive mode)
3. **Local Provider Setup** - Requires separate Ollama installation

## Comparison with Claude Code

| Aspect | Codex CLI | Claude Code |
|--------|-----------|-------------|
| Provider | OpenAI | Anthropic |
| Cost | Paid | Free tier available |
| Interactive | Terminal TUI | Terminal TUI |
| MCP | Yes | Yes |
| Local models | Ollama/LM Studio | Ollama |
| Code review | Built-in | Via skills |

## Next Steps

1. Need Codex subscription for full functionality
2. Alternative: Set up local Ollama provider
3. Explore MCP server integration once authenticated
4. Test code review feature with subscription

## Files Created

- `references/codex-tools.md` - Quick reference guide