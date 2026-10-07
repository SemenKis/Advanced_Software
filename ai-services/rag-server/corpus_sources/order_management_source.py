import os
from collections import defaultdict
from datetime import datetime, timezone

import requests

DATABASE_SERVICE_URL = os.getenv("ORDER_DATABASE_SERVICE_URL", "http://localhost:5012")
SOURCE_PREFIX = "order"
SOURCE_ID = "order-database-service:/orders"

# NOTE ON CHUNK TEXT
# The shared pipeline embeds text by hashing whitespace-separated words, so
# "pending," or "status=pending" would NOT match the word "pending" in a query.
# Chunk text is therefore written as plain words separated by spaces, with no
# punctuation attached to the important words.


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chunk(chunk_id: str, text: str, **metadata) -> dict:
    return {
        "chunk_id": chunk_id,
        "source_id": SOURCE_ID,
        "authority_tier": "tier_1",
        "text": text,
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, **metadata},
        "indexed_at": _now_iso(),
    }


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def load_chunks() -> list[dict]:
    
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/orders", timeout=10)
        response.raise_for_status()
        orders = response.json()
        if not isinstance(orders, list):
            raise ValueError(f"unexpected response from /orders: {orders!r}")
    except Exception as exc:
        return [{
            "chunk_id": f"{SOURCE_PREFIX}_unreachable",
            "source_id": "order-database-service",
            "authority_tier": "tier_1",
            "text": f"Order database unreachable: {exc}",
            "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "reachable": False},
            "indexed_at": _now_iso(),
        }]

    chunks: list[dict] = []

    chunks.append(_chunk(
        f"{SOURCE_PREFIX}_order_count",
        f"Total number of orders in order management is {len(orders)}",
        metric="count",
    ))

    # One chunk per order
    for order in orders:
        order_id = order.get("order_id")
        amount = order.get("total_amount") or 0
        chunks.append(_chunk(
            f"{SOURCE_PREFIX}_record_{order_id}",
            (
                f"Order record order id {order_id} "
                f"customer {order.get('order_name', 'unknown')} "
                f"product {order.get('product_name', 'unknown')} "
                f"quantity {order.get('quantity', 'n/a')} "
                f"total amount {float(amount):.2f} "
                f"order status {order.get('order_status', 'unknown')} "
                f"delivery address {order.get('order_address', 'n/a')}"
            ),
            table="orders",
            order_id=order_id,
        ))

    # Orders grouped by status
    by_status: dict[str, list] = defaultdict(list)
    for order in orders:
        by_status[order.get("order_status") or "unknown"].append(order)

    if by_status:
        summary = " and ".join(
            f"{status} {len(group)}" for status, group in sorted(by_status.items())
        )
        chunks.append(_chunk(
            f"{SOURCE_PREFIX}_status_summary",
            f"Order status summary number of orders by status {summary}",
            metric="status_summary",
        ))
        for status, group in sorted(by_status.items()):
            ids = " ".join(str(o.get("order_id")) for o in group)
            chunks.append(_chunk(
                f"{SOURCE_PREFIX}_status_{status}",
                f"{status} orders there are {_plural(len(group), status + ' order')} "
                f"with order status {status} the {status} order ids are {ids}",
                metric="status_group",
                status=status,
            ))
    else:
        chunks.append(_chunk(
            f"{SOURCE_PREFIX}_status_summary",
            "There are no orders so no order status summary is available",
            metric="status_summary",
        ))

    # Orders grouped by product
    by_product: dict[str, list] = defaultdict(list)
    for order in orders:
        by_product[order.get("product_name") or "unknown"].append(order)

    if by_product:
        parts = []
        for product, group in sorted(by_product.items()):
            quantity = sum(int(o.get("quantity") or 0) for o in group)
            parts.append(f"{product} has {_plural(len(group), 'order')} with total quantity {quantity}")
        chunks.append(_chunk(
            f"{SOURCE_PREFIX}_product_summary",
            "Orders by product " + " and ".join(parts),
            metric="product_summary",
        ))

    total_value = sum(float(o.get("total_amount") or 0) for o in orders)
    chunks.append(_chunk(
        f"{SOURCE_PREFIX}_total_value",
        f"Total value of all orders is {total_value:.2f}",
        metric="total_value",
    ))

    return chunks