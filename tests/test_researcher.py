from src.agents.researcher import _normalize_sources


def test_normalize_sources_empty_input_returns_empty_list():
    assert _normalize_sources("", []) == []


def test_normalize_sources_falls_back_to_urls_in_raw_text():
    raw = "See https://example.com/page and https://another.org/post for details."

    normalized = _normalize_sources(raw, None)

    assert normalized == [
        {"url": "https://example.com/page", "title": "example.com/page"},
        {"url": "https://another.org/post", "title": "another.org/post"},
    ]


def test_normalize_sources_filters_malformed_urls():
    raw = "No valid urls here"
    extracted = [
        {"url": "not-a-url", "title": "bad"},
        {"url": "https://valid.com/x", "title": "Valid"},
        "ftp://not-allowed",
    ]

    normalized = _normalize_sources(raw, extracted)

    assert normalized == [{"url": "https://valid.com/x", "title": "Valid"}]
