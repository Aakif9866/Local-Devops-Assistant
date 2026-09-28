from mcp.server.fastmcp import FastMCP

from tools.docker_tools import (
    check_docker_health_impl,
    get_container_logs_impl,
    inspect_container_impl,
    list_containers_impl,
)
from tools.system_tools import check_port_impl

mcp = FastMCP("local-devops-assistant")


@mcp.tool()
def hello_world(name: str) -> str:
    """Say hello to someone. Used to verify the MCP connection works end to end."""
    return f"Hello, {name}! Your MCP server is alive."


@mcp.tool()
def list_containers() -> list[dict]:
    """List all Docker containers (running or stopped) with name, image, status, and ports."""
    return list_containers_impl()


@mcp.tool()
def get_container_logs(container_name: str, tail: int = 100) -> dict:
    """Get the most recent logs from a named Docker container."""
    return get_container_logs_impl(container_name, tail)


@mcp.tool()
def inspect_container(container_name: str) -> dict:
    """Inspect a container's config, health, network info, restart count, and exit code.
    Sensitive environment variables (passwords, secrets, tokens, keys) are redacted."""
    return inspect_container_impl(container_name)


@mcp.tool()
def check_port(port: int, host: str = "localhost") -> dict:
    """Check whether a TCP port is accessible on the given host (default localhost)."""
    return check_port_impl(port, host)


@mcp.tool()
def check_docker_health() -> dict:
    """Check whether the Docker daemon is running and responsive, with basic diagnostics."""
    return check_docker_health_impl()


if __name__ == "__main__":
    mcp.run(transport="stdio")
