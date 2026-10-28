import importlib.util
import sys
from pathlib import Path
 
SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
 
import coordinator
from agents import inventory_planner_agent as planner
from agents import inventory_reviewer_agent as reviewer
from agents import inventory_worker_agent as worker
from domains import DOMAINS
 
APP_SPEC = importlib.util.spec_from_file_location(
    "shared_multi_agent_inventory_test_app", SERVER_ROOT / "app.py"
)
app_module = importlib.util.module_from_spec(APP_SPEC)
APP_SPEC.loader.exec_module(app_module)
app = app_module.app
 
PRODUCTS = [
    {"product_id": 1, "name": "Barcode Scanners", "brand": "ClickTech",
     "category_name": "Organisation Tools", "supplier_name": "TrackTools Co.",
     "price": 35.99, "quantity": 120, "reorder_level": 20},
    {"product_id": 2, "name": "Pallet Jacks", "brand": "LoadMaster",
     "category_name": "Loading Equipment", "supplier_name": "Global Machinery Ltd.",
     "price": 139.49, "quantity": 8, "reorder_level": 15},
    {"product_id": 12, "name": "Hand Truck", "brand": "LoadMaster",
     "category_name": "Loading Equipment", "supplier_name": "Global Machinery Ltd.",
     "price": 89.50, "quantity": 9, "reorder_level": 10},
]
 
 
def _patch_data(monkeypatch, products=PRODUCTS, reply="Summary."):
    monkeypatch.setattr(worker, "fetch_products", lambda: products)
    monkeypatch.setattr(worker, "call_model", lambda *a, **k: reply)
 
 
def test_inventory_domain_is_registered_with_plan_passing():
    assert "inventory" in DOMAINS
    assert DOMAINS["inventory"]["worker_uses_plan"] is True
    assert {"plan", "work", "review"} <= DOMAINS["inventory"].keys()
 
 
def test_low_stock_request_filters_to_low_products(monkeypatch):
    _patch_data(monkeypatch)
    result = worker.generate_output("Which products are low on stock?")
    ids = [r["product_id"] for r in result["evidence"] if r["kind"] == "product"]
    assert sorted(ids) == [2, 12]  # product 1 is well stocked
    summary = result["evidence"][0]
    assert summary["kind"] == "stock_summary"
    assert summary["product_count"] == 2 and summary["low_stock_count"] == 2
    assert result["human_approval_required"] is True
 
 
def test_product_id_filter_uses_exact_id_not_prefix(monkeypatch):
    _patch_data(monkeypatch)
    result = worker.generate_output("Review product 1")
    ids = [r["product_id"] for r in result["evidence"] if r["kind"] == "product"]
    assert ids == [1]  # must not also match product 12
 
 
def test_category_and_supplier_are_read_from_data(monkeypatch):
    _patch_data(monkeypatch)
    by_cat = worker.generate_output("Show loading equipment stock")
    assert by_cat["filters"]["categories"] == ["loading equipment"]
    assert by_cat["evidence"][0]["product_count"] == 2
    by_sup = worker.generate_output("Anything from TrackTools Co.?")
    assert by_sup["filters"]["suppliers"] == ["tracktools co."]
    assert by_sup["evidence"][0]["product_count"] == 1
 
 
def test_stock_value_total(monkeypatch):
    _patch_data(monkeypatch)
    summary = worker.generate_output("Show all products")["evidence"][0]
    expected = round(35.99 * 120 + 139.49 * 8 + 89.50 * 9, 2)
    assert summary["total_stock_value"] == expected
    assert summary["total_units"] == 137
 
 
def test_planner_output_reaches_worker_prompt(monkeypatch):
    seen = []
    monkeypatch.setattr(worker, "fetch_products", lambda: PRODUCTS)
    monkeypatch.setattr(worker, "call_model",
                        lambda m, s, u, **k: seen.append(u) or "ok")
    plan = {"status": "completed", "output": "Check reorder levels first"}
    worker.generate_output("Review product 2", plan)
    assert plan["output"] in seen[0]
 
 
