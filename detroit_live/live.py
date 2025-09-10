from collections.abc import Iterator
from quart import websocket
from lxml import etree
import asyncio
import orjson
from .app import CustomQuart
from typing import TypeVar, Any
from itertools import chain
from hashlib import sha256

from detroit_live.events import EVENT_HEADERS, Event, EventHandler, EventGroup
from detroit_live.diffdict import diffdict

LiveSelection = TypeVar("LiveSelection")

def to_bytes(node: etree.Element) -> bytes:
    return etree.tostring(node).removesuffix(b"\n")

def to_string(node: etree.Element) -> str:
    return etree.tostring(node, method="html").decode("utf-8").removesuffix("\n")

async def send(json: dict):
    await websocket.send(orjson.dumps(json))

class Live:
    def __init__(self, selection: LiveSelection):
        self.selection = selection
        self.tree = self.selection._tree
        self.events = self.selection._events
        self.data = self.selection._data
        self.html = self.prepare_html()
        self.previous_id = ""

    def prepare_html(self):
        if self.tree is None:
            return "<html></html>"
        node = self.tree.root
        tag = node.tag
        script = EVENT_HEADERS + "".join(
            group.listener_script()
            for group in self.events.values()
        )
        if tag != "html":
            return f"<html><body>{self.selection}<script>{script}</script></body></html>"
        body = self.selection.select("body")
        if body._groups:
            body.append("script").text(script)
            return str(self.selection).replace("&lt;", "<").replace("&gt;", ">")
        else:
            self.append("script").text(script)
            return str(self.selection).replace("&lt;", "<").replace("&gt;", ">")

    def filter_handlers(self, event: Event, typename: str, group: EventGroup) -> Iterator[EventHandler]:
        # Filter handlers by typename
        handlers = [h for h in group if h.typename == typename]

        # Filter handlers by element_id when it is possible
        if hasattr(event, "element_id"):
            element_id = event.element_id
            if self.previous_id == element_id == "": # Unknown element ID
                return
            elif self.previous_id != element_id: # New element ID
                mouseleave = [
                    h for h in group
                    if h.node == self.previous_id and h.typename == "mouseleave"
                ]
                handlers = mouseleave + [h for h in handlers if h.node == element_id]
                self.previous_id = element_id
            else: # Same ID
                handlers = [h for h in handlers if h.node == element_id]
        return handlers

    async def propagate_event(self, event: Event, event_type: str):
        typename = event.get("typename")
        group = self.events[event_type]
        event = group.event.from_json(event)
        if handlers := self.filter_handlers(event, typename, group):
            for handler in handlers:
                await self.handle_event(handler, event)

    async def handle_event(self, handler: EventHandler, event: Event):
        # No specific node
        if handler.node is None:
            handler.listener(event, None, None)
            await send({"elementId": 0, "outerHTML": str(self.selection)})
            return

        element_ids = handler.nodes()
        nodes = [self.tree.get(node) for node in element_ids]
        old_attribs = [dict(node.attrib) for node in nodes]
        for i, node in enumerate(nodes):
            old_attribs[i]["innerHTML"] = node.text
        node_sha256 = [sha256(to_bytes(node)).digest() for node in nodes]

        node = self.tree.get(handler.node)
        handler.listener(event, self.data.get(node), node)

        # If any change
        for i, element_id in enumerate(element_ids):
            node = nodes[i]
            old_attrib = old_attribs[i]
            if node_sha256[i] != sha256(to_bytes(node)).digest():
                if len(node) == 0: # No child
                    new_attrib = dict(node.attrib)
                    new_attrib["innerHTML"] = node.text
                    diff = diffdict(old_attrib, new_attrib)
                    await send({"elementId": element_id, "diff": diff})
                else:
                    await send({"elementId": element_id, "outerHTML": to_string(node)})

    def run(
        self,
        name: str | None = None,
        host: str | None = None,
        port: int | None = None,
        debug: bool | None = None,
        use_reloader: bool = True,
        loop: asyncio.AbstractEventLoop | None = None,
        ca_certs: str | None = None,
        certfile: str | None = None,
        keyfile: str | None = None,
        **kwargs: Any,
    ): 
        app = CustomQuart(__name__ if name is None else name)

        @app.websocket("/ws")
        async def ws():
            while True:
                event = orjson.loads(await websocket.receive())
                event_type = event.get("type")
                if event_type not in self.events:
                    continue
                await self.propagate_event(event, event_type)


        @app.route("/")
        async def index():
            return self.html

        app.run(
            host,
            port,
            debug,
            use_reloader,
            loop,
            ca_certs,
            certfile,
            keyfile,
            **kwargs,
        )
