# Stage 4 — Client Integration

## What we're building

Wiring `server.py` into a real MCP client's config so an AI assistant launches it
automatically and can call its tools during a conversation, instead of us manually
sending JSON-RPC over stdin like the smoke test does.

## Which client

Claude Desktop wasn't installed on this machine, so this project uses **Claude Code**
itself as the MCP client — it reads the same config shape and is what's already running.
The config format is effectively identical for both; the Claude Desktop version is
included below for reference.

## Claude Code: `.mcp.json`

Project-scoped config, placed at the project root (already committed):

```json
{
  "mcpServers": {
    "local-devops-assistant": {
      "command": "/absolute/path/to/local-devops-mcp/.venv/bin/python3",
      "args": ["/absolute/path/to/local-devops-mcp/server.py"]
    }
  }
}
```

Key detail: `command` points at the **venv's** `python3`, not the system one — that's
what makes `mcp` importable without manually activating the venv first. Claude Code
launches this as a subprocess itself; there's no "run the server" step for you to do
manually once this file exists.

Paths here are machine-specific (this user's home directory). On a different machine,
regenerate them with:

```bash
cd local-devops-mcp && pwd            # project dir
echo "$(pwd)/.venv/bin/python3"       # command value
echo "$(pwd)/server.py"               # args value
```

## Claude Desktop equivalent (for reference)

Same `mcpServers` key, different file location:
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS). Requires a
full quit + relaunch of Claude Desktop to pick up config changes (it doesn't hot-reload).

## What happens internally when you ask a natural-language question

Say you type: *"Is my postgres container healthy?"*

1. Claude Code already ran `tools/list` against this server when the session started
   (or config changed) — the six tool schemas + docstrings are sitting in context.
2. The model reads your question and matches it against tool descriptions. `inspect_container`'s
   docstring literally says "health" — that's the strongest signal, so the model picks it.
3. It also has to supply `container_name`. If you didn't say the exact name, the model
   may first call `list_containers` to find something matching "postgres" — this is the
   model chaining two tool calls on its own, not something you coded.
4. Client sends `tools/call` with `{"name": "inspect_container", "arguments": {"container_name": "devops-test-postgres"}}`.
5. Your Python function runs, returns the dict (health status, restart count, redacted env).
6. The result comes back as `content`/`structuredContent`, gets inserted into the model's
   context, and the model writes a sentence like "Yes, devops-test-postgres is healthy,
   0 restarts."

Nothing here is special-cased for Docker — the exact same lifecycle handles "what's on
port 5432" or "show me nginx's logs," because it's driven by docstrings and schemas, not
hardcoded intent matching.

## Verifying without a GUI

Since there's no interactive GUI client attached to this automated session, `scripts/smoke_test.py`
plays the client's role programmatically — same `initialize` → `notifications/initialized`
→ `tools/list` → `tools/call` sequence a real client performs, just scripted instead of
driven by a language model's tool-choice reasoning. That's *why* this project is testable
without ever opening an app: the protocol is faithfully reproducible outside any specific
client.

To test with the real thing: open a new Claude Code session with this project directory
as the working directory — it will auto-discover `.mcp.json` and load
`local-devops-assistant`'s tools into that session.

## Task to verify understanding

If you had two MCP servers configured with overlapping tool names (say, both expose a
`check_port` tool), what problem would that create for the model at tool-selection time,
and what's the obvious fix at the config level?
