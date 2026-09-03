from flask import Blueprint, jsonify, request

from database import get_connection
from agentic_loop import analyse_shipment


transportation = Blueprint(
    "transportation",
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

@transportation.route("/api/shipments", methods=["GET"])
def get_shipments():
    connection = get_connection()

    shipments = connection.execute(
        """
        SELECT *
        FROM shipments
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    return jsonify(
        [dict(shipment) for shipment in shipments]
    )

@transportation.route(
    "/api/shipments/<int:shipment_id>",
    methods=["GET"]
)
def get_shipment(shipment_id):
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
        return jsonify({
            "error": "Shipment not found"
        }), 404

    return jsonify(dict(shipment))


@transportation.route(
    "/api/shipments",
    methods=["POST"]
)
def create_shipment():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    origin = data.get("origin")
    destination = data.get("destination")

    if not origin or not destination:
        return jsonify({
            "error": "Origin and destination are required"
        }), 400

    status = data.get(
        "status",
        "PLANNED"
    ).upper()

    if status not in VALID_STATUSES:
        return jsonify({
            "error": "Invalid shipment status"
        }), 400

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO shipments (
            origin,
            destination,
            status,
            driver,
            vehicle,
            departure_date,
            estimated_arrival,
            delay_minutes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            origin,
            destination,
            status,
            data.get("driver"),
            data.get("vehicle"),
            data.get("departure_date"),
            data.get("estimated_arrival"),
            data.get("delay_minutes", 0)
        )
    )

    connection.commit()

    shipment_id = cursor.lastrowid

    shipment = connection.execute(
        """
        SELECT *
        FROM shipments
        WHERE id = ?
        """,
        (shipment_id,)
    ).fetchone()

    connection.close()

    return jsonify(dict(shipment)), 201

@transportation.route(
    "/api/shipments/<int:shipment_id>",
    methods=["PUT"]
)
def update_shipment(shipment_id):
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    connection = get_connection()

    existing = connection.execute(
        """
        SELECT *
        FROM shipments
        WHERE id = ?
        """,
        (shipment_id,)
    ).fetchone()

    if existing is None:
        connection.close()

        return jsonify({
            "error": "Shipment not found"
        }), 404

    existing = dict(existing)

    status = data.get(
        "status",
        existing["status"]
    ).upper()

    if status not in VALID_STATUSES:
        connection.close()

        return jsonify({
            "error": "Invalid shipment status"
        }), 400

    connection.execute(
        """
        UPDATE shipments

        SET
            origin = ?,
            destination = ?,
            status = ?,
            driver = ?,
            vehicle = ?,
            departure_date = ?,
            estimated_arrival = ?,
            delay_minutes = ?

        WHERE id = ?
        """,
        (
            data.get(
                "origin",
                existing["origin"]
            ),

            data.get(
                "destination",
                existing["destination"]
            ),

            status,

            data.get(
                "driver",
                existing["driver"]
            ),

            data.get(
                "vehicle",
                existing["vehicle"]
            ),

            data.get(
                "departure_date",
                existing["departure_date"]
            ),

            data.get(
                "estimated_arrival",
                existing["estimated_arrival"]
            ),

            data.get(
                "delay_minutes",
                existing["delay_minutes"]
            ),

            shipment_id
        )
    )

    connection.commit()

    shipment = connection.execute(
        """
        SELECT *
        FROM shipments
        WHERE id = ?
        """,
        (shipment_id,)
    ).fetchone()

    connection.close()

    return jsonify(dict(shipment))


@transportation.route(
    "/api/shipments/<int:shipment_id>",
    methods=["DELETE"]
)
def delete_shipment(shipment_id):
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

        return jsonify({
            "error": "Shipment not found"
        }), 404

    connection.execute(
        """
        DELETE FROM shipments
        WHERE id = ?
        """,
        (shipment_id,)
    )

    connection.commit()
    connection.close()

    return jsonify({
        "message": "Shipment deleted successfully"
    })


@transportation.route(
    "/api/shipments/<int:shipment_id>/analyse",
    methods=["POST"]
)
def analyse_transportation(shipment_id):
    try:
        result = analyse_shipment(
            shipment_id
        )

        if result is None:
            return jsonify({
                "error": "Shipment not found"
            }), 404

        return jsonify(result)

    except RuntimeError as error:
        return jsonify({
            "error": str(error)
        }), 503