# Experiments

This directory contains documentation of various experiments conducted as part of the 30-Day AI CLI Experimentation Plan and other exploratory work.

## Mermaid Diagram Generation (Day 17)
Documented in: [`docs/experiments/mermaid-diagram-generation.md`](docs/experiments/mermaid-diagram-generation.md)

**Objective**: Use the `design-doc-mermaid` skill to create technical Mermaid diagrams for the custom MCP server.

**Key Learnings**:
- Subgraphs are essential for grouping related components in architecture diagrams
- `autonumber` in sequence diagrams makes it easy to reference specific steps
- Unicode symbols significantly improve diagram readability at a glance
- `classDef` color coding creates instant visual hierarchy without requiring a separate legend
- The resilient workflow pattern (validate before embedding) prevents broken diagrams in documentation

**Deliverables**:
1. Architecture Diagram (`docs/architecture/mcp-server-architecture.md`)
2. Sequence Diagrams (`docs/architecture/mcp-server-sequences.md`)

## Excalidraw Diagram Generation
Documented in: [`docs/experiments/excalidraw-diagram-generation.md`](docs/experiments/excalidraw-diagram-generation.md)

**Objective**: Experiment with Excalidraw for creating architecture and workflow diagrams.

**Key Learnings**:
- Excalidraw enables rapid creation of expressive, hand-drawn style diagrams
- Cross-tool workflow diagrams help visualize interactions between different AI CLI tools
- Architecture diagrams benefit from Excalidraw's free-form drawing capabilities

**Deliverables**:
- Cross-tool workflow diagram (`visuals/cross-tool-workflow.excalidraw`)
- MCP server architecture diagram (`visuals/mcp-server-architecture.excalidraw`)

## Other Experiments
Additional experiments documented in the `/docs/experiments/` directory include:
- Claude Code workflow scanning
- Codex agentic workflow exploration
- Gemini CLI setup and experimentation
- MCP exploration
- Graphic designer SVG enhancement
- Graphic designer SVG enhancement

Each experiment documents objectives, methodologies, key learnings, and deliverables related to exploring various AI CLI tools and automation techniques.

## Related Visuals
Corresponding visual diagrams for experiments are stored in the `/visuals/` directory:
- [`visuals/cross-tool-workflow.excalidraw`](visuals/cross-tool-workflow.excalidraw)
- [`visuals/mcp-server-architecture.excalidraw`](visuals/mcp-server-architecture.excalidraw)