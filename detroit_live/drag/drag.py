from lxml import etree
from collections.abc import Callable
from detroit.array import argpass
from detroit.types import Accessor
from typing import TypeVar
from .drag_event import DragEvent
from .nodrag import nodrag, yesdrag
from ..dispatch import dispatch
from ..events import MouseEvent, Event, pointer
from ..selection import LiveSelection, select
from ..types import EventFunction, T

TDrag = TypeVar("Drag", bound="Drag")

def constant(x):
    def f(*args):
        return x

def default_filter(event: MouseEvent, d: T | None, node: etree.Element) -> bool:
    return not event.ctrl_key and not event.button

def default_subject(event: DragEvent, d: T | None) -> T | dict[str, float]:
    return {"x": event.x, "y": event.y} if d is None else d

def default_container(event: MouseEvent, d: T | None, node: etree.Element) -> etree.Element:
    return node.getparent()

def default_touchable(selection: LiveSelection) -> Accessor[T, bool]:
    def touchable(d: T, i: int, group: list[etree.Element]) -> bool:
        target = group[i]
        def filter_func(node: etree.Element, typename: str, name: str) -> bool:
            return node == target and "touchstart" == typename
        for event_listener in selection._events.values():
            if len(event_listener.filter(filter_func)):
                return True
        return False

class Gesture:

    def __init__(
        self,
        drag,
        event,
        d,
        node,
        identifier,
        dispatch,
        subject,
        p: tuple[float, float]
    ):
        self._drag = drag
        self._event = event
        self._d = d
        self._node = node
        self._identifier = identifier
        self._dispatch = dispatch
        self._subject = subject
        self._p = p
        self._dx = subject["x"] - p[0]
        self._dy = subject["y"] - p[1]

    def gesture(self, typename: str, event: MouseEvent, touch: Event | None = None):
        p0 = self._p
        n = 0
        match typename:
            case "start":
                self._gestures[self._identifier] = self.gesture
                n = self._active
                self._active += 1
            case "end":
                self._gestures.pop(self._identifier)
                self._active -= 1
                self._p = pointer(event or event)
                n = self._active
            case "drag":
                self._p = pointer(touch or event)
                n = self._active

        self._dispatch(
            typename,
            DragEvent(
                event_type=typename,
                source_event=event,
                subject=self._subject,
                target=self._drag,
                identifier=self._identifier,
                active=n,
                x=self._p[0] + self._dx,
                y=self._p[1] + self._dy,
                dx=self._p[0] - p0[0],
                dy=self._p[1] - p0[1],
                dispatch=self._dispatch,
            ),
            self._d,
            self._node,
        )


class Drag:

    def __init__(self, extra_nodes: list[etree.Element] | None = None):
        self._extra_nodes = extra_nodes
        self._filter = argpass(default_filter)
        self._subject = argpass(default_subject)
        self._touchable = default_touchable
        self._gestures = {}
        self._listeners = dispatch("start", "drag", "end")
        self._active = 0
        self._mouse_down_x = None
        self._mouse_down_y = None
        self._mouse_moving = None
        self._touch_ending = None
        self._click_distance_2 = 0

    def __call__(self, selection: LiveSelection):
        (
            selection.on("mousedown.drag", self._mouse_downed, self._extra_nodes)
            .filter(self._touchable(selection))
            .on("touchstart.drag", self._touch_started, self._extra_nodes)
            .on("touchmove.drag", self._touch_moved, self._extra_nodes)
            .on("touchend.drag touchcancel.drag", self._touch_ended, self._extra_nodes)
            .style("touch-action", "none")
            .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)")
        )

    def _before_start(
        self,
        event: MouseEvent,
        d: T | None,
        node: etree.Element,
        identifier: str,
        touch: Event | None = None,
    ) -> Gesture | None:
        dispatch = self._listeners.copy()
        p = pointer(touch or event)
        subject = self._subject(DragEvent(
            event_type="beforestart",
            source_event=event,
            subject=None,
            target=self,
            identifier=identifier,
            active=self._active,
            x=p[0],
            y=p[1],
            dx=0,
            dy=0,
            dispatch=dispatch,
        ), d)
        return (
            None if subject is None
            else Gesture(self, event, d, node, identifier, dispatch, subject, p)
        )

    def _mouse_downed(self, event: MouseEvent, d: T | None, node: etree.Element):
        if self._touch_ending or not self._filter(event, d, node):
            return
        gesture = self._before_start(event, d, node, "mouse")
        if gesture is None:
            return
        (
            select(node) # event.view = Window ?
            .on("mousemove.drag", self._mouse_moved)
            .on("mouseup.drag", self._mouse_upped)
        )
        nodrag(node) # same question ?
        # maybe need a specific event listener to deal with this event
        # nopropagation(event)
        self._mouse_moving = False
        self._mouse_down_x = event.client_x
        self._mouse_down_y = event.client_y
        gesture("start", event)

    def _mouse_moved(self, event: MouseEvent, d: T | None, node: etree.Element):
        # noevent(event) # specific listener ?
        if not self._mouse_moving:
            dx = event.client_x - self._mouse_down_x
            dy = event.client_y - self._mouse_down_y
            self._mouse_moving = dx * dx + dy * dy > self._click_distance_2
        self._gestures["mouse"]("drag", event)

    def _mouse_upped(self, event: MouseEvent, d: T | None, node: etree.Element):
        select(node).on("mousemove.drag mouseup.drag", None) # event.view = Window ?
        yesdrag(node, self._mouse_moving) # event.view ?
        self._gestures["mouse"]("end", event)

    def _touch_started(self, event: MouseEvent, d: T | None, node: etree.Element):
        if not self._filter(event, d, node):
            return
        touches = event.changed_touches # touch event ?
        for touch in touches:
            if gesture := self._before_start(event, d, node, touch["identifier"], touch):
                # nopropagation(event) # Special event listener ?
                gesture("start", event, touch)

    def _touch_moved(self, event: MouseEvent, d: T | None, node: etree.Element):
        touches = event.changed_touches # touch event ?
        for touch in touches:
            if gesture := self._gestures.get(touch["identifier"]):
                # noevent(event) # Special event listener ?
                gesture("drag", event, touch)

    def _touch_ended(self, event: MouseEvent, d: T | None, node: etree.Element):
        touches = event.changed_touches
        if self._touch_ending:
            # clear_timeout(self._touch_ending) # Hmm timeout to clear but how ?
            pass
        # self._touch_ending = set_timeout(...)
        for touch in touches:
            if gesture := self._gestures.get(touch["identifier"]):
                # nopropagation(event) # Special event listener
                gesture("end", event, touch)

    def set_filter(self, filter_func: EventFunction[T | None, bool]) -> TDrag:
        if callable(filter_func):
            self._filter = filter_func
        else:
            self._filter = constant(filter_func)
        return self

    def set_subject(self, subject: EventFunction[T | None, T | dict[str, float]]) -> TDrag:
        if callable(subject):
            self._subject = subject
        else:
            self._subject = constant(subject)
        return self

    def set_touchable(self, touchable: Callable[[LiveSelection], EventFunction[T | None, bool]]) -> TDrag:
        if callable(touchable):
            self._touchable = touchable
        else:
            self._touchable = constant(touchable)
        return self

    def on(self, typename: str, callback: Callable[..., None]) -> TDrag:
        self._listeners.on(typename, callback)
        return self

    def set_click_distance(self, click_distance: float) -> TDrag:
        self._click_distance_2 = click_distance * click_distance
        return self

    def get_filter(self):
        return self._filter

    def get_subject(self):
        return self._subject

    def get_touchable(self):
        return self._touchable
