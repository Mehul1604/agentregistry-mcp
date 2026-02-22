from core.server import mcp
from core.utils import get_tool_config
from core.registry_client import get_servers


@mcp.tool()
def list_servers() -> list:
    """Return all MCP servers registered in AgentRegistry."""
    servers = get_servers()
    return [
        {
            "name": s["server"]["name"],
            "description": s["server"].get("description", ""),
            "version": s["server"].get("version", ""),
            "metadata": s.get("_meta", {})
        }
        for s in servers
    ]

