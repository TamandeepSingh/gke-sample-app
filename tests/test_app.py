# ============================================================
# tests/test_app.py — Unit tests for the calculator app
# ============================================================
# pytest is the test runner. It discovers this file automatically
# because the filename starts with "test_".
#
# Flask provides a test client that simulates HTTP requests
# without actually starting a server — tests run fast and in isolation.
#
# Run locally: pytest tests/ -v
# ============================================================

import sys
import os

# Add the app directory to Python's module search path so we can import app.py.
# This is needed because tests/ and app/ are sibling directories.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
from app import app as flask_app   # import the Flask instance from app.py


# ---------------------------------------------------------------
# Fixture: test client
# ---------------------------------------------------------------
# A pytest fixture is a reusable setup function.
# @pytest.fixture marks it so pytest injects it into test functions
# that declare it as a parameter.
@pytest.fixture
def client():
    # testing=True disables Flask's error handler so exceptions
    # propagate to the test and produce useful tracebacks.
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client   # yield hands the client to the test; cleanup runs after


# ---------------------------------------------------------------
# Tests
# ---------------------------------------------------------------

def test_home_page_loads(client):
    """GET / should return 200 and contain the form."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Calculator" in response.data


def test_health_check(client):
    """GET /healthz should return 200 — used by K8s probes."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.data == b"ok"


def test_addition(client):
    response = client.post("/calculate", data={"a": "10", "b": "5", "op": "add"})
    assert response.status_code == 200
    assert b"15" in response.data


def test_subtraction(client):
    response = client.post("/calculate", data={"a": "10", "b": "3", "op": "subtract"})
    assert response.status_code == 200
    assert b"7" in response.data


def test_multiplication(client):
    response = client.post("/calculate", data={"a": "6", "b": "7", "op": "multiply"})
    assert response.status_code == 200
    assert b"42" in response.data


def test_division(client):
    response = client.post("/calculate", data={"a": "10", "b": "4", "op": "divide"})
    assert response.status_code == 200
    assert b"2.5" in response.data


def test_division_by_zero(client):
    """Dividing by zero should return an error message, not crash."""
    response = client.post("/calculate", data={"a": "5", "b": "0", "op": "divide"})
    assert response.status_code == 200
    assert b"Cannot divide by zero" in response.data


def test_invalid_input(client):
    """Non-numeric input should return an error message."""
    response = client.post("/calculate", data={"a": "abc", "b": "5", "op": "add"})
    assert response.status_code == 200
    assert b"valid numbers" in response.data


def test_negative_numbers(client):
    response = client.post("/calculate", data={"a": "-3", "b": "-4", "op": "multiply"})
    assert response.status_code == 200
    assert b"12" in response.data


def test_decimal_numbers(client):
    response = client.post("/calculate", data={"a": "1.5", "b": "2.5", "op": "add"})
    assert response.status_code == 200
    assert b"4" in response.data
