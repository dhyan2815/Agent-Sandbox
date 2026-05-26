import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "../../");

const server = new Server(
  {
    name: "custom-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "get_timestamp",
        description: "Returns the current timestamp in ISO format.",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      },
      {
        name: "echo",
        description: "Echoes back the provided message.",
        inputSchema: {
          type: "object",
          properties: {
            message: {
              type: "string",
              description: "The message to echo back",
            },
          },
          required: ["message"],
        },
      },
      {
        name: "add_memory_entry",
        description: "Appends a new entry to a specified memory file.",
        inputSchema: {
          type: "object",
          properties: {
            file_target: {
              type: "string",
              description: "Path representing the target file relative to repository root (e.g., GEMINI.md, .claude/memory/decision_log.md).",
            },
            content: {
              type: "string",
              description: "The actual memory or changelog text.",
            },
            date: {
              type: "string",
              description: "Optional ISO date string. Defaults to current date.",
            },
          },
          required: ["file_target", "content"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "get_timestamp") {
    return {
      content: [
        {
          type: "text",
          text: new Date().toISOString(),
        },
      ],
    };
  }

  if (request.params.name === "echo") {
    const message = request.params.arguments?.message;
    return {
      content: [
        {
          type: "text",
          text: `Echo: ${message}`,
        },
      ],
    };
  }

  if (request.params.name === "add_memory_entry") {
    const args = request.params.arguments;
    const fileTarget = args.file_target;
    const content = args.content;
    const date = args.date || new Date().toISOString().split("T")[0];
    
    try {
      const targetPath = path.resolve(REPO_ROOT, fileTarget);
      
      // Basic security check to ensure we don't write outside the repo root
      if (!targetPath.startsWith(REPO_ROOT)) {
        throw new Error("Cannot write outside repository root");
      }
      
      const entryText = `\n- **${date}**: ${content}\n`;
      await fs.appendFile(targetPath, entryText, "utf-8");
      
      return {
        content: [
          {
            type: "text",
            text: `Successfully appended memory entry to ${fileTarget}.`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Failed to append memory entry: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }

  throw new Error(`Unknown tool: ${request.params.name}`);
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Custom MCP server running on stdio");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
