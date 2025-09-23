from detroit_live.events.headers import EVENT_HEADERS, headers

def test_headers():
    assert headers("localhost", "5000") == EVENT_HEADERS
    assert "128.284.1.8" in headers("128.284.1.8", "5000")
    assert "1500" in headers("localhost", "1500")
    multiple = headers("128.284.1.8", "1500")
    assert "128.284.1.8" in multiple
    assert "1500" in multiple
