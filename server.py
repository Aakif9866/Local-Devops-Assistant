from mcp.server.fastmcp import FastMCP

from tools.docker_tools import list_containers_impl

mcp = FastMCP("local-devops-assistant")


@mcp.tool()
def hello_world(name: str) -> str:
    """Say hello to someone. Used to verify the MCP connection works end to end."""
    return f"Hello, {name}! Your MCP server is alive."


@mcp.tool()
def list_containers() -> list[dict]:
    """List all Docker containers (running or stopped) with name, image, status, and ports."""
    return list_containers_impl()


if __name__ == "__main__":
    mcp.run(transport="stdio")
