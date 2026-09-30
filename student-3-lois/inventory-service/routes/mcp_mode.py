import json
import os

from flask import Blueprint, request
import requests

from services.database_api import get_low_stock_products, get_products

mcp_bp = Blueprint("mcp_mode", __name__)


def mcp_mode_is_enabled(req) -> bool:
    enabled = os.getenv("MCP_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
    if not enabled:
        return False
    mode_header = req.headers.get("X-MCP-Mode", "on").strip().lower()
    return mode_header in ("1", "true", "yes", "on")


def mcp_disabled_response():
    return "<p>MCP Mode is disabled.</p>", 403


def mcp_render_json(title: str, payload):
    return f"<h3>{title}</h3><pre>{json.dumps(payload, indent=2, default=str)}</pre>"


@mcp_bp.post("/mcp/product-count")
def mcp_product_count():
    if not mcp_mode_is_enabled(request):
        return mcp_disabled_response()
    try:
        count = len(get_products())
        return mcp_render_json("MCP Tool: product_count", {"product_count": count}), 200
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
        products = get_products()
        matches = [p for p in products if p.get("category_name", "").lower() == category_name.lower()]
        return mcp_render_json("MCP Tool: products_by_category", matches), 200
    except requests.RequestException as exc:
        return f"<p>MCP products_by_category failed.</p><pre>{exc}</pre>", 503


@mcp_bp.post("/mcp/low-stock-report")
def mcp_low_stock_report():
    if not mcp_mode_is_enabled(request):
        return mcp_disabled_response()
    try:
        report = get_low_stock_products()
        return mcp_render_json("MCP Tool: low_stock_report", report), 200
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
        products = get_products()
        matches = [p for p in products if p.get("supplier_name", "").lower() == supplier_name.lower()]
        if not matches:
            return mcp_render_json("MCP Tool: supplier_lookup", {"error": f"No products found for supplier '{supplier_name}'"}), 200
        return mcp_render_json("MCP Tool: supplier_lookup", matches), 200
    except requests.RequestException as exc:
        return f"<p>MCP supplier_lookup failed.</p><pre>{exc}</pre>", 503
