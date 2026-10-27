"""Terminal client for the Multi-Agent Server.

Usage:
    python workflow_runner.py "Which storage zones are near capacity?"
    python workflow_runner.py --domain transportation "Which shipments are delayed?"
"""
import argparse
import json
import os

import requests

from domains import DEFAULT_DOMAIN, DOMAINS

SERVER_URL = os.getenv("MULTI_AGENT_SERVER_URL", "http://localhost:5005")
DECISIONS = {"1": "Accept", "2": "Correct", "3": "Reject"}


def main():
    parser = argparse.ArgumentParser(description="Run a shared multi-agent workflow.")
    parser.add_argument(
        "--domain",
        choices=sorted(DOMAINS),
        default=DEFAULT_DOMAIN,
        help=f"Workflow domain (default: {DEFAULT_DOMAIN})",
    )
    parser.add_argument("request", nargs="+", help="Request for the agents")
    args = parser.parse_args()
    user_request = " ".join(args.request)

    print(f"Running {args.domain} workflow on {SERVER_URL} ...")
    try:
        resp = requests.post(
            f"{SERVER_URL}/workflow",
            json={"request": user_request, "domain": args.domain},
            timeout=300,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        print(f"Could not run workflow: {exc}")
        return 1
    result = resp.json()

    for key in ("planner", "worker", "reviewer"):
        agent = result[key]
        print(f"\n[{key.upper()}] ({agent['status']}, {agent.get('model', 'n/a')})")
        print(agent["output"])
        if key == "worker" and agent.get("evidence"):
            print("Evidence:")
            print(json.dumps(agent["evidence"], indent=2))
    print(f"\nWorkflow ID: {result['workflow_id']}  ({result['duration_ms']} ms)")

    print("\nHuman review: 1 = Accept, 2 = Correct, 3 = Reject")
    choice = input("Your decision: ").strip()
    if choice not in DECISIONS:
        print("No valid decision entered. Workflow stays pending.")
        return 0
    note = input("Correction or reason (required for Correct): ").strip()
    try:
        resp = requests.post(
            f"{SERVER_URL}/workflow/decision",
            json={
                "workflow_id": result["workflow_id"],
                "decision": DECISIONS[choice],
                "note": note,
                "domain": args.domain,
            },
            timeout=10,
        )
        resp.raise_for_status()
        print(resp.json().get("message", resp.text))
    except requests.exceptions.RequestException as exc:
        print(f"Could not record human decision: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
