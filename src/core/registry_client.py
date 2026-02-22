import requests

BASE_URL = "http://localhost:12121/v0"

def get_servers():
    """Fetch all published MCP servers from AgentRegistry."""
    resp = requests.get(f"{BASE_URL}/servers")
    resp.raise_for_status()
    data = resp.json()
    # CLI paginates, but local registry returns simple structure
    # handle both possibilities
    if isinstance(data, dict) and "servers" in data:
        return data["servers"]
    return data


def get_deployments():
    """Fetch deployments from registry."""
    resp = requests.get(f"{BASE_URL}/deployments")
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "deployments" in data:
        return data["deployments"]
    return data

# print("TESTING REGISTRY CLIENT")
# print("Fetching servers...")
# servers = get_servers()
# print(f"Received {len(servers)} servers:")
# for server in servers:
#     server_obj = server["server"] if "server" in server else server
#     print(f"- {server_obj['name']} (ID: {server_obj['description']})")
# print("\nFetching deployments...")
# deployments = get_deployments()
# print(f"Received {len(deployments)} deployments:")
# for deployment in deployments:
#     print(deployment, type(deployment))
