import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tools import (
    check_storage_capacity,
    check_order_status,
    inventory_product_count,
    inventory_products_by_category,
    inventory_low_stock_report,
    inventory_supplier_lookup,
    check_shipment_status,
)

TOOLS = {
    "check_storage_capacity": check_storage_capacity,
    "check_order_status": check_order_status,
    "inventory_product_count": inventory_product_count,
    "inventory_products_by_category": inventory_products_by_category,
    "inventory_low_stock_report": inventory_low_stock_report,
    "inventory_supplier_lookup": inventory_supplier_lookup,
    "check_shipment_status": check_shipment_status,
}


class MCPHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8")) if raw else {}

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "mcp-server", "tools": list(TOOLS.keys())})
            return
        self._send_json(404, {"status": "error", "error": "not_found"})

    def do_POST(self):
        tool_name = self.path.replace("/tool/", "").strip("/")
        if tool_name not in TOOLS:
            self._send_json(404, {"status": "error", "error": f"Unknown tool: {tool_name}"})
            return

        try:
            payload = self._read_json()
        except Exception as exc:
            self._send_json(400, {"status": "error", "error": f"invalid_json: {exc}"})
            return

        try:
            result = TOOLS[tool_name](**payload)
            self._send_json(200, result)
        except Exception as exc:
            self._send_json(500, {"status": "error", "error": str(exc)})


def main():
    port = int(os.environ.get("MCP_PORT", "5004"))
    server = ThreadingHTTPServer(("0.0.0.0", port), MCPHandler)
    print(f"MCP HTTP server running on 0.0.0.0:{port}")
    print(f"Available tools: {list(TOOLS.keys())}")
    server.serve_forever()


if __name__ == "__main__":
    main()
