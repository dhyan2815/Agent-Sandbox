# Codex CLI Tools Reference

> OpenAI's command-line coding agent for code execution and agentic workflows.

## Installation

```bash
npm install -g @openai/codex
```

## Commands

| Command | Description |
|---------|-------------|
| `codex` | Start interactive session |
| `codex exec` | Run Codex non-interactively |
| `codex review` | Run code review |
| `codex login` | Authenticate (device auth) |
| `codex logout` | Remove credentials |
| `codex mcp` | Manage MCP servers |
| `codex doctor` | Diagnose installation |

## Authentication

- Requires **Codex subscription** (not free ChatGPT)
- Device auth flow: `codex login --device-auth`
- Uses ChatGPT or API key authentication

## Available Models

- `gpt-5.3-codex` (default, requires paid subscription)
- `gpt-4o` (requires paid subscription)
- `--oss` flag for local providers (Ollama, LM Studio)

## Configuration

Config file: `~/.codex/config.toml`

```toml
model = "gpt-5.3-codex"
```

## Use Cases

1. Code completion and generation
2. Code review and refactoring
3. Agentic multi-step tasks
4. Bug detection and fixes
5. Documentation generation

## Comparison with Claude Code

| Feature | Codex | Claude Code |
|---------|-------|-------------|
| Provider | OpenAI | Anthropic |
| Model | GPT-5.3 | Claude 4 |
| Free tier | No | Yes (limited) |
| MCP Support | Yes | Yes |
| Interactive | Yes | Yes |