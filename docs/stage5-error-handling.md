# Stage 5 — Error Handling and Security

## Principle

Every tool must return a structured error dict (`{"error": "..."}`), never let a
Python exception escape to the MCP layer. An uncaught exception would crash the
`mcp.run()` event loop — killing every other tool for the rest of the session, not
just the one call that failed. A caught exception, by contrast, becomes one failed
`tools/call` the model can read, reason about, and route around.

## What was already safe from Stage 2–3

- **Safe subprocess execution**: `_run_docker` always calls `subprocess.run(["docker", *args], ...)`
  with a Python list, never `shell=True` or string concatenation. An AI-supplied
  `container_name` can never break out into a second shell command.
- **Sensitive information filtering**: `_filter_env` redacts any env var whose key
  matches `PASSWORD|SECRET|TOKEN|KEY|CREDENTIAL|PWD` before it ever leaves `inspect_container`.
- **Invalid container handling**: a non-existent container name already produced a
  non-zero `docker inspect` exit code, caught and turned into `{"error": ...}`.

## What Stage 5 added — the gaps that were still there

1. **Timeout handling.** `subprocess.run(..., timeout=N)` raises `TimeoutExpired` if a
   docker call hangs — previously uncaught, this would have crashed the server.
   `_run_docker` now catches it and returns a `CompletedProcess` with `returncode=-1` and
   a descriptive `stderr`, so existing `if result.returncode != 0` checks in every
   `*_impl` function handle it automatically, with zero changes needed elsewhere.

2. **Docker daemon / CLI entirely unavailable.** If the `docker` binary itself isn't on
   `PATH` (not just "daemon not running" — the binary missing), `subprocess.run` raises
   `FileNotFoundError`. Also now caught in `_run_docker` and converted the same way.
   Verified by temporarily setting `PATH=/nonexistent` and confirming
   `check_docker_health_impl()` returns `{"healthy": False, "error": "docker CLI not found..."}`
   instead of crashing.

3. **Invalid port validation** (was already present, confirmed still correct):
   `check_port_impl` rejects `port <= 0` or `port >= 65536` *before* touching a socket —
   cheaper than a failed connect, and avoids OS-specific behavior for garbage port numbers.

4. **Input validation on container name / tail count.** `get_container_logs_impl` and
   `inspect_container_impl` now reject empty/whitespace `container_name` and non-positive
   `tail` up front, rather than letting Docker produce a confusing CLI error.

5. **Malformed-output safety.** `json.loads()` calls against `docker inspect` / `docker info`
   / `docker ps` output are now wrapped in `try/except json.JSONDecodeError` (and
   `IndexError` for `inspect`'s single-element array) — defensive against any future
   Docker CLI output-format change breaking the whole tool instead of just that call.

## Why validate *before* the external call, not just catch failures after

Cheaper (no network/subprocess round-trip for input that can never succeed), and the
error message is under your control and immediately meaningful ("port must be 1-65535")
rather than whatever raw error the OS or Docker CLI happens to produce for garbage input.

## Terminal verification

```bash
source .venv/bin/activate
python3 scripts/smoke_test.py
```

New assertions added this stage: empty `container_name`, out-of-range `port`, negative
`tail` — each expected to return `{"error": ...}` rather than raise. All ten checks pass.

## Task to verify understanding

`_run_docker`'s `FileNotFoundError` handler and its `TimeoutExpired` handler both return
a `CompletedProcess` with `returncode=-1` instead of, say, `-2` and `-3` to distinguish
them. Does that matter to any caller right now? What would you need to change if a caller
*did* need to tell "timed out" apart from "binary missing" programmatically (not just via
the error string)?
