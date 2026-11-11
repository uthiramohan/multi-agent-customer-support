import json

import pytest

from src.db import init_database


@pytest.fixture(scope="session", autouse=True)
def database():
    """Load Chinook into memory once for the whole test session."""
    return init_database()


@pytest.fixture
def call():
    """Invoke a LangChain tool and return (raw_json, parsed)."""
    def _call(tool, **kwargs):
        raw = tool.invoke(kwargs)
        return raw, json.loads(raw)
    return _call
