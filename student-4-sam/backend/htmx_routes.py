from html import escape

from flask import Blueprint, request

from database import get_connection
from agentic_loop import analyse_shipment


htmx_transportation = Blueprint(
    "htmx_transportation",
    __name__
)


VALID_STATUSES = {
    "PLANNED",
    "READY_FOR_DISPATCH",
    "IN_TRANSIT",
    "DELAYED",
    "DELIVERED",
    "CANCELLED"
}


def render_shipments():
    connection = get_connection()

    shipments = connection.execute(
        """
        SELECT *
        FROM shipments
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    html = """
    <table border="1" cellpadding="8">
        <thead>
            <tr>
                <th>ID</th>
                <th>Origin</th>
                <th>Destination</th>
                <th>Status</th>
                <th>Driver</th>
                <th>Vehicle</th>
                <th>Delay</th>
                <th>Actions</th>
            </tr>
        </thead>

        <tbody>
    """

    for shipment in shipments:
        shipment_id = shipment["id"]

        html += f"""
        <tr id="shipment-{shipment_id}">
            <td>{shipment_id}</td>

            <td>
                {escape(shipment["origin"])}
            </td>

            <td>
                {escape(shipment["destination"])}
            </td>

            <td>
                {escape(shipment["status"])}
            </td>

            <td>
                {escape(shipment["driver"] or "")}
            </td>

            <td>
                {escape(shipment["vehicle"] or "")}
            </td>

            <td>
                {shipment["delay_minutes"]} min
            </td>

            <td>

                <button
                    hx-get="http://localhost:5004/htmx/shipments/{shipment_id}/edit"
                    hx-target="#shipment-{shipment_id}"
                    hx-swap="outerHTML">
                    Edit
                </button>

                <button
                    hx-delete="http://localhost:5004/htmx/shipments/{shipment_id}"
                    hx-target="#shipment-table"
                    hx-swap="innerHTML"
                    hx-confirm="Delete this shipment?">
                    Delete
                </button>

                <button
                    hx-post="http://localhost:5004/htmx/shipments/{shipment_id}/analyse"
                    hx-target="#ai-result"
                    hx-swap="innerHTML">
                    Analyse with Qwen
                </button>

            </td>
        </tr>
        """

    html += """
        </tbody>
    </table>
    """

    return html


@htmx_transportation.get(
    "/htmx/shipments"
)
def get_shipments():
    return render_shipments()


@htmx_transportation.post(
    "/htmx/shipments"
)
def create_shipment():
    origin = request.form.get(
        "origin",
        ""
    ).strip()

    destination = request.form.get(
        "destination",
        ""
    ).strip()

    status = request.form.get(
        "status",
        "PLANNED"
    ).upper()

    driver = request.form.get(
        "driver",
        ""
    ).strip()

    vehicle = request.form.get(
        "vehicle",
        ""
    ).strip()

    try:
        delay_minutes = int(
            request.form.get(
                "delay_minutes",
                0
            )
        )
    except ValueError:
        delay_minutes = 0

    if not origin or not destination:
        return (
            "<p>Origin and destination are required.</p>",
            400
        )

    if status not in VALID_STATUSES:
        return (
            "<p>Invalid status.</p>",
            400
        )

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO shipments (
            origin,
            destination,
            status,
            driver,
            vehicle,
            delay_minutes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            origin,
            destination,
            status,
            driver,
            vehicle,
            delay_minutes
        )
    )

    connection.commit()
    connection.close()

    return render_shipments()


@htmx_transportation.get(
    "/htmx/shipments/<int:shipment_id>/edit"
)
def edit_shipment(shipment_id):
    connection = get_connection()

    shipment = connection.execute(
        """
        SELECT *
        FROM shipments
        WHERE id = ?
        """,
        (shipment_id,)
    ).fetchone()

    connection.close()

    if shipment is None:
        return (
            "<tr><td>Shipment not found</td></tr>",
            404
        )

    return f"""
    <tr id="shipment-{shipment_id}">

        <td>
            {shipment_id}
        </td>

        <td>
            <input
                name="origin"
                value="{escape(shipment['origin'])}">
        </td>

        <td>
            <input
                name="destination"
                value="{escape(shipment['destination'])}">
        </td>

        <td>
            <select name="status">

                <option
                    value="PLANNED"
                    {"selected" if shipment["status"] == "PLANNED" else ""}>
                    PLANNED
                </option>

                <option
                    value="READY_FOR_DISPATCH"
                    {"selected" if shipment["status"] == "READY_FOR_DISPATCH" else ""}>
                    READY_FOR_DISPATCH
                </option>

                <option
                    value="IN_TRANSIT"
                    {"selected" if shipment["status"] == "IN_TRANSIT" else ""}>
                    IN_TRANSIT
                </option>

                <option
                    value="DELAYED"
                    {"selected" if shipment["status"] == "DELAYED" else ""}>
                    DELAYED
                </option>

                <option
                    value="DELIVERED"
                    {"selected" if shipment["status"] == "DELIVERED" else ""}>
                    DELIVERED
                </option>

                <option
                    value="CANCELLED"
                    {"selected" if shipment["status"] == "CANCELLED" else ""}>
                    CANCELLED
                </option>

            </select>
        </td>

        <td>
            <input
                name="driver"
                value="{escape(shipment["driver"] or "")}">
        </td>

        <td>
            <input
                name="vehicle"
                value="{escape(shipment["vehicle"] or "")}">
        </td>

        <td>
            <input
                type="number"
                name="delay_minutes"
                min="0"
                value="{shipment["delay_minutes"]}">
        </td>

        <td>

            <button
                hx-put="http://localhost:5004/htmx/shipments/{shipment_id}"
                hx-include="#shipment-{shipment_id} input, #shipment-{shipment_id} select"
                hx-target="#shipment-table"
                hx-swap="innerHTML">
                Save
            </button>

            <button
                hx-get="http://localhost:5004/htmx/shipments"
                hx-target="#shipment-table"
                hx-swap="innerHTML">
                Cancel
            </button>

        </td>

    </tr>
    """


@htmx_transportation.put(
    "/htmx/shipments/<int:shipment_id>"
)
def update_shipment(shipment_id):
    origin = request.form.get(
        "origin",
        ""
    ).strip()

    destination = request.form.get(
        "destination",
        ""
    ).strip()

    status = request.form.get(
        "status",
        "PLANNED"
    ).upper()

    driver = request.form.get(
        "driver",
        ""
    ).strip()

    vehicle = request.form.get(
        "vehicle",
        ""
    ).strip()

    try:
        delay_minutes = int(
            request.form.get(
                "delay_minutes",
                0
            )
        )
    except ValueError:
        delay_minutes = 0

    connection = get_connection()

    existing = connection.execute(
        """
        SELECT id
        FROM shipments
        WHERE id = ?
        """,
        (shipment_id,)
    ).fetchone()

    if existing is None:
        connection.close()

        return (
            "<p>Shipment not found.</p>",
            404
        )

    connection.execute(
        """
        UPDATE shipments
        SET
            origin = ?,
            destination = ?,
            status = ?,
            driver = ?,
            vehicle = ?,
            delay_minutes = ?
        WHERE id = ?
        """,
        (
            origin,
            destination,
            status,
            driver,
            vehicle,
            delay_minutes,
            shipment_id
        )
    )

    connection.commit()
    connection.close()

    return render_shipments()


@htmx_transportation.delete(
    "/htmx/shipments/<int:shipment_id>"
)
def delete_shipment(shipment_id):
    connection = get_connection()

    connection.execute(
        """
        DELETE FROM shipments
        WHERE id = ?
        """,
        (shipment_id,)
    )

    connection.commit()
    connection.close()

    return render_shipments()


@htmx_transportation.post(
    "/htmx/shipments/<int:shipment_id>/analyse"
)
def analyse_transportation(shipment_id):
    try:
        result = analyse_shipment(
            shipment_id
        )

    except RuntimeError as error:
        return (
            f"<p>AI service unavailable: {escape(str(error))}</p>",
            503
        )

    if result is None:
        return (
            "<p>Shipment not found.</p>",
            404
        )

    observation = result["observe"]

    return f"""
    <div>

        <h3>PLAN</h3>
        <p>
            {escape(result["plan"])}
        </p>

        <h3>ACT</h3>
        <p>
            {escape(result["act"])}
        </p>

        <h3>OBSERVE</h3>

        <p>
            Shipment:
            {observation["shipment_id"]}
        </p>

        <p>
            Route:
            {escape(observation["origin"])}
            →
            {escape(observation["destination"])}
        </p>

        <p>
            Status:
            {escape(observation["status"])}
        </p>

        <p>
            Delay:
            {observation["delay_minutes"]} minutes
        </p>

        <h3>ADAPT — QWEN</h3>

        <pre>{escape(result["adapt"])}</pre>

    </div>
    """