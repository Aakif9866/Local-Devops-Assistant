from mcp.server.fastmcp import FastMCP

mcp = FastMCP("local-devops-assistant")


@mcp.tool()
def hello_world(name: str) -> str:
    """Say hello to someone. Used to verify the MCP connection works end to end."""
    return f"Hello, {name}! Your MCP server is alive."


if __name__ == "__main__":
    mcp.run(transport="stdio")
