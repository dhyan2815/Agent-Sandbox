# Architecture

## MCP Server Architecture

The MCP server is the core component that enables agent-based workflows by providing a standardized interface for tools and external services. This section documents the architecture and operation of the custom MCP server implementation.

### High-Level Architecture

The MCP server follows a modular design with distinct layers:

- **Clients**: AI CLI tools (Claude Code, Gemini CLI) that send tool requests
- **Transport Layer**: Handles JSON-RPC communication over stdio
- **Core Layer**: Manages request dispatch, validation, error handling, and logging
- **Tools Layer**: Contains 5 registered tools with specific capabilities
- **Storage Layer**: Manages repository file system access with security protections

![MCP Server Architecture](docs/architecture/mcp-server-architecture.md)

### Component Breakdown

#### Transport Layer
- **StdioServerTransport**: Bridges stdin/stdout to JSON-RPC message protocol
- Handles raw I/O operations and message framing

#### Core Layer
- **Request Dispatcher**: Routes `CallToolRequest` to appropriate tool handlers
- **Input Validation**: Prevents path traversal and enforces input constraints
- **Error Handler**: Centralized exception handling with structured `isError` responses
- **Structured Logger**: Emits JSON log entries with timestamps and operation durations

#### Tools (5 registered)
1. **mcp_echo** - Read-only echo functionality
2. **mcp_get_timestamp** - Returns current timestamp
3. **mcp_add_memory_entry** - Writes entries to memory files (GEMINI.md, CLAUDE.md)
4. **mcp_repo_list_files** - Lists repository files and directories
5. **mcp_repo_search_content** - Searches content across repository files

#### Storage Layer
- **Repository File System**: Path-traversal protected access to repo files
- **Memory Files**: Special files for persistent memory (GEMINI.md, CLAUDE.md)
- **Content Files**: Repository documentation and skill files

### Key Design Patterns

- **Subgraphs** in Mermaid diagrams for logical component grouping
- **Color-coded classDef** for visual hierarchy without separate legends
- **Unicode symbols** for immediate component identification
- **Autonumbered sequences** for step-by-step documentation reference

### Tool Interaction Examples

#### Happy Path Flow
1. Client sends `CallToolRequest` for `mcp_repo_search_content`
2. Dispatcher validates arguments and routes to tool
3. Tool executes file system operations with proper validation
4. Results are processed and returned through the dispatcher
5. Structured logging occurs at each stage

#### Error Handling
- Unknown tool requests return graceful error responses
- Path traversal attempts are blocked with clear error messages
- All errors are caught and converted to structured responses

## Experimental Diagrams

The repository includes experimental Mermaid diagrams documenting tool interactions:

- **Architecture Diagram**: High-level component layout with color coding
- **Sequence Diagrams**: Detailed step-by-step interaction flows for:
  - Successful tool calls
  - Unknown tool error handling
  - Input validation failures
  - Memory entry operations

These diagrams use:
- `autonumber` for step tracking
- Unicode symbols for visual clarity
- Subgraphs for logical grouping
- Class definitions for color coding