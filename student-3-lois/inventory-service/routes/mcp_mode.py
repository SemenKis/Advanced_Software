import json

from flask import Blueprint, request
import requests

from services.mcp_api import call_mcp_tool, mcp_disabled_response, mcp_mode_is_enabled

mcp_bp = Blueprint("mcp_mode", __name__)

def mcp_render_json(title: str, payload):
    return f"<h3>{title}</h3><pre>{json.dumps(payload, indent=2, default=str)}</pre>"


@mcp_bp.post("/mcp/product-count")
def mcp_product_count():
    if not mcp_mode_is_enabled(request):
        return mcp_disabled_response()
    try:
        result = call_mcp_tool("inventory_product_count", {})
        return mcp_render_json("MCP Tool: inventory_product_count", result), 200
    except requests.RequestException as exc:
        return f"<p>MCP product_count failed.</p><pre>{exc}</pre>", 503


@mcp_bp.post("/mcp/products-by-category")
def mcp_products_by_category():
    if not mcp_mode_is_enabled(request):
        return mcp_disabled_response()

    category_name = request.form.get("category_name", "").strip()
    if not category_name:
        return "<p>category_name is required.</p>", 400

    try:
        result = call_mcp_tool("inventory_products_by_category", {"category_name": category_name})
        return mcp_render_json("MCP Tool: inventory_products_by_category", result), 200
    except requests.RequestException as exc:
        return f"<p>MCP products_by_category failed.</p><pre>{exc}</pre>", 503


@mcp_bp.post("/mcp/low-stock-report")
def mcp_low_stock_report():
    if not mcp_mode_is_enabled(request):
        return mcp_disabled_response()
    try:
        result = call_mcp_tool("inventory_low_stock_report", {})
        return mcp_render_json("MCP Tool: inventory_low_stock_report", result), 200
    except requests.RequestException as exc:
        return f"<p>MCP low_stock_report failed.</p><pre>{exc}</pre>", 503


@mcp_bp.post("/mcp/supplier-lookup")
def mcp_supplier_lookup():
    if not mcp_mode_is_enabled(request):
        return mcp_disabled_response()

    supplier_name = request.form.get("supplier_name", "").strip()
    if not supplier_name:
        return "<p>supplier_name is required.</p>", 400

    try:
        result = call_mcp_tool("inventory_supplier_lookup", {"supplier_name": supplier_name})
        return mcp_render_json("MCP Tool: inventory_supplier_lookup", result), 200
    except requests.RequestException as exc:
        return f"<p>MCP supplier_lookup failed.</p><pre>{exc}</pre>", 503

