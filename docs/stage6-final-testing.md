# Stage 6 — Final Testing and Architecture

## Architecture

```
 ┌──────────┐   types a question    ┌────────────────────┐
 │   User   │ ─────────────────────▶│   AI Assistant       │
 └──────────┘                       │  (Claude, in an      │
      ▲                             │   MCP-aware client)  │
      │  natural-language answer    └──────────┬───────────┘
      │                                         │ JSON-RPC over stdio
      │                             ┌───────────▼───────────┐
      │                             │      MCP Client        │
      │                             │ (built into the app —  │
      │                             │  spawns & talks to the │
      │                             │  server subprocess)    │
      │                             └───────────┬───────────┘
      │                                         │ tools/list, tools/call
      │                             ┌───────────▼───────────┐
      │                             │      MCP Server         │
      │                             │      (server.py)        │
      │                             │  @mcp.tool() functions   │
      │                             └───────────┬───────────┘
      │                                         │ subprocess.run(["docker", ...])
      │                             ┌───────────▼───────────┐
      │                             │   Docker CLI / daemon   │
      └─────────────────────────────┴────────────────────────┘
                 result flows back up through every layer
```

Everything left of "MCP Client" (the AI assistant's reasoning) is not code you wrote —
it's the model reading tool schemas and docstrings. Everything from "MCP Server" down
is this project.

## Full request-response lifecycle, one more time, precisely

1. Client process starts `python3 server.py` as a subprocess (per `.mcp.json`).
2. Client → Server: `initialize` (protocol version, capabilities) — Server replies with
   its own capabilities and `serverInfo.name`.
3. Client → Server: `notifications/initialized` (no reply expected — just an ack that the
   handshake is done).
4. Client → Server: `tools/list` — Server replies with all six tools' names, JSON Schemas
   (from type hints), and descriptions (from docstrings).
5. User asks a question. The model, with those six schemas in context, picks zero, one,
   or multiple tools to call, and may **chain** calls — e.g. `list_containers` first to
   resolve a container name, then `inspect_container` with that exact name.
6. Client → Server: `tools/call` with the tool name and a JSON object of arguments matching
   the schema.
7. Server runs your plain Python function (e.g. `inspect_container_impl`), which shells
   out to `docker`, parses output, redacts secrets, and returns a dict.
8. FastMCP wraps that return value as `content` (text) and, for list-typed returns, also
   `structuredContent` — Server → Client as the `tools/call` response.
9. Client feeds the result into the model's context; model composes the natural-language
   answer; User sees it.
10. Steps 5–9 repeat for as many tool calls as the question needs, all within one client
    session — the subprocess from step 1 stays alive the whole time.

## Test suites in this repo

```bash
source .venv/bin/activate
python3 scripts/smoke_test.py      # protocol + all 6 tools + input-validation edge cases
python3 scripts/scenario_test.py   # 4 natural-language scenarios from the original spec,
                                    # with tool-chaining simulated the way a real client's
                                    # model would drive it
```

Both scripts spin up `server.py` fresh, drive it purely over stdio JSON-RPC — exactly
what a real client does — and assert on real results from real (throwaway) Docker
containers, not mocks.

## What "final" means here, honestly

- **Protocol layer**: fully verified — handshake, discovery, every tool call, structured
  and unstructured response shapes.
- **Tool logic**: fully verified — all 6 tools, against real running/stopped containers,
  real open/closed ports, real secret redaction.
- **Client integration**: config verified (`.mcp.json` paths resolve), lifecycle documented,
  but not exercised with a live GUI + live model in this environment (no Claude Desktop
  installed here). Opening a Claude Code session with this project directory would complete
  that last mile.
- **OmniRoute tie-in (optional next step)**: OmniRoute is running (`localhost:20128/v1`) but
  has no model registered yet (`/v1/models` returns `[]`) — the API key needs to be added
  through OmniRoute's own dashboard, not just its `.env`, since providers live in its
  database. Once a model is registered there, this MCP server's tool schemas could be
  passed directly into an OmniRoute chat-completion call with `tools=[...]` to get a *real*
  LLM doing the tool selection that `scenario_test.py` currently simulates by hand.

## Task to verify understanding (final)

Walk through, from memory, what happens between you typing "is postgres healthy?" and
seeing an answer — name every hop (User → ... → Docker → ... → User) and what travels
over each one. If you can do this without re-reading Stage 1, you've internalized the
protocol, not just copied the code.
