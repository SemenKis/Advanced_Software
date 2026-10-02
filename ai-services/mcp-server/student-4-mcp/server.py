from mcp.server.fastmcp import FastMCP

from tools import get_delayed_shipments, get_shipment_count, get_shipment_status

mcp = FastMCP("Transportation Management MCP")

AVAILABLE_TOOLS = [
    "shipment_count",
    "shipment_status",
    "delayed_shipments",
]


@mcp.tool()
def shipment_count():
    return get_shipment_count()


@mcp.tool()
def shipment_status(shipment_id: str | int | None = None):
    return get_shipment_status(shipment_id)


@mcp.tool()
def delayed_shipments():
    return get_delayed_shipments()


if __name__ == "__main__":
    print("Starting Transportation Management MCP Server...")
    print("Server status: RUNNING")
    print("Interact with MCP tools from a second terminal.")
    print("Available tools:")
    for tool in AVAILABLE_TOOLS:
        print(f"- {tool}")
    mcp.run()
