"""type-a-cmp-mcp -- FastMCP server wrapping a REST API as MCP tools."""

import os
from typing import Any

import httpx
from fastmcp import FastMCP

mcp = FastMCP("type-a-cmp-mcp")

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict | list:
    """Send an HTTP request to the upstream REST API and return the JSON response."""
    headers: dict[str, str] = {"Accept": "application/json"}

    token = os.environ.get("API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        resp = await client.request(
            method, path, headers=headers, params=params, json=json_body
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# MCP Tools -- replace these placeholders with your actual API endpoints
# ---------------------------------------------------------------------------


@mcp.tool
async def list_items(limit: int = 50, offset: int = 0) -> list[dict]:
    """List items from the API.

    Args:
        limit: Maximum number of items to return (default 50).
        offset: Number of items to skip for pagination (default 0).
    """
    return await _request("GET", "/items", params={"limit": limit, "offset": offset})


@mcp.tool
async def get_item(item_id: str) -> dict:
    """Get a single item by its identifier.

    Args:
        item_id: The unique identifier of the item.
    """
    return await _request("GET", f"/items/{item_id}")


@mcp.tool
async def create_item(name: str, description: str = "") -> dict:
    """Create a new item.

    Args:
        name: Name of the item to create.
        description: Optional description for the item.
    """
    return await _request(
        "POST", "/items", json_body={"name": name, "description": description}
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
