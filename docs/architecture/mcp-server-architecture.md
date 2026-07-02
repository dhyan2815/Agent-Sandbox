# Custom MCP Server — Architecture Overview

> Generated using the `design-doc-mermaid` skill on Day 17 of the 30-Day AI CLI Experimentation Plan.

## System Architecture

This diagram shows the high-level component layout of the custom MCP server (`mcp/custom-server/`), including transport, core dispatcher, tool registry, and external dependencies.

```mermaid
graph TB
    subgraph Clients["👤 AI CLI Clients"]
        CC["⚙️ Claude Code"]
        GC["⚙️ Gemini CLI"]
    end

    subgraph Transport["🔌 Transport Layer"]
        STDIO["📡 StdioServerTransport\n(stdin/stdout JSON-RPC)"]
    end

    subgraph Core["🏗️ MCP Server Core (v2.0.0)"]
        Dispatcher["🔄 Request Dispatcher\n(CallToolRequestSchema)"]
        Validator["🛡️ Input Validation\n(validateString / resolveSafePath)"]
        ErrorHandler["❌ Centralized Error Handler\n(try/catch with isError response)"]
        Logger["📝 Structured Logger\n(JSON to stderr)"]
    end

    subgraph Tools["📦 Registered Tools (5)"]
        direction LR
        T1["mcp_echo\n🔒 read-only"]
        T2["mcp_get_timestamp\n🔒 read-only"]
        T3["mcp_add_memory_entry\n✏️ write"]
        T4["mcp_repo_list_files\n🔒 read-only"]
        T5["mcp_repo_search_content\n🔒 read-only"]
    end

    subgraph Storage["💾 Repository File System"]
        FS["📂 REPO_ROOT\n(path-traversal protected)"]
        Memory["📄 GEMINI.md / CLAUDE.md\n(memory files)"]
        Docs["📁 docs/ / skills/ / visuals/\n(content files)"]
    end

    CC -->|"JSON-RPC"| STDIO
    GC -->|"JSON-RPC"| STDIO
    STDIO --> Dispatcher
    Dispatcher --> Validator
    Validator --> T1 & T2 & T3 & T4 & T5
    Dispatcher --> ErrorHandler
    Dispatcher --> Logger
    T3 -->|"appendFile"| Memory
    T4 -->|"readdir"| FS
    T5 -->|"readFile + search"| Docs

    classDef client fill:#ffd43b,stroke:#333,stroke-width:2px,color:black
    classDef transport fill:#a5d8ff,stroke:#333,stroke-width:2px,color:darkblue
    classDef core fill:#b2f2bb,stroke:#333,stroke-width:2px,color:darkgreen
    classDef tool fill:#d0bfff,stroke:#333,stroke-width:2px,color:#4a0080
    classDef storage fill:#fff3bf,stroke:#333,stroke-width:2px,color:#664d00

    class CC,GC client
    class STDIO transport
    class Dispatcher,Validator,ErrorHandler,Logger core
    class T1,T2,T3,T4,T5 tool
    class FS,Memory,Docs storage
```

## Component Responsibilities

| Component | Responsibility |
|---|---|
| **StdioServerTransport** | Bridges stdin/stdout to JSON-RPC message protocol |
| **Request Dispatcher** | Routes `CallToolRequest` to the correct tool handler by name |
| **Input Validation** | Type checks, length limits, path traversal prevention |
| **Error Handler** | Catches all tool exceptions, returns structured `isError` responses |
| **Structured Logger** | Emits JSON log entries to stderr with timestamps and durations |
| **Tool Registry** | Maps of 5 tools with schemas, annotations, and handler functions |
