from typing import Any, TypeVar

import orjson
from lxml import etree
from quart import websocket

from ..events import TrackingTree
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


async def send(json: dict[str, Any]):
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
        self.event_listeners = self.selection._events
        self.html = self.prepare_html()

    def prepare_html(self) -> str:
        """
        Generates HTML content containing scripts for events

        Returns
        -------
        str
            HTML content
        """
        ttree = TrackingTree()
        if ttree.root is None:
            return "<html></html>"
        node = ttree.root
        tag = node.tag
        script = self.event_listeners.into_script()
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
                for json in self.event_listeners(event):
                    await send(json)

        @app.route("/")
        async def index():
            return self.html
        
        return app
