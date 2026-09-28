# Stage 3 — Docker Integration

## What we're building

The remaining four tools: `get_container_logs`, `inspect_container`, `check_port`,
`check_docker_health`. All wired the same way as Stage 2 — an `_impl` function in
`tools/`, a thin `@mcp.tool()` wrapper in `server.py`.

## How Python talks to Docker here

Deliberately **not** using the `docker` Python SDK. The Docker CLI is already installed
on any machine running Docker Desktop, and shelling out to it via `subprocess` with a
fixed argument list keeps the dependency count at zero and the command surface auditable
in one function (`_run_docker`). This is a legitimate tradeoff, not a shortcut: the
Docker SDK talks to the same daemon socket the CLI does, just with more moving parts.

## `get_container_logs`

```python
def get_container_logs_impl(container_name: str, tail: int = 100) -> dict:
    result = _run_docker(["logs", "--tail", str(tail), container_name])
```

Notice `container_name` — a string that could theoretically come from the AI based on
something you typed — lands as **one element in the argument list**, never interpolated
into a shell string. Even if a user tried `container_name = "x; rm -rf /"`, Docker would
just fail to find a container literally named that; there's no shell to interpret the
`;`.

## `inspect_container` and the secrets requirement

`docker inspect` dumps *everything*, including `Config.Env` — which regularly contains
`POSTGRES_PASSWORD`, `API_KEY`, etc. The task explicitly required these never reach the
AI. `_filter_env()` masks any variable whose **name** matches a sensitive pattern
(`PASSWORD`, `SECRET`, `TOKEN`, `KEY`, `CREDENTIAL`, `PWD`) and returns
`KEY=***REDACTED***` instead of dropping the entry entirely — the AI still learns *that*
a secret is configured (useful for diagnosis: "is DATABASE_PASSWORD even set?") without
ever seeing the value.

This was verified in the smoke test against a real `devops-test-postgres` container
with `POSTGRES_PASSWORD=testpass` set — the test asserts the string `REDACTED` appears
in the returned env list and would fail loudly if the raw password ever leaked through.

## `check_port`

Uses `socket.connect_ex()`, not Docker at all — a raw TCP connect attempt with a 2-second
timeout. This is why the tool works for *any* port check (e.g. "is 5432 reachable"),
not just Docker-published ports.

## `check_docker_health`

Runs `docker info --format {{json .}}`. If the daemon isn't running at all, `_run_docker`
still returns a `CompletedProcess` (it doesn't raise) with a non-zero return code and a
stderr message like `Cannot connect to the Docker daemon` — which is exactly what this
tool surfaces as `{"healthy": false, "error": "..."}"`. This is the tool an AI should
call *first* when every other tool starts failing, so it can tell the difference between
"Docker is down" and "that specific container doesn't exist."

## Reusable smoke test

`scripts/smoke_test.py` now exercises all six tools against real infrastructure — two
throwaway containers (`devops-test-nginx`, `devops-test-postgres`) started for this
purpose — and asserts on real values, not just "didn't crash":

```bash
source .venv/bin/activate
python3 scripts/smoke_test.py
```

It specifically checks: daemon health, real container listing, real log retrieval,
password redaction, open vs. closed port detection, and that an unknown container name
returns a structured error instead of an unhandled exception.

## A structural note on `structuredContent`

Tools returning `list[dict]` (like `list_containers`) get a populated
`structuredContent.result` in the MCP response. Tools returning a plain `dict` (like
`check_docker_health`) do not, in this SDK version — the data still arrives, but only
inside `content[0].text` as a JSON string. The smoke test's `call()` helper handles both
shapes. This is worth knowing before you assume every tool's output is machine-parseable
the same way.

## Task to verify understanding

`check_port_impl` validates `0 < port < 65536` before connecting. What class of bug does
this prevent, specifically — and why is validating *before* the network call better than
just letting `socket.connect_ex` fail naturally on a bad port number?
