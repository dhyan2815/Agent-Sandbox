# Custom MCP Server — Tool Interaction Sequences

> Generated using the `design-doc-mermaid` skill on Day 17 of the 30-Day AI CLI Experimentation Plan.

## Sequence 1: Successful Tool Call (`mcp_repo_search_content`)

This diagram traces a complete successful request from the AI CLI client through transport, dispatcher, validation, tool execution, and structured logging.

```mermaid
sequenceDiagram
    autonumber

    participant Client as 👤 AI CLI Client
    participant Transport as 📡 StdioTransport
    participant Dispatcher as 🔄 Dispatcher
    participant Logger as 📝 Logger (stderr)
    participant Validator as 🛡️ Validator
    participant Tool as 🔍 mcp_repo_search_content
    participant FS as 💾 Repository FS

    Client->>Transport: CallToolRequest (JSON-RPC)
    Transport->>Dispatcher: { name: "mcp_repo_search_content", args }
    Dispatcher->>Logger: INFO "Tool called: mcp_repo_search_content"
    Dispatcher->>Validator: validateString(query), resolveSafePath(directory)
    Validator-->>Dispatcher: ✅ Validated args

    Dispatcher->>Tool: handleRepoSearchContent(args)
    Tool->>FS: fs.stat(resolvedDir)
    FS-->>Tool: { isDirectory: true }
    Tool->>FS: fs.readdir(dir, { withFileTypes })
    FS-->>Tool: [file entries]

    loop For each text file (≤ max_results)
        Tool->>FS: fs.readFile(filePath, "utf-8")
        FS-->>Tool: file content
        Tool->>Tool: line-by-line search for query
    end

    Tool-->>Dispatcher: { content: [{ type: "text", text: JSON }] }
    Dispatcher->>Logger: INFO "Tool completed" { duration_ms }
    Dispatcher-->>Transport: JSON-RPC response
    Transport-->>Client: Result with matches
```

## Sequence 2: Error Handling — Unknown Tool

This diagram shows how the server gracefully handles a request for a non-existent tool without crashing.

```mermaid
sequenceDiagram
    autonumber

    participant Client as 👤 AI CLI Client
    participant Transport as 📡 StdioTransport
    participant Dispatcher as 🔄 Dispatcher
    participant Logger as 📝 Logger (stderr)
    participant ToolMap as 📦 Tool Registry

    Client->>Transport: CallToolRequest { name: "nonexistent_tool" }
    Transport->>Dispatcher: { name: "nonexistent_tool", args: {} }
    Dispatcher->>Logger: INFO "Tool called: nonexistent_tool"
    Dispatcher->>ToolMap: toolMap.get("nonexistent_tool")
    ToolMap-->>Dispatcher: undefined

    Dispatcher->>Logger: WARN "Unknown tool requested: nonexistent_tool"
    Dispatcher-->>Transport: { isError: true, content: "Unknown tool..." }
    Transport-->>Client: Error response (no crash)
```

## Sequence 3: Error Handling — Input Validation Failure

This diagram shows the path traversal prevention in action when a malicious file path is provided.

```mermaid
sequenceDiagram
    autonumber

    participant Client as 👤 AI CLI Client
    participant Transport as 📡 StdioTransport
    participant Dispatcher as 🔄 Dispatcher
    participant Logger as 📝 Logger (stderr)
    participant Validator as 🛡️ Validator
    participant Tool as ✏️ mcp_add_memory_entry

    Client->>Transport: CallToolRequest { name: "mcp_add_memory_entry" }
    Note right of Client: file_target: "../../etc/passwd"
    Transport->>Dispatcher: { name, args }
    Dispatcher->>Logger: INFO "Tool called"
    Dispatcher->>Tool: handleAddMemoryEntry(args)
    Tool->>Validator: resolveSafePath("../../etc/passwd")
    Validator->>Validator: path.resolve(REPO_ROOT, target)
    Validator->>Validator: resolved.startsWith(REPO_ROOT)?

    Validator-->>Tool: ❌ Error("Path traversal detected")
    Tool-->>Dispatcher: throw Error
    Dispatcher->>Logger: ERROR "Tool failed" { error, duration_ms }
    Dispatcher-->>Transport: { isError: true, content: "Path traversal..." }
    Transport-->>Client: Error response (file system protected)
```

## Sequence 4: Memory Entry Write Flow

This diagram shows the complete flow of `mcp_add_memory_entry` appending content to a memory file.

```mermaid
sequenceDiagram
    autonumber

    participant Client as 👤 AI CLI Client
    participant Transport as 📡 StdioTransport
    participant Dispatcher as 🔄 Dispatcher
    participant Validator as 🛡️ Validator
    participant Tool as ✏️ mcp_add_memory_entry
    participant FS as 💾 Repository FS
    participant Logger as 📝 Logger (stderr)

    Client->>Transport: CallToolRequest
    Note right of Client: file_target: "GEMINI.md"<br/>content: "Day 17 completed"
    Transport->>Dispatcher: { name, args }
    Dispatcher->>Validator: validateString(file_target), validateString(content)
    Validator-->>Dispatcher: ✅ Valid
    Dispatcher->>Tool: handleAddMemoryEntry(args)
    Tool->>Validator: resolveSafePath("GEMINI.md")
    Validator-->>Tool: ✅ /repo/root/GEMINI.md

    Tool->>FS: fs.appendFile(targetPath, entryText)
    FS-->>Tool: ✅ Written
    Tool->>Logger: INFO "Memory entry appended" { file }
    Tool-->>Dispatcher: { content: "Successfully appended..." }
    Dispatcher->>Logger: INFO "Tool completed" { duration_ms }
    Dispatcher-->>Transport: JSON-RPC response
    Transport-->>Client: Success confirmation
```
