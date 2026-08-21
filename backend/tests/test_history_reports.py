"""Tests for new features: transaction filters (GET /api/transactions) and weekly report."""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

TINY_PNG = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)


@pytest.fixture(scope="module")
def products():
    r = requests.get(f"{BASE_URL}/api/products", timeout=20)
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def seeded(products):
    """Create one sale + one purchase in the current week for filter/report checks."""
    product = next(p for p in products if p["stock"] >= 5)
    marker = f"TEST_{uuid.uuid4().hex[:8]}"
    created = []
    purchase = requests.post(f"{BASE_URL}/api/transactions", json={
        "type": "purchase", "product_id": product["id"], "quantity": 3,
        "unit_price": 12000, "note": marker, "proof_image": TINY_PNG}, timeout=20)
    assert purchase.status_code == 200, purchase.text
    created.append(purchase.json())
    sale = requests.post(f"{BASE_URL}/api/transactions", json={
        "type": "sale", "product_id": product["id"], "quantity": 2,
        "unit_price": 18000, "note": marker}, timeout=20)
    assert sale.status_code == 200, sale.text
    created.append(sale.json())
    return {"product": product, "marker": marker, "purchase": created[0], "sale": created[1]}


# --- GET /api/transactions filters ---
class TestTransactionFilters:
    def test_no_params_returns_all_sorted_desc(self, seeded):
        r = requests.get(f"{BASE_URL}/api/transactions", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 2
        assert all("_id" not in t for t in data)
        stamps = [t["created_at"] for t in data]
        assert stamps == sorted(stamps, reverse=True), "transactions not sorted newest first"
        ids = {t["id"] for t in data}
        assert seeded["sale"]["id"] in ids and seeded["purchase"]["id"] in ids

    @pytest.mark.parametrize("ttype", ["sale", "purchase"])
    def test_type_filter(self, ttype, seeded):
        r = requests.get(f"{BASE_URL}/api/transactions", params={"type": ttype}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data, f"no {ttype} transactions returned"
        assert all(t["type"] == ttype for t in data)
        assert seeded[ttype]["id"] in {t["id"] for t in data}

    def test_invalid_type_is_ignored(self):
        r = requests.get(f"{BASE_URL}/api/transactions", params={"type": "bogus"}, timeout=20)
        assert r.status_code == 200
        assert len(r.json()) == len(requests.get(f"{BASE_URL}/api/transactions", timeout=20).json())

    def test_search_case_insensitive(self, seeded):
        name = seeded["product"]["name"]
        r = requests.get(f"{BASE_URL}/api/transactions", params={"q": name.upper()}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data
        assert all(name.lower() in t["product_name"].lower() for t in data)
        r2 = requests.get(f"{BASE_URL}/api/transactions", params={"q": name[:4].lower()}, timeout=20)
        assert r2.status_code == 200 and r2.json()

    def test_search_no_match_returns_empty(self):
        r = requests.get(f"{BASE_URL}/api/transactions", params={"q": "zzz_no_such_product_zzz"}, timeout=20)
        assert r.status_code == 200
        assert r.json() == []

    def test_date_range_today_inclusive(self, seeded):
        today = datetime.now(timezone.utc).date().isoformat()
        r = requests.get(f"{BASE_URL}/api/transactions", params={"date_from": today, "date_to": today}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        ids = {t["id"] for t in data}
        assert seeded["sale"]["id"] in ids, "today's transaction missing from inclusive date range"
        assert all(t["created_at"][:10] == today for t in data)

    def test_date_to_before_creation_excludes(self, seeded):
        past = (datetime.now(timezone.utc).date() - timedelta(days=365)).isoformat()
        r = requests.get(f"{BASE_URL}/api/transactions", params={"date_to": past}, timeout=20)
        assert r.status_code == 200
        assert seeded["sale"]["id"] not in {t["id"] for t in r.json()}

    def test_date_from_future_returns_empty(self):
        future = (datetime.now(timezone.utc).date() + timedelta(days=5)).isoformat()
        r = requests.get(f"{BASE_URL}/api/transactions", params={"date_from": future}, timeout=20)
        assert r.status_code == 200
        assert r.json() == []

    def test_combined_filters(self, seeded):
        today = datetime.now(timezone.utc).date().isoformat()
        r = requests.get(f"{BASE_URL}/api/transactions", params={
            "type": "sale", "q": seeded["product"]["name"], "date_from": today, "date_to": today}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert seeded["sale"]["id"] in {t["id"] for t in data}
        assert all(t["type"] == "sale" and t["created_at"][:10] == today for t in data)

    def test_proof_image_persisted(self, seeded):
        r = requests.get(f"{BASE_URL}/api/transactions", params={"q": seeded["product"]["name"]}, timeout=20)
        match = next(t for t in r.json() if t["id"] == seeded["purchase"]["id"])
        assert match["proof_image"] == TINY_PNG


# --- GET /api/reports/weekly ---
class TestWeeklyReport:
    def test_current_week_structure_and_totals(self, seeded):
        r = requests.get(f"{BASE_URL}/api/reports/weekly", params={"week_offset": 0}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        expected = {"week_start", "week_end", "label", "sales_total", "purchases_total",
                    "cash_flow", "sales_count", "purchases_count", "products", "share_text"}
        assert expected <= d.keys()
        start = datetime.fromisoformat(d["week_start"]).date()
        end = datetime.fromisoformat(d["week_end"]).date()
        assert start.weekday() == 0, "week does not start on Monday"
        assert (end - start).days == 6
        today = datetime.now(timezone.utc).date()
        assert start <= today <= end
        assert abs(d["cash_flow"] - (d["sales_total"] - d["purchases_total"])) < 0.01
        assert d["sales_count"] >= 1 and d["purchases_count"] >= 1
        # totals must match transactions in that window
        txs = requests.get(f"{BASE_URL}/api/transactions", params={
            "date_from": d["week_start"], "date_to": d["week_end"]}, timeout=20).json()
        sales = round(sum(t["total"] for t in txs if t["type"] == "sale"), 2)
        purchases = round(sum(t["total"] for t in txs if t["type"] == "purchase"), 2)
        assert round(d["sales_total"], 2) == sales
        assert round(d["purchases_total"], 2) == purchases
        assert len([t for t in txs if t["type"] == "sale"]) == d["sales_count"]

    def test_product_movement_matches_seed(self, seeded):
        d = requests.get(f"{BASE_URL}/api/reports/weekly", timeout=20).json()
        row = next((m for m in d["products"] if m["name"] == seeded["product"]["name"]), None)
        assert row is not None, "seeded product missing from weekly movement"
        assert row["sold"] >= 2 and row["purchased"] >= 3
        assert row["sales_value"] >= 36000 and row["purchases_value"] >= 36000
        values = [m["sales_value"] + m["purchases_value"] for m in d["products"]]
        assert values == sorted(values, reverse=True), "movement not sorted by value desc"

    def test_share_text_content(self):
        d = requests.get(f"{BASE_URL}/api/reports/weekly", timeout=20).json()
        text = d["share_text"]
        lines = text.split("\n")
        assert lines[0].startswith("GreenBasket weekly report")
        assert d["label"] in lines[0]
        idr = lambda v: "Rp " + f"{v:,.0f}".replace(",", ".")
        assert "$" not in text, "share text still uses dollar formatting"
        assert idr(d["sales_total"]) in text
        assert idr(d["purchases_total"]) in text
        assert "Cash flow:" in text
        cash_line = next(l for l in lines if l.startswith("Cash flow:"))
        assert idr(abs(d["cash_flow"])) in cash_line
        assert ("+" if d["cash_flow"] >= 0 else "-") in cash_line
        assert ("Stock movement:" in text) == bool(d["products"])

    def test_previous_week_offset(self):
        cur = requests.get(f"{BASE_URL}/api/reports/weekly", params={"week_offset": 0}, timeout=20).json()
        prev = requests.get(f"{BASE_URL}/api/reports/weekly", params={"week_offset": -1}, timeout=20).json()
        assert prev["label"] != cur["label"]
        d_cur = datetime.fromisoformat(cur["week_start"]).date()
        d_prev = datetime.fromisoformat(prev["week_start"]).date()
        assert (d_cur - d_prev).days == 7
        assert prev["week_end"] < cur["week_start"]

    def test_far_future_week_is_empty(self):
        d = requests.get(f"{BASE_URL}/api/reports/weekly", params={"week_offset": 200}, timeout=20).json()
        assert d["sales_total"] == 0 and d["purchases_total"] == 0
        assert d["products"] == []
        assert "No stock movement this week." in d["share_text"]

    def test_invalid_offset_returns_422(self):
        r = requests.get(f"{BASE_URL}/api/reports/weekly", params={"week_offset": "abc"}, timeout=20)
        assert r.status_code == 422
