def format_orders_html(orders):
    if not orders:
        return "<p>No orders found.</p>"

    html = "<ul>"
    for order in orders:
        html += (
            f"<li>{order['order_id']} - "
            f"{order['order_name']} - {order['subject_code']}</li>"
        )
    html += "</ul>"
    return html


def format_order_html(order):
    return (
        f"<p>ID: {order['order_id']}<br>"
        f"Name: {order['order_name']}<br>"
        f"Subject: {order['subject_code']}</p>"
    )
# Format 'ORD-00000'
def format_order_ref(order_id):
    return f"ORD-{int(order_id):05d}"

# return dictionary with order_ref formatting
def with_order_ref(order):
    return {**order, "order_ref": format_order_ref(order["order_id"])}