from agents.inventory_planner_agent import plan_workflow as plan_inventory
from agents.inventory_reviewer_agent import review_output as review_inventory
from agents.inventory_worker_agent import generate_output as work_inventory
from agents.order_planner_agent import plan_workflow as plan_orders
from agents.order_reviewer_agent import review_output as review_orders
from agents.order_worker_agent import generate_output as work_orders
from agents.planner_agent import plan_workflow as plan_warehouse
from agents.reviewer_agent import review_output as review_warehouse
from agents.worker_agent import generate_output as work_warehouse
from agents.transportation_planner_agent import plan_workflow as plan_transportation
from agents.transportation_reviewer_agent import review_output as review_transportation
from agents.transportation_worker_agent import generate_output as work_transportation

DEFAULT_DOMAIN = "warehouse"

DOMAINS = {
    "warehouse": {"plan": plan_warehouse, "work": work_warehouse, "review": review_warehouse},
    "orders": {"plan": plan_orders, "work": work_orders, "review": review_orders},
    "inventory": {"plan": plan_inventory, "work": work_inventory, "review": review_inventory, "worker_uses_plan": True},
    "transportation": {
        "plan": plan_transportation,
        "work": work_transportation,
        "review": review_transportation,
        "worker_uses_plan": True,
    },
}