def test_reviewer_receives_plan_evidence_and_worker_output(monkeypatch):
    seen = []
    monkeypatch.setattr(reviewer, "call_model",
                        lambda m, s, u, **k: seen.append(u) or "Verdict: Approve")
    plan = {"output": "Plan step"}
    result = {"output": "Worker says product 2 is low", "evidence": [{"product_id": 2}]}
    reviewer.review_output("Review product 2", plan, result)
    assert "Plan step" in seen[0]
    assert '"product_id": 2' in seen[0]
    assert "Worker says product 2 is low" in seen[0]
 
 
def test_no_match_skips_model(monkeypatch):
    monkeypatch.setattr(worker, "fetch_products", lambda: PRODUCTS)
 
    def boom(*a, **k):
        raise AssertionError("model must not be called when nothing matches")
 
    monkeypatch.setattr(worker, "call_model", boom)
    result = worker.generate_output("Review product 999")
    assert result["status"] == "completed"
    assert result["evidence"] == []
    assert "No products match" in result["output"]
 
 
def test_inventory_api_failure_is_reported(monkeypatch):
    import requests
 
    def down():
        raise requests.ConnectionError("db down")
 
    monkeypatch.setattr(worker, "fetch_products", down)
    result = worker.generate_output("Show products")
    assert result["status"].startswith("error")
    assert result["evidence"] == []
    assert result["human_approval_required"] is True
 
 
def test_model_failure_falls_back_to_evidence_summary(monkeypatch):
    monkeypatch.setattr(worker, "fetch_products", lambda: PRODUCTS)
 
    def fail(*a, **k):
        raise ConnectionError("ollama down")
 
    monkeypatch.setattr(worker, "call_model", fail)
    monkeypatch.setattr(planner, "call_model", fail)
    monkeypatch.setattr(reviewer, "call_model", fail)
    w = worker.generate_output("low stock")
    assert w["status"].startswith("fallback")
    assert "Product 2" in w["output"]
    assert planner.plan_workflow("low stock")["status"].startswith("fallback")
    assert "Verdict: Needs changes" in reviewer.review_output("q", {}, w)["output"]
 
 
def test_full_http_workflow_and_decision(tmp_path, monkeypatch):
    monkeypatch.setattr(coordinator, "HISTORY_PATH", tmp_path / "history.jsonl")
    monkeypatch.setattr(coordinator, "AUDIT_PATH", tmp_path / "audit.jsonl")
    _patch_data(monkeypatch)
    monkeypatch.setattr(planner, "call_model", lambda *a, **k: "1. Fetch products")
    monkeypatch.setattr(reviewer, "call_model", lambda *a, **k: "Verdict: Approve")
 
    client = app.test_client()
    resp = client.post("/workflow", json={"request": "Which products are low on stock?",
                                          "domain": "inventory"})
    assert resp.status_code == 200
    wf = resp.get_json()
    assert wf["domain"] == "inventory"
    assert wf["worker"]["evidence"][0]["kind"] == "stock_summary"
    assert wf["human_decision"]["status"] == "pending"
 
    # Correct needs a note
    assert client.post("/workflow/decision", json={
        "workflow_id": wf["workflow_id"], "decision": "Correct", "domain": "inventory",
    }).status_code == 400
 
    ok = client.post("/workflow/decision", json={
        "workflow_id": wf["workflow_id"], "decision": "Correct",
        "note": "Pallet jack reorder level is 20", "domain": "inventory",
    })
    assert ok.status_code == 200
 
    status = client.get("/workflow/status?domain=inventory").get_json()
    assert status["workflow_count"] == 1
    assert status["latest_workflow"]["human_decision"]["decision"] == "Correct"
 
    # Other domains must not see it, and a wrong-domain decision is rejected.
    assert client.get("/workflow/status?domain=orders").get_json()["workflow_count"] == 0
 
 
def test_low_stock_phrasings_are_detected():
    for text in ("Which products are low on stock?", "low stock items", "what needs reordering",
                 "stock is low for loaders", "anything below reorder level",
                 "are we running out of tape", "out of stock?"):
        assert worker.wants_low_stock(text), text
    for text in ("Show all products", "What is the price of product 3?",
                 "Summarise loading equipment"):
        assert not worker.wants_low_stock(text), text
 
