from core.server import mcp
from core.registry_client import get_servers


@mcp.tool()
def search_servers(query: str):
    """Search MCP servers by keyword in name or description."""
    servers = get_servers()
    query = query.lower()

    matches = []
    for s in servers:
        text = f"{s['server']['name']} {s['server'].get('description','')}".lower()
        if query in text:
            matches.append({
                "name": s["server"]["name"],
                "description": s["server"].get("description", ""),
                "version": s["server"].get("version", ""),
                "metadata": s.get("_meta", {})
            })

    return matches

