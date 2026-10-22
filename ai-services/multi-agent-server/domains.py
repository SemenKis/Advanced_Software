"""Maps a workflow domain to the agents that handle it.

Each domain keeps its own planner, worker and reviewer, so one team's logic
never has to be edited to change another's. "warehouse" is the default so
callers that send no domain behave exactly as before.
"""
from agents.order_planner_agent import plan_workflow as plan_orders
from agents.order_reviewer_agent import review_output as review_orders
from agents.order_worker_agent import generate_output as work_orders
from agents.planner_agent import plan_workflow as plan_warehouse
from agents.reviewer_agent import review_output as review_warehouse
from agents.worker_agent import generate_output as work_warehouse

DEFAULT_DOMAIN = "warehouse"

DOMAINS = {
    "warehouse": {"plan": plan_warehouse, "work": work_warehouse, "review": review_warehouse},
    "orders": {"plan": plan_orders, "work": work_orders, "review": review_orders},
}