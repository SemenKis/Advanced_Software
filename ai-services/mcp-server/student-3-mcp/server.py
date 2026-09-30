from mcp.server.fastmcp import FastMCP

from tools import (
    get_low_stock_report,
    get_product_count,
    get_products_by_category,
    get_supplier_lookup,
)

mcp = FastMCP("Inventory Management MCP")

AVAILABLE_TOOLS = [
    "product_count",
    "products_by_category",
    "low_stock_report",
    "supplier_lookup",
]


@mcp.tool()
def product_count():
    return get_product_count()


@mcp.tool()
def products_by_category(category_name: str):
    return get_products_by_category(category_name)


@mcp.tool()
def low_stock_report():
    return get_low_stock_report()


@mcp.tool()
def supplier_lookup(supplier_name: str):
    return get_supplier_lookup(supplier_name)


if __name__ == "__main__":
    print("Starting Inventory Management MCP Server...")
    print("Server status: RUNNING")
    print("Interact with MCP tools from a second terminal.")
    print("Available tools:")
    for tool in AVAILABLE_TOOLS:
        print(f"- {tool}")
    mcp.run()
