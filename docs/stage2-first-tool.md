# Stage 2 — First Real Tool: `list_containers`

## What we're building

A tool that shells out to `docker ps -a` and returns structured container data
(name, image, status, ports) instead of a hello-world string.

## Why this shape

`tools/docker_tools.py` holds a pure function, `list_containers_impl()`, with no MCP
imports at all. `server.py` imports it and wraps it with `@mcp.tool()`. This separation
matters: the Docker logic is testable and reusable on its own, and the MCP layer stays a
thin adapter. You'll keep this pattern for every tool from here on.

```python
def list_containers_impl() -> list[dict]:
    result = _run_docker(["ps", "-a", "--format", "{{json .}}"])
    ...
```

```python
@mcp.tool()
def list_containers() -> list[dict]:
    """List all Docker containers (running or stopped) with name, image, status, and ports."""
    return list_containers_impl()
```

## Tool registration, descriptions, schemas — with a real example this time

- **Registration**: `@mcp.tool()` adds `list_containers` to the same registry `hello_world`
  is in. `tools/list` now returns two tools.
- **Parameter schema**: `list_containers()` takes no arguments, so FastMCP generates an
  empty input schema — the model doesn't need to supply anything to call it.
- **Description**: the docstring is the *only* thing the model sees to decide "does this
  tool answer questions like 'what containers are running?'" — vague docstrings produce
  vague tool selection.

## Structured responses

Look at what `tools/call` actually returns (captured from a real run):

```json
{
  "result": {
    "content": [ {"type": "text", "text": "{...one container as JSON text...}"}, ... ],
    "structuredContent": { "result": [ {"id": ..., "name": ..., "image": ...}, ... ] },
    "isError": false
  }
}
```

FastMCP gives you both: `content` (text blocks, for models that only read text) and
`structuredContent` (the actual typed data, parsed from your return type annotation).
This is why annotating `-> list[dict]` isn't cosmetic — it's what produces `structuredContent`.

## Safe subprocess execution (introduced early, not bolted on later)

```python
def _run_docker(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
```

Note there is no `shell=True` and no string concatenation of user input into a command.
`args` is always a fixed Python list — even once later tools accept a `container_name`
parameter from the AI, that string becomes one list element, never part of a shell
command line. This is what prevents command injection.

## Terminal verification

```bash
docker run -d --name devops-test-nginx -p 18080:80 nginx:alpine
python3 server.py   # then, from another process, send tools/list and tools/call
```

Full protocol smoke test (handshake → `notifications/initialized` → `tools/list` →
`tools/call`) is in `scripts/smoke_stage2.py`-equivalent logic; expected result:
`list_containers` appears in `tools/list`, and calling it returns your real containers,
including any test containers you started.

## Task to verify understanding

If `list_containers_impl()` raised a raw Python exception (say, `docker` binary not
found) instead of returning `{"error": ...}`, what would happen to the MCP response —
would the client see `isError: true`, or would the whole process crash? Think about it;
Stage 5 covers exactly this.
