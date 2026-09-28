# Stage 1 — MCP Fundamentals

## What MCP is

MCP (Model Context Protocol) is a standard protocol that lets an AI assistant discover
and call functions ("tools") that live in a separate process. Instead of every AI app
inventing its own plugin format, MCP standardizes discovery and invocation so one server
can plug into any MCP-compatible client (Claude Desktop, Claude Code, Cursor, ...).

## Core concepts

| Concept | Definition | In this project |
|---|---|---|
| MCP Server | Process exposing tools/resources | `server.py` |
| MCP Client | Lives inside the AI app, speaks MCP to servers | Built into Claude Desktop |
| Tool | Named function + JSON Schema the AI can call | `hello_world`, `list_containers`, ... |
| Transport | How bytes move between client/server | stdio (local subprocess, stdin/stdout) |

Resources and prompts exist in the spec but are intentionally unused here — tools are
the only primitive needed for "run diagnostic, return structured data."

## Request lifecycle

1. Client spawns `python3 server.py` as a subprocess (config tells it how).
2. Client sends `initialize` over stdio — a handshake exchanging protocol version and capabilities.
3. Client sends `tools/list` — server responds with tool names + JSON Schemas (metadata only, no code runs).
4. The model reads those schemas as a menu and decides which tool fits the user's question.
5. Client sends `tools/call` with tool name + arguments.
6. Server runs the Python function, returns the result as a JSON-RPC response.
7. Client feeds the result back to the model, which writes the natural-language answer.

## `server.py` walkthrough

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("local-devops-assistant")

@mcp.tool()
def hello_world(name: str) -> str:
    """Say hello to someone. Used to verify the MCP connection works end to end."""
    return f"Hello, {name}! Your MCP server is alive."

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

- `FastMCP("local-devops-assistant")` — server object; the name string is what the client displays.
- `@mcp.tool()` — registers the function, auto-generates the JSON Schema from type hints,
  and uses the docstring as the tool description **the model reads to decide whether to call it**.
- `mcp.run(transport="stdio")` — starts the event loop reading JSON-RPC off stdin, writing
  responses to stdout. No networking, no port — stdio is a subprocess pipe.

## Manual protocol test (no client needed)

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python3 server.py
```

Expected: a JSON-RPC response with `serverInfo.name == "local-devops-assistant"` and
`capabilities.tools` present — confirms the handshake works before any client is involved.

## Version note

`pip install mcp` currently installs `mcp 2.x`, which renamed `FastMCP` to `MCPServer`
with a different API. This project pins `mcp<2` (see `requirements.txt`) to use the
stable, widely-documented `FastMCP` API.
