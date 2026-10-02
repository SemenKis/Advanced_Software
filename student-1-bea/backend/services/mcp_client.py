import os
import requests

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://host.docker.internal:5004")


def call_tool(tool_name, arguments=None):

    response = requests.post(
        f"{MCP_SERVER_URL}/tool/{tool_name}",
        json=arguments or {},
        timeout=10,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"status": "error", "error": response.text}
    return payload, response.status_code