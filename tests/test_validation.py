"""POST /shorten must only accept sensible absolute http(s) URLs."""

import pytest


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "not a url",
        "ironhack.com",
        "javascript:alert(1)",
        "ftp://example.com/file",
        "https://",
        "https://exa mple.com",
        "https://example.com/\nsecond-line",
        "https://example.com/" + "a" * 300,
    ],
)
def test_bad_urls_are_rejected(client, bad):
    response = client.post("/shorten", json={"url": bad})
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.parametrize("good", ["https://ironhack.com", "http://localhost:8000/x?y=1#z", "https://sub.example.co.uk/a/b"])
def test_good_urls_are_accepted(client, good):
    assert client.post("/shorten", json={"url": good}).status_code == 200


def test_surrounding_whitespace_is_trimmed(client, store):
    body = client.post("/shorten", json={"url": "  https://ironhack.com \n"}).json()
    assert body["original_url"] == "https://ironhack.com"
    assert store.get(body["short_code"]) == "https://ironhack.com"
