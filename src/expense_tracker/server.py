"""MCP server: the imperative shell around the expense domain.

Tools are added feature by feature, each one driven by a spec in
specs/<feature>/spec.md.
"""

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("expense-tracker")


def main() -> None:
    """Entry point for the `expense-tracker-mcp` console script."""
    mcp.run(transport="stdio")
