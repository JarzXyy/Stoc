import os
import uuid
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://grocery-tracker-160.preview.emergentagent.com").rstrip("/")


def test_products_and_summary_load():
    products = requests.get(f"{BASE_URL}/api/products", timeout=15)
    assert products.status_code == 200
    data = products.json()
    assert data and all("id" in item and "stock" in item for item in data)
    summary = requests.get(f"{BASE_URL}/api/summary", timeout=15)
    assert summary.status_code == 200
    assert {"products", "stock_units", "sales", "purchases", "cash_flow", "low_stock"} <= summary.json().keys()


def test_purchase_sale_persistence_and_stock_change():
    products = requests.get(f"{BASE_URL}/api/products", timeout=15).json()
    product = next(item for item in products if item["stock"] >= 2)
    initial = product["stock"]
    marker = f"TEST_{uuid.uuid4().hex}"
    purchase = requests.post(f"{BASE_URL}/api/transactions", json={
        "type": "purchase", "product_id": product["id"], "quantity": 2,
        "unit_price": product["cost_price"], "note": marker,
        "proof_image": "data:image/png;base64,TESTPROOF",
    }, timeout=15)
    assert purchase.status_code == 200
    assert purchase.json()["proof_image"].startswith("data:image/")
    after_purchase = next(item for item in requests.get(f"{BASE_URL}/api/products", timeout=15).json() if item["id"] == product["id"])
    assert after_purchase["stock"] == initial + 2
    sale = requests.post(f"{BASE_URL}/api/transactions", json={
        "type": "sale", "product_id": product["id"], "quantity": 1,
        "unit_price": product["selling_price"], "note": marker,
    }, timeout=15)
    assert sale.status_code == 200
    after_sale = next(item for item in requests.get(f"{BASE_URL}/api/products", timeout=15).json() if item["id"] == product["id"])
    assert after_sale["stock"] == initial + 1
    transactions = requests.get(f"{BASE_URL}/api/transactions", timeout=15).json()
    assert any(item["note"] == marker and item["proof_image"] for item in transactions)


def test_transaction_rejects_invalid_and_excess_sale():
    product = requests.get(f"{BASE_URL}/api/products", timeout=15).json()[0]
    invalid = requests.post(f"{BASE_URL}/api/transactions", json={"type": "sale", "product_id": product["id"], "quantity": 0, "unit_price": 1}, timeout=15)
    assert invalid.status_code == 400
    excess = requests.post(f"{BASE_URL}/api/transactions", json={"type": "sale", "product_id": product["id"], "quantity": 999999, "unit_price": 1}, timeout=15)
    assert excess.status_code == 400