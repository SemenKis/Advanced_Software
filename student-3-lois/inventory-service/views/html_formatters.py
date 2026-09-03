def format_products_html(products):
    if not products:
        return "<p>No products found.</p>"
    rows = ""
    for p in products:
        low_stock = p["quantity"] <= p["reorder_level"]
        badge = (
            '<span class="badge badge-low">Low stock</span>'
            if low_stock
            else '<span class="badge badge-ok">OK</span>'
        )
        rows += (
            "<tr>"
            f"<td>{p['product_id']}</td>"
            f"<td>{p['name']}</td>"
            f"<td>{p.get('brand') or '-'}</td>"
            f"<td>{p['category_name']}</td>"
            f"<td>{p['supplier_name']}</td>"
            f"<td>${p['price']:.2f}</td>"
            f"<td>{p['quantity']}</td>"
            f"<td>{badge}</td>"
            "</tr>"
        )
    return (
        '<table class="data-table">'
        "<thead><tr><th>ID</th><th>Name</th><th>Brand</th><th>Category</th>"
        "<th>Supplier</th><th>Price</th><th>Qty</th><th>Status</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def format_product_html(product):
    return (
        "<div class='product-detail'>"
        f"<p><strong>ID:</strong> {product['product_id']}</p>"
        f"<p><strong>Name:</strong> {product['name']}</p>"
        f"<p><strong>Brand:</strong> {product.get('brand') or '-'}</p>"
        f"<p><strong>Description:</strong> {product.get('description') or '-'}</p>"
        f"<p><strong>Category:</strong> {product['category_name']}</p>"
        f"<p><strong>Supplier:</strong> {product['supplier_name']}</p>"
        f"<p><strong>Price:</strong> ${product['price']:.2f}</p>"
        f"<p><strong>Quantity:</strong> {product['quantity']}</p>"
        f"<p><strong>Reorder level:</strong> {product['reorder_level']}</p>"
        "</div>"
    )


def format_categories_options(categories):
    return "".join(f"<option value='{c['category_id']}'>{c['name']}</option>" for c in categories)


def format_suppliers_options(suppliers):
    return "".join(f"<option value='{s['supplier_id']}'>{s['name']}</option>" for s in suppliers)


def format_stocktakes_html(stocktakes):
    if not stocktakes:
        return "<p>No stocktake activity recorded yet.</p>"
    rows = ""
    for s in stocktakes:
        rows += (
            "<tr>"
            f"<td>{s['stocktake_id']}</td>"
            f"<td>{s['product_name']}</td>"
            f"<td>{s['member_name']}</td>"
            f"<td>{s['counted_quantity']}</td>"
            f"<td>{s['timestamp']}</td>"
            "</tr>"
        )
    return (
        '<table class="data-table">'
        "<thead><tr><th>ID</th><th>Product</th><th>Member</th><th>Counted Qty</th><th>Timestamp</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )
