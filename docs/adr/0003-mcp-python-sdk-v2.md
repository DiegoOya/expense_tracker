# 3. Official MCP Python SDK v2, venv + pip

- Status: accepted
- Date: 2026-10-05

## Context

Most examples online (and the model's own habits) use SDK v1, where
the server class was `FastMCP` in `mcp.server.fastmcp`. The installed
SDK is 2.3.0.

## Decision

- Use `mcp>=2.3,<3`: `from mcp.server.mcpserver import MCPServer`,
  tools with `@mcp.tool()`, `mcp.run(transport="stdio")`.
- Test tools in-process with `from mcp import Client`:
  `async with Client(server) as client: await client.call_tool(...)`.
  Results expose `is_error` and `structured_content`.
- Domain errors are converted to `mcp.server.mcpserver.exceptions.
  ToolError` in `server.py`. In v2 any other exception reaches the
  client only as "Error executing tool <name>", hiding the reason.
- Environment: `python -m venv` + `pip install -e ".[dev]"`, with
  bounded version ranges in `pyproject.toml` (no lock file).

## Consequences

- Error messages in specs can be asserted end to end.
- Without a lock file, CI may pick up new minor versions; the ranges
  limit the blast radius. Revisit (uv or pip-tools) if it bites.
