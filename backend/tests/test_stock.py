"""Tests for POST /api/products/{id}/stock (stock top-up) and light regression on products/summary."""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")


def get_product(pid):
    r = requests.get(f"{BASE_URL}/api/products", timeout=20)
    assert r.status_code == 200
    return next((p for p in r.json() if p["id"] == pid), None)


@pytest.fixture(scope="class")
def product():
    """Dedicated product per test module/worker so parallel workers don't fight over stock counts."""
    listing = requests.get(f"{BASE_URL}/api/products", timeout=20)
    assert listing.status_code == 200, listing.text
    assert listing.json(), "no products seeded"
    assert all("_id" not in p for p in listing.json())
    r = requests.post(f"{BASE_URL}/api/products", json={
        "name": f"TEST_stock_{uuid.uuid4().hex[:8]}", "category": "TEST", "unit": "unit",
        "stock": 20, "reorder_level": 5, "cost_price": 1.0, "selling_price": 2.0}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


# --- add stock happy path + persistence ---
class TestAddStock:
    def test_add_stock_increments_and_persists(self, product):
        before = get_product(product["id"])["stock"]
        r = requests.post(f"{BASE_URL}/api/products/{product['id']}/stock", json={"quantity": 7}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "_id" not in body
        assert body["id"] == product["id"]
        assert body["stock"] == before + 7, f"response stock {body['stock']} != {before + 7}"
        assert get_product(product["id"])["stock"] == before + 7, "stock not persisted"

    def test_repeated_adds_accumulate(self, product):
        before = get_product(product["id"])["stock"]
        for _ in range(3):
            r = requests.post(f"{BASE_URL}/api/products/{product['id']}/stock", json={"quantity": 2}, timeout=20)
            assert r.status_code == 200, r.text
        assert get_product(product["id"])["stock"] == before + 6

    def test_add_stock_reflected_in_summary(self, product):
        before = requests.get(f"{BASE_URL}/api/summary", timeout=20).json()["stock_units"]
        r = requests.post(f"{BASE_URL}/api/products/{product['id']}/stock", json={"quantity": 5}, timeout=20)
        assert r.status_code == 200
        after = requests.get(f"{BASE_URL}/api/summary", timeout=20).json()["stock_units"]
        assert after >= before + 5, "summary stock_units did not increase"

    @pytest.mark.parametrize("qty", [0, -1, -50])
    def test_non_positive_quantity_rejected(self, product, qty):
        before = get_product(product["id"])["stock"]
        r = requests.post(f"{BASE_URL}/api/products/{product['id']}/stock", json={"quantity": qty}, timeout=20)
        assert r.status_code == 400, f"expected 400 for qty={qty}, got {r.status_code}: {r.text}"
        assert "detail" in r.json()
        assert get_product(product["id"])["stock"] == before, "stock changed despite rejection"

    def test_unknown_product_returns_404(self):
        r = requests.post(f"{BASE_URL}/api/products/{uuid.uuid4().hex}/stock", json={"quantity": 3}, timeout=20)
        assert r.status_code == 404, r.text
        assert "detail" in r.json()

    def test_missing_quantity_returns_422(self, product):
        r = requests.post(f"{BASE_URL}/api/products/{product['id']}/stock", json={}, timeout=20)
        assert r.status_code == 422, r.text

    def test_non_integer_quantity_returns_422(self, product):
        r = requests.post(f"{BASE_URL}/api/products/{product['id']}/stock", json={"quantity": "abc"}, timeout=20)
        assert r.status_code == 422, r.text


# --- light regression: sale reduces stock, oversell rejected ---
class TestTransactionStockRegression:
    def test_sale_reduces_stock(self, product):
        requests.post(f"{BASE_URL}/api/products/{product['id']}/stock", json={"quantity": 10}, timeout=20)
        before = get_product(product["id"])["stock"]
        r = requests.post(f"{BASE_URL}/api/transactions", json={
            "type": "sale", "product_id": product["id"], "quantity": 4,
            "unit_price": 2.0, "note": "TEST_stock_regression"}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["total"] == 8.0
        assert get_product(product["id"])["stock"] == before - 4

    def test_oversell_rejected(self, product):
        current = get_product(product["id"])["stock"]
        r = requests.post(f"{BASE_URL}/api/transactions", json={
            "type": "sale", "product_id": product["id"], "quantity": current + 100,
            "unit_price": 1.0, "note": "TEST_oversell"}, timeout=20)
        assert r.status_code == 400, r.text
        assert get_product(product["id"])["stock"] == current
