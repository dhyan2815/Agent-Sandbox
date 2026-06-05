import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "../..");
const serverPath = path.join(repoRoot, "mcp", "custom-server", "index.js");

const transport = new StdioClientTransport({
  command: "node",
  args: [serverPath],
  cwd: repoRoot,
});

const client = new Client({
  name: "day12-mcp-test",
  version: "1.0.0",
});

await client.connect(transport);

const tools = await client.listTools();
const timestamp = await client.callTool({
  name: "get_timestamp",
  arguments: {},
});
const echo = await client.callTool({
  name: "echo",
  arguments: { message: "day 12 integration check" },
});

console.log(JSON.stringify({ tools, timestamp, echo }, null, 2));

await client.close();
