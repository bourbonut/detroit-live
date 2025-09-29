import asyncio
import detroit_live as d3
from detroit_live.events.event_listeners import EventListeners
from detroit_live.events.event_producers import EventProducers
import orjson
import pytest

@pytest.mark.asyncio
async def test_create_app_1():
    svg = d3.create("svg")
    app = svg.create_app()
    client = app.test_client()
    response = await client.get("/")
    assert response.status_code == 200
    content = await response.get_data()
    content = content.decode()
    assert "<html>" in content
    assert "<body>" in content
    assert "<script>" in content
    assert "localhost" in content
    assert "5000" in content

@pytest.mark.asyncio
async def test_create_app_2():
    svg = d3.create("svg")
    app = svg.create_app()
    client = app.test_client()
    response = await client.get("/")
    assert response.status_code == 200
    content = await response.get_data()
    content = content.decode()
    for _ in range(10):
        response = await client.get("/")
    content = await response.get_data()
    content = content.decode()
    assert len(content.split("<script>")) == 2 # only one script

@pytest.mark.asyncio
async def test_create_app_3():
    svg = d3.create("svg")
    app = svg.create_app(host="111.222.3.444", port=1234)
    client = app.test_client()
    response = await client.get("/")
    assert response.status_code == 200
    content = await response.get_data()
    content = content.decode()
    assert "<html>" in content
    assert "<body>" in content
    assert "<script>" in content
    assert "111.222.3.444" in content
    assert "1234" in content

@pytest.mark.asyncio
async def test_create_app_4():
    svg = d3.create("svg")
    result = []
    def html(selection, script):
        result.extend([selection, script])
        return "<html></html>"
    app = svg.create_app(html=html)
    client = app.test_client()
    response = await client.get("/")
    assert response.status_code == 200
    content = await response.get_data()
    content = content.decode()
    assert content == "<html></html>"
    assert len(result) == 2

@pytest.mark.asyncio
async def test_create_app_5():
    svg = d3.create("svg")
    app = svg.create_app()
    assert app.name == "detroit-live"
    app = svg.create_app("mytestapp")
    assert app.name == "mytestapp"

@pytest.mark.asyncio
async def test_create_app_6(monkeypatch):
    json = {
        "x": 150,
        "y": 250,
        "clientX": 100,
        "clientY": 200,
        "pageX": 300,
        "pageY": 400,
        "button": 1,
        "ctrlKey": True,
        "shiftKey": False,
        "altKey": True,
        "elementId": "svg",
        "rectTop": 75,
        "rectLeft": 100,
        "type": "MouseEvent",
        "typename": "mousedown",
    }
    def mock_call(self, event):
        yield "Success"
    monkeypatch.setattr(EventListeners, "__call__", mock_call)
    def mock_queue_task(self, result=None):
        return
    monkeypatch.setattr(EventProducers, "queue_task", mock_queue_task)
    svg = d3.create("svg")
    app = svg.create_app()
    client = app.test_client()
    async with client.websocket('/ws') as test_websocket:
        await test_websocket.send(orjson.dumps(json).decode())
        result = await test_websocket.receive()
    assert result.decode() == '"Success"'
    event_producers = d3.event_producers()
    for task in event_producers._pending.values():
        task.cancel()

@pytest.mark.asyncio
async def test_create_app_7(monkeypatch):
    queue = asyncio.Queue()
    calls = {"next_tasks": 0, "queue_task": 0}

    async def task():
        queue.put_nowait((None, {"status": "success"}))
        return 10

    def mock_next_tasks(self, result=None):
        calls["next_tasks"] += 1
        if result is None:
            return {asyncio.create_task(task())}

    def mock_queue_task(self, result=None):
        calls["queue_task"] += 1
        if result is None:
            return asyncio.create_task(queue.get())

    monkeypatch.setattr(EventProducers, "next_tasks", mock_next_tasks)
    monkeypatch.setattr(EventProducers, "queue_task", mock_queue_task)
    svg = d3.create("svg")
    app = svg.create_app()
    client = app.test_client()
    async with client.websocket('/ws') as test_websocket:
        result = await test_websocket.receive()
    assert orjson.loads(result) == {"status": "success"}
    assert calls["next_tasks"] == 3
    assert calls["queue_task"] == 3
