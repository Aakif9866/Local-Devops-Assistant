# Local DevOps Assistant — MCP Server

A Python MCP server that lets an MCP-compatible AI assistant (Claude Desktop, Claude Code, Cursor)
inspect your local Docker environment: list containers, tail logs, inspect health, check ports,
and verify Docker itself is responsive.

Built as a learning project for understanding the Model Context Protocol from first principles —
see `docs/` for a stage-by-stage explanation of how it was built and why.

## Stack

- Python 3.10+
- Official `mcp` Python SDK (`FastMCP`, pinned `<2` — see `docs/stage1-fundamentals.md`)
- Docker CLI via `subprocess` (no extra SDK dependency)
- stdio transport (local subprocess, no HTTP/ports)

No LangChain, no RAG, no vector DBs, no extra AI API calls — this project is about the
protocol and the tools, not an LLM pipeline.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Tools

| Tool | Purpose |
|---|---|
| `hello_world` | Sanity-check the MCP connection |
| `list_containers` | List running/stopped containers |
| `get_container_logs` | Tail logs for a named container |
| `inspect_container` | Config, health, network, restart count (secrets filtered) |
| `check_port` | Check whether a TCP port is reachable |
| `check_docker_health` | Confirm the Docker daemon is up and responding |

All tools are read-only. No arbitrary shell command is ever built from AI-provided input.

## Running against Claude Desktop

See `docs/stage4-client-integration.md` for the config snippet and what happens end to end
when you ask a natural-language question.

## Docs

- [Stage 1 — MCP Fundamentals](docs/stage1-fundamentals.md)
- [Stage 2 — First Real Tool](docs/stage2-first-tool.md)
- [Stage 3 — Docker Integration](docs/stage3-docker-integration.md)
- [Stage 4 — Client Integration](docs/stage4-client-integration.md)
- [Stage 5 — Error Handling & Security](docs/stage5-error-handling.md)
- [Stage 6 — Final Testing & Architecture](docs/stage6-final-testing.md)
