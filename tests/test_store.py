import json
import logging

from api.cache import NoCache
from api.logging_config import JsonFormatter
from api.main import generate_code
from api.store import MemoryStore, build_store


def test_memory_store_roundtrip():
    s = MemoryStore()
    assert s.save("abc", "https://a.com") is True
    assert s.get("abc") == "https://a.com"
    assert s.count() == 1
    assert s.get("nope") is None


def test_memory_store_refuses_to_overwrite():
    s = MemoryStore()
    s.save("abc", "https://a.com")
    assert s.save("abc", "https://b.com") is False
    assert s.get("abc") == "https://a.com"


def test_build_store_defaults_to_memory():
    assert build_store(None).kind == "memory"


def test_no_cache_is_a_harmless_null_object():
    c = NoCache()
    c.set("k", "v")
    assert c.get("k") is None and c.ping() is True


def test_generate_code_has_the_requested_length_and_alphabet():
    code = generate_code(MemoryStore(), length=8)
    assert len(code) == 8 and code.isalnum()


def test_generate_code_gives_up_when_everything_collides():
    class Full(MemoryStore):
        def get(self, code):
            return "taken"

    assert generate_code(Full(), attempts=3) is None


def test_json_log_lines_are_valid_json_with_extra_fields():
    record = logging.LogRecord("clippy", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    record.request_id = "r1"
    data = json.loads(JsonFormatter().format(record))
    assert data["msg"] == "hello world" and data["level"] == "info" and data["request_id"] == "r1"
