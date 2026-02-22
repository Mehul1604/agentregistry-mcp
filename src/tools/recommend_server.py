from core.server import mcp
from core.registry_client import get_servers, get_deployments


@mcp.tool()
def recommend_server(task: str):
    """
    Recommend the best MCP server for a task description.
    Uses simple keyword matching + deployment awareness.
    """
    servers = get_servers()
    deployments = get_deployments()

    deployed_names = {d["deployment"]["name"] for d in deployments} if isinstance(deployments, list) else set()

    task = task.lower()

    scored = []

    for s in servers:
        text = f"{s['server']['name']} {s['server'].get('description','')}".lower()

        score = 0
        if any(word in text for word in task.split()):
            score += 2

        if s["server"]["name"] in deployed_names:
            score += 1  # prefer already deployed servers

        scored.append((score, s))

    scored.sort(reverse=True, key=lambda x: x[0])

    if not scored:
        return {"message": "No servers found"}

    best = scored[0][1]

    return {
        "recommended": best["server"]["name"],
        "reason": "Best keyword match and deployment status"
    }

