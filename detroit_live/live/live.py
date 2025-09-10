from collections.abc import Iterator
from hashlib import sha256
from typing import TypeVar

import orjson
from lxml import etree
from quart import websocket

from .diffdict import diffdict
from .events import EVENT_HEADERS, Event, EventGroup, EventHandler

from .app import CustomQuart

LiveSelection = TypeVar("LiveSelection")


def to_bytes(node: etree.Element) -> bytes:
    """
    Converts a node element into bytes.

    Parameters
    ----------
    node : etree.Element
        Node element

    Returns
    -------
    bytes
        Bytes content of the node
    """
    return etree.tostring(node).removesuffix(b"\n")


def to_string(node: etree.Element) -> str:
    """
    Converts a node element into text.

    Parameters
    ----------
    node : etree.Element
        Node element

    Returns
    -------
    str
        Text content of the node.
    """
    return etree.tostring(node, method="html").decode("utf-8").removesuffix("\n")


async def send(json: dict):
    """
    Sends a json content message through websocket.

    Parameters
    ----------
    json : dict
        JSON message
    """
    await websocket.send(orjson.dumps(json))


class Live:
    """
    Live object which helps to make a interactive application through
    websocket.

    Parameters
    ----------
    selection : LiveSelection
        Live Selection
    """

    def __init__(self, selection: LiveSelection):
        self.selection = selection
        self.tree = self.selection._tree
        self.events = self.selection._events
        self.data = self.selection._data
        self.html = self.prepare_html()
        self.previous_id = ""

    def prepare_html(self) -> str:
        """
        Generates HTML content containing scripts for events

        Returns
        -------
        str
            HTML content
        """
        if self.tree is None:
            return "<html></html>"
        node = self.tree.root
        tag = node.tag
        script = EVENT_HEADERS + "".join(
            group.listener_script() for group in self.events.values()
        )
        if tag != "html":
            return (
                f"<html><body>{self.selection}<script>{script}</script></body></html>"
            )
        body = self.selection.select("body")
        if body._groups:
            body.append("script").text(script)
            return str(self.selection).replace("&lt;", "<").replace("&gt;", ">")
        else:
            self.append("script").text(script)
            return str(self.selection).replace("&lt;", "<").replace("&gt;", ">")

    def filter_handlers(
        self, event: Event, typename: str, group: EventGroup
    ) -> Iterator[EventHandler]:
        """
        Filters event handlers of a group given the event and the event
        typename.

        Parameters
        ----------
        event : Event
            Event
        typename : str
            Event typename
        group : EventGroup
            Group of event handlers

        Returns
        -------
        Iterator[EventHandler]
            Iterator of filtered event handlers
        """
        # Filter handlers by typename
        handlers = [h for h in group if h.typename == typename]

        # Filter handlers by element_id when it is possible
        if hasattr(event, "element_id"):
            element_id = event.element_id
            if self.previous_id == element_id == "":  # Unknown element ID
                return
            elif self.previous_id != element_id:  # New element ID
                mouseleave = [
                    h
                    for h in group
                    if h.node == self.previous_id and h.typename == "mouseleave"
                ]
                handlers = mouseleave + [h for h in handlers if h.node == element_id]
                self.previous_id = element_id
            else:  # Same ID
                handlers = [h for h in handlers if h.node == element_id]
        return handlers

    async def propagate_event(self, event: Event, event_type: str):
        """
        Propagate an event through its corresponding handlers.

        Parameters
        ----------
        event : Event
            Event
        event_type : str
            Event type
        """
        typename = event.get("typename")
        group = self.events[event_type]
        event = group.event.from_json(event)
        if handlers := self.filter_handlers(event, typename, group):
            for handler in handlers:
                await self.handle_event(handler, event)

    async def handle_event(self, handler: EventHandler, event: Event):
        """
        Handles an event by calling its listener and sends the updated
        information message through websocket.

        Parameters
        ----------
        handler : EventHandler
            Event handler
        event : Event
            Event
        """
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
                if len(node) == 0:  # No child
                    new_attrib = dict(node.attrib)
                    new_attrib["innerHTML"] = node.text
                    diff = diffdict(old_attrib, new_attrib)
                    await send({"elementId": element_id, "diff": diff})
                else:
                    await send({"elementId": element_id, "outerHTML": to_string(node)})

    def create_app(self, name: str | None = None) -> CustomQuart:
        """
        Creates an application for allowing interactivity.

        This is best used for development only, see Hypercorn for production
        servers.

        Parameters
        ----------
        name : str | None
            Name of the application

        Returns
        -------
        CustomQuart
            Application
        """
        app = CustomQuart("detroit-live" if name is None else name)

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
        
        return app
