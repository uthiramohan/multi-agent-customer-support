import json

import pytest

from src.agents.memory import merge_preferences
from src.db import lookup_customer_id, normalize_phone, run_query_safe, verify_database
from src.tools._common import like_pattern, safe_int


# ---- run_query_safe ---------------------------------------------------------
def test_basic_select_returns_valid_json():
    rows = json.loads(run_query_safe("SELECT COUNT(*) AS n FROM Customer"))
    assert rows == [{"n": 59}]


def test_parameterized_query_filters():
    rows = json.loads(run_query_safe(
        "SELECT CustomerId, FirstName FROM Customer WHERE CustomerId = :cid", {"cid": 1}))
    assert len(rows) == 1 and rows[0]["CustomerId"] == 1


def test_empty_result_is_empty_json_list():
    assert run_query_safe("SELECT * FROM Customer WHERE CustomerId = :cid", {"cid": -1}) == "[]"


def test_injection_payload_is_bound_as_plain_data():
    payload = "x' OR '1'='1"
    rows = json.loads(run_query_safe(
        "SELECT * FROM Customer WHERE Email = :email", {"email": payload}))
    assert rows == []


@pytest.mark.parametrize("query, expected", [
    ("SELECT COUNT(*) AS n FROM Artist", 275),
    ("SELECT COUNT(*) AS n FROM Album", 347),
    ("SELECT COUNT(*) AS n FROM Track", 3503),
    ("SELECT COUNT(*) AS n FROM Genre", 25),
    ("SELECT COUNT(*) AS n FROM Invoice", 412),
    ("SELECT COUNT(*) AS n FROM InvoiceLine", 2240),
])
def test_table_counts_match_spec(query, expected):
    assert json.loads(run_query_safe(query))[0]["n"] == expected


def test_parallel_queries_are_thread_safe():
    """Agents run tool calls in parallel threads against one in-memory connection."""
    from concurrent.futures import ThreadPoolExecutor
    query = "SELECT CustomerId FROM Invoice WHERE CustomerId = :cid ORDER BY InvoiceDate DESC"
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda i: len(json.loads(run_query_safe(query, {"cid": 5}))), range(200)))
    assert set(results) == {7}


# ---- normalize_phone --------------------------------------------------------
@pytest.mark.parametrize("raw, expected", [
    ("+1 (555) 123-4567", "+15551234567"),    # international, plus preserved
    ("555-123-4567", "5551234567"),           # dashes
    ("(555) 123 4567", "5551234567"),         # parentheses and spaces
    ("5551234567", "5551234567"),             # already digits
    ("+55 (12) 3923-5555", "+551239235555"),  # real Chinook format
])
def test_normalize_phone_formats(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", None, "   ", "abc"])
def test_normalize_phone_empty_inputs(raw):
    assert normalize_phone(raw) == ""


# ---- health check -----------------------------------------------------------
def test_verify_database_healthy():
    status = verify_database()
    assert status["status"] == "healthy"
    assert status["table_count"] >= 11
    assert status["missing_tables"] == []


# ---- customer lookup (identity verification) --------------------------------
def test_lookup_by_customer_id():
    assert lookup_customer_id("5") == "5"


def test_lookup_by_email_case_insensitive():
    assert lookup_customer_id("LUISG@EMBRAER.COM.BR") == "1"


@pytest.mark.parametrize("phone", ["+55 (12) 3923-5555", "+551239235555", "55 12 3923 5555"])
def test_lookup_by_phone_any_format(phone):
    assert lookup_customer_id(phone) == "1"


@pytest.mark.parametrize("bad", ["99999", "nobody@example.com", "123", "", None])
def test_lookup_not_found(bad):
    assert lookup_customer_id(bad) is None


# ---- helpers ----------------------------------------------------------------
def test_safe_int_valid_and_invalid():
    assert safe_int(" 42 ") == 42
    for bad in ["abc", "", None, "-3", "0", "1.5", True]:
        with pytest.raises(ValueError):
            safe_int(bad)


def test_like_pattern_escapes_wildcards():
    assert like_pattern("100%_x") == "%100\\%\\_x%"


# ---- memory merge -----------------------------------------------------------
def test_merge_preferences_is_union_and_never_removes():
    assert merge_preferences(["rock", "AC/DC"], ["jazz", "Rock"]) == ["rock", "AC/DC", "jazz"]
    assert merge_preferences(["rock"], []) == ["rock"]
