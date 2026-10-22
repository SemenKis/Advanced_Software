"""Terminal client for the Multi-Agent Server.

Usage:
    python workflow_runner.py "Which storage zones are near capacity?"
"""
import os
import sys

import requests

SERVER_URL = os.getenv("MULTI_AGENT_SERVER_URL", "http://localhost:5006")
DECISIONS = {"1": "Accept", "2": "Partially Accept", "3": "Reject"}


def main():
    if len(sys.argv) < 2:
        print('Usage: python workflow_runner.py "your request"')
        return 1
    user_request = " ".join(sys.argv[1:])

    print(f"Running workflow on {SERVER_URL} ...")
    try:
        resp = requests.post(f"{SERVER_URL}/workflow", json={"request": user_request}, timeout=300)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        print(f"Could not run workflow: {exc}")
        return 1
    result = resp.json()

    for key in ("planner", "worker", "reviewer"):
        agent = result[key]
        print(f"\n[{key.upper()}] ({agent['status']}, {agent['model']})")
        print(agent["output"])
    print(f"\nWorkflow ID: {result['workflow_id']}  ({result['duration_ms']} ms)")

    print("\nHuman review: 1 = Accept, 2 = Partially Accept, 3 = Reject")
    choice = input("Your decision: ").strip()
    if choice not in DECISIONS:
        print("No valid decision entered. Workflow stays pending.")
        return 0
    note = input("Reason (optional): ").strip()
    resp = requests.post(
        f"{SERVER_URL}/workflow/decision",
        json={"workflow_id": result["workflow_id"], "decision": DECISIONS[choice], "note": note},
        timeout=10,
    )
    print(resp.json().get("message", resp.text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
