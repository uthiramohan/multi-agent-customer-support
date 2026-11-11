import json

import pytest
from langchain_core.messages import AIMessage

from src.agents.invoice_agent import enforce_verified_customer_id
from src.tools.invoice_tools import (
    INVOICE_TOOLS, get_employee_by_invoice_and_customer, get_invoice_line_items,
    get_invoices_by_customer_sorted_by_date, get_purchased_tracks_sorted_by_price,
    get_support_rep_for_customer,
)


# ---- get_invoices_by_customer_sorted_by_date --------------------------------
def test_invoices_found_and_sorted_desc(call):
    _, data = call(get_invoices_by_customer_sorted_by_date, customer_id="1")
    dates = [r["InvoiceDate"] for r in data["results"]]
    assert len(dates) > 1
    assert dates == sorted(dates, reverse=True)


def test_invoices_total_spent_matches_sum(call):
    _, data = call(get_invoices_by_customer_sorted_by_date, customer_id="5")
    assert data["total_spent"] == round(sum(r["Total"] for r in data["results"]), 2)


def test_invoices_not_found(call):
    _, data = call(get_invoices_by_customer_sorted_by_date, customer_id="99999")
    assert data["status"] == "not_found"


def test_invoices_invalid_customer_id(call):
    _, data = call(get_invoices_by_customer_sorted_by_date, customer_id="abc")
    assert data["status"] == "error"


# ---- get_purchased_tracks_sorted_by_price -----------------------------------
def test_purchased_tracks_sorted_by_price(call):
    _, data = call(get_purchased_tracks_sorted_by_price, customer_id="1")
    prices = [r["UnitPrice"] for r in data["results"]]
    assert prices and prices == sorted(prices, reverse=True)
    assert "SongName" in data["results"][0]  # each row is a track, not an invoice


def test_purchased_tracks_not_found(call):
    _, data = call(get_purchased_tracks_sorted_by_price, customer_id="99999")
    assert data["status"] == "not_found"


# ---- get_employee_by_invoice_and_customer -----------------------------------
def test_employee_for_invoice_found(call):
    _, inv = call(get_invoices_by_customer_sorted_by_date, customer_id="1")
    invoice_id = str(inv["results"][0]["InvoiceId"])
    _, data = call(get_employee_by_invoice_and_customer, invoice_id=invoice_id, customer_id="1")
    assert data["status"] == "ok" and data["results"][0]["FirstName"]


def test_employee_for_other_customers_invoice_is_denied(call):
    _, inv = call(get_invoices_by_customer_sorted_by_date, customer_id="2")
    other_invoice = str(inv["results"][0]["InvoiceId"])
    _, data = call(get_employee_by_invoice_and_customer, invoice_id=other_invoice, customer_id="1")
    assert data["status"] == "not_found"


def test_employee_invalid_invoice_id(call):
    _, data = call(get_employee_by_invoice_and_customer, invoice_id="xyz", customer_id="1")
    assert data["status"] == "error"


# ---- get_invoice_line_items -------------------------------------------------
def test_line_items_found(call):
    _, inv = call(get_invoices_by_customer_sorted_by_date, customer_id="5")
    latest = inv["results"][0]
    _, data = call(get_invoice_line_items, invoice_id=str(latest["InvoiceId"]), customer_id="5")
    assert data["returned_count"] >= 1
    line_total = round(sum(r["UnitPrice"] * r["Quantity"] for r in data["results"]), 2)
    assert line_total == latest["Total"]


def test_line_items_not_found(call):
    _, data = call(get_invoice_line_items, invoice_id="999999", customer_id="5")
    assert data["status"] == "not_found"


# ---- get_support_rep_for_customer -------------------------------------------
def test_support_rep_found(call):
    _, data = call(get_support_rep_for_customer, customer_id="1")
    assert data["results"][0]["Title"]


def test_support_rep_not_found(call):
    _, data = call(get_support_rep_for_customer, customer_id="99999")
    assert data["status"] == "not_found"


# ---- JSON validity ----------------------------------------------------------
@pytest.mark.parametrize("tool, args", [
    (get_invoices_by_customer_sorted_by_date, {"customer_id": "1"}),
    (get_purchased_tracks_sorted_by_price, {"customer_id": "1"}),
    (get_employee_by_invoice_and_customer, {"invoice_id": "1", "customer_id": "2"}),
    (get_invoice_line_items, {"invoice_id": "abc", "customer_id": "1"}),
    (get_support_rep_for_customer, {"customer_id": ""}),
])
def test_invoice_outputs_are_valid_json(tool, args):
    assert isinstance(json.loads(tool.invoke(args)), dict)


# ---- secure customer-id injection -------------------------------------------
def test_tool_call_customer_id_is_forced_to_verified_id():
    msg = AIMessage(content="", id="m1", tool_calls=[{
        "name": "get_invoices_by_customer_sorted_by_date", "args": {"customer_id": "42"}, "id": "c1"}])
    out = enforce_verified_customer_id({"messages": [msg], "customer_id": "5"})
    assert out["messages"][0].tool_calls[0]["args"]["customer_id"] == "5"
    assert out["messages"][0].id == "m1"


def test_invoice_tools_registered():
    assert len(INVOICE_TOOLS) == 5
