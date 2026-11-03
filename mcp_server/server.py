"""Small MCP stdio adapter over the Django REST API.

Run this with: python mcp_server/server.py
For container use, run: podman compose run --rm app python /app/mcp_server/server.py
Configure your MCP client to launch that command in this project directory.
"""
import json
import os
import requests
from mcp.server.fastmcp import FastMCP

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
mcp = FastMCP("cricket-log-search")

def api_get(path: str, params: dict | None = None):
    response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def api_post(path: str, payload: dict):
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def cricket_stats() -> str:
    """Return event totals, matches, event-type/status breakdowns, and data-quality flag counts."""
    return json.dumps(api_get("/api/stats/"), ensure_ascii=False, indent=2)

@mcp.tool()
def search_cricket_events(query: str, top_k: int = 5, match_id: str = "", event_type: str = "", player: str = "", team: str = "", status: str = "") -> str:
    """Find semantically similar cricket log events. Optional metadata filters must exactly match stored values."""
    filters = {k: v for k, v in {"match_id": match_id, "event_type": event_type, "player": player, "team": team, "status": status}.items() if v}
    return json.dumps(api_post("/api/search/", {"query": query, "top_k": top_k, "filters": filters}), ensure_ascii=False, indent=2)

@mcp.tool()
def ask_cricket_logs(question: str, top_k: int = 5) -> str:
    """Ask a question about cricket logs and return the answer plus retrieved event evidence."""
    return json.dumps(api_post("/api/chat/", {"question": question, "top_k": top_k}), ensure_ascii=False, indent=2)

@mcp.tool()
def list_cricket_events(match_id: str = "", player: str = "", team: str = "", event_type: str = "", status: str = "") -> str:
    """List events using exact MongoDB metadata filters. Useful for enumerating records, not semantic similarity."""
    params = {k: v for k, v in {"match_id": match_id, "player": player, "team": team, "event_type": event_type, "status": status}.items() if v}
    return json.dumps(api_get("/api/events/", params), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    mcp.run(transport="stdio")
