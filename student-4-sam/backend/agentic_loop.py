from database import get_connection
from ollama_service import generate_response


def analyse_shipment(shipment_id):
    
    plan = (
        "Analyse the selected shipment for transportation "
        "delays, operational risks and recommended actions."
    )

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
        return None

    shipment = dict(shipment)

    act = (
        f"Retrieved shipment {shipment_id} "
        "from the transportation database."
    )

    observation = {
        "shipment_id": shipment["id"],
        "origin": shipment["origin"],
        "destination": shipment["destination"],
        "status": shipment["status"],
        "driver": shipment["driver"],
        "vehicle": shipment["vehicle"],
        "departure_date": shipment["departure_date"],
        "estimated_arrival": shipment["estimated_arrival"],
        "delay_minutes": shipment["delay_minutes"]
    }

    prompt = f"""
You are an AI assistant for a Transportation Management System.

Your responsibility is to analyse a shipment and provide useful,
practical transportation recommendations.

PLAN:
{plan}

SHIPMENT OBSERVATION:

Shipment ID: {shipment['id']}
Origin: {shipment['origin']}
Destination: {shipment['destination']}
Status: {shipment['status']}
Driver: {shipment['driver']}
Vehicle: {shipment['vehicle']}
Departure: {shipment['departure_date']}
Estimated Arrival: {shipment['estimated_arrival']}
Current Delay: {shipment['delay_minutes']} minutes

Analyse this transportation situation.

Return a concise response with exactly these sections:

Risk Level:
Identified Issues:
Recommended Actions:

Do not invent information that is not present in the shipment data.
"""

    recommendation = generate_response(prompt)

    return {
        "plan": plan,
        "act": act,
        "observe": observation,
        "adapt": recommendation
    }