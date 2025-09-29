from collections.abc import Callable
from typing import TypeVar

from detroit.array import argpass
from detroit.types import Accessor
from lxml import etree

from ..dispatch import Dispatch, dispatch
from ..events import Event, MouseEvent, pointer
from ..selection import LiveSelection, select
from ..types import EventFunction, T
from .drag_event import DragEvent
from .noevent import noevent

TDrag = TypeVar("Drag", bound="Drag")


def constant(x):
    def f(*args):
        return x


def default_filter(event: MouseEvent, d: T | None, node: etree.Element) -> bool:
    return not event.ctrl_key and not event.button


def default_subject(event: DragEvent, d: T | None) -> T | dict[str, float]:
    return {"x": event.x, "y": event.y} if d is None else d


def default_container(
    event: MouseEvent, d: T | None, node: etree.Element
) -> etree.Element:
    return node.getparent()


def default_touchable(selection: LiveSelection) -> Accessor[T, bool]:
    def touchable(d: T, i: int, group: list[etree.Element]) -> bool:
        target = group[i]
        for event_listener in selection.event_listeners.values():
            if len(event_listener.search(target, "touchstart")):
                return True
        return False

    return touchable


class Gesture:
    def __init__(
        self,
        drag: TDrag,
        event: MouseEvent,
        d: T,
        node: etree.Element,
        identifier: str,
        dispatch: Dispatch,
        subject: T | dict[str, float],
        p: tuple[float, float],
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

    def __call__(self, typename: str, event: MouseEvent, touch: Event | None = None):
        p0 = self._p
        p, n = self._drag._update_from_gesture(
            typename,
            event,
            self.__call__,
            self._identifier,
            touch,
        )
        self._p = p or self._p
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
    """
    Creates a new drag behavior. The returned behavior, drag, is both an object
    and a function, and is typically applied to selected elements via
    :code:`Selection.call`.

    Parameters
    ----------
    extra_nodes: list[etree.Element] | None
        Extra nodes to update when the listener is called
    """

    def __init__(self, extra_nodes: list[etree.Element] | None = None):
        self._extra_nodes = extra_nodes
        self._filter = argpass(default_filter)
        self._container = argpass(default_container)
        self._subject = argpass(default_subject)
        self._touchable = default_touchable
        self._gestures = {}
        self._listeners = dispatch("start", "drag", "end")
        self._container_element = None
        self._active = 0
        self._mouse_down_x = 0
        self._mouse_down_y = 0
        self._mouse_moving = False
        self._touch_ending = None
        self._click_distance_2 = 0

    def __call__(self, selection: LiveSelection):
        """
        Applies this drag behavior to the specified selection. This function is
        typically not invoked directly, and is instead invoked via
        :code:`Selection.call`.

        Parameters
        ----------
        selection : LiveSelection
            Selection
        """
        (
            selection.on("mousedown.drag", self._mouse_downed, self._extra_nodes)
            .on("mousemove.drag", self._mouse_moved, self._extra_nodes, active=False)
            .on("dragstart.drag", noevent, self._extra_nodes, active=False)
            .on("mouseup.drag", self._mouse_upped, self._extra_nodes, active=False)
            .filter(self._touchable(selection))
            .on("touchstart.drag", self._touch_started, self._extra_nodes)
            .on("touchmove.drag", self._touch_moved, self._extra_nodes)
            .on("touchend.drag touchcancel.drag", self._touch_ended, self._extra_nodes)
            .style("touch-action", "none")
            .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)")
        )

    def _update_from_gesture(
        self,
        typename: str,
        event: MouseEvent,
        gesture: Callable[[str, MouseEvent, Event | None], None],
        identifier: str,
        touch: Event | None = None,
    ):
        p = None
        n = 0
        match typename:
            case "start":
                self._gestures[identifier] = gesture
                n = self._active
                self._active += 1
            case "end":
                self._gestures.pop(identifier)
                self._active -= 1
                p = pointer(touch or event, self._container_element)
                n = self._active
            case "drag":
                p = pointer(touch or event, self._container_element)
                n = self._active
        return p, n

    def _before_start(
        self,
        container: etree.Element,
        event: MouseEvent,
        d: T | None,
        node: etree.Element,
        identifier: str,
        touch: Event | None = None,
    ) -> Gesture | None:
        dispatch = self._listeners.copy()
        self._container_element = container
        p = pointer(touch or event, container)
        subject = self._subject(
            DragEvent(
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
            ),
            d,
        )
        return (
            None
            if subject is None
            else Gesture(self, event, d, node, identifier, dispatch, subject, p)
        )

    def _mouse_downed(self, event: MouseEvent, d: T | None, node: etree.Element):
        if self._touch_ending or not self._filter(event, d, node):
            return
        gesture = self._before_start(
            self._container(event, d, node), event, d, node, "mouse"
        )
        if gesture is None:
            return
        select(node).set_event("mousemove.drag mouseup.drag dragstart.drag", True)
        self._mouse_moving = False
        self._mouse_down_x = event.client_x
        self._mouse_down_y = event.client_y
        gesture("start", event)

    def _mouse_moved(self, event: MouseEvent, d: T | None, node: etree.Element):
        if not self._mouse_moving:
            dx = event.client_x - self._mouse_down_x
            dy = event.client_y - self._mouse_down_y
            self._mouse_moving = dx * dx + dy * dy > self._click_distance_2
        self._gestures["mouse"]("drag", event)

    def _mouse_upped(self, event: MouseEvent, d: T | None, node: etree.Element):
        select(node).set_event("mousemove.drag mouseup.drag dragstart.drag", False)
        self._gestures["mouse"]("end", event)

    def _touch_started(self, event: MouseEvent, d: T | None, node: etree.Element):
        if not self._filter(event, d, node):
            return
        touches = event.changed_touches  # touch event ?
        c = self._container(event, d, node)
        for touch in touches:
            if gesture := self._before_start(
                c, event, d, node, touch["identifier"], touch
            ):
                gesture("start", event, touch)

    def _touch_moved(self, event: MouseEvent, d: T | None, node: etree.Element):
        touches = event.changed_touches  # touch event ?
        for touch in touches:
            if gesture := self._gestures.get(touch["identifier"]):
                gesture("drag", event, touch)

    def _touch_ended(self, event: MouseEvent, d: T | None, node: etree.Element):
        touches = event.changed_touches
        if self._touch_ending:
            # clear_timeout(self._touch_ending) # Hmm timeout to clear but how ?
            pass
        # self._touch_ending = set_timeout(...)
        for touch in touches:
            if gesture := self._gestures.get(touch["identifier"]):
                gesture("end", event, touch)

    def set_filter(self, filter_func: EventFunction[T | None, bool]) -> TDrag:
        """
        Sets the event filter to the specified function and returns the drag
        behavior.

        If the filter returns false, the initiating event is ignored and no
        drag gestures are started. Thus, the filter determines which input
        events are ignored; the default filter ignores mousedown events on
        secondary buttons, since those buttons are typically intended for other
        purposes, such as the context menu.

        Parameters
        ----------
        filter_func : EventFunction[T | None, bool]
            Filter function

        Returns
        -------
        Drag
            Itself
        """
        if callable(filter_func):
            self._filter = filter_func
        else:
            self._filter = constant(filter_func)
        return self

    def set_subject(
        self, subject: EventFunction[T | None, T | dict[str, float]]
    ) -> TDrag:
        """
        Sets the subject accessor to the specified object or function and
        returns the drag behavior.

        The subject of a drag gesture represents the thing being dragged. It is
        computed when an initiating input event is received, such as a
        mousedown or touchstart, immediately before the drag gesture starts.
        The subject is then exposed as event.subject on subsequent drag events
        for this gesture.

        Parameters
        ----------
        subject : EventFunction[T | None, T | dict[str, float]]
            Subject function

        Returns
        -------
        Drag
            Itself
        """
        if callable(subject):
            self._subject = subject
        else:
            self._subject = constant(subject)
        return self

    def set_touchable(
        self, touchable: Callable[[LiveSelection], EventFunction[T | None, bool]]
    ) -> TDrag:
        """
        Sets the touch support detector to the specified function and returns
        the drag behavior.

        Parameters
        ----------
        touchable : Callable[[LiveSelection], EventFunction[T | None, bool]]
            Touchable function

        Returns
        -------
        Drag
            Itself
        """
        if callable(touchable):
            self._touchable = touchable
        else:
            self._touchable = constant(touchable)
        return self

    def on(self, typenames: str, callback: Callable[..., None]) -> TDrag:
        """
        If listener is specified, sets the event listener for the specified
        typenames and returns the drag behavior. If an event listener was
        already registered for the same type and name, the existing listener is
        removed before the new listener is added. If listener is null, removes
        the current event listeners for the specified typenames, if any. If
        listener is not specified, returns the first currently-assigned
        listener matching the specified typenames, if any. When a specified
        event is dispatched, each listener will be invoked with the same
        context and arguments as selection.on listeners: the current event
        (event) and datum d, with the this context as the current DOM element.

        The typenames is a string containing one or more typename separated by
        whitespace. Each typename is a type, optionally followed by a period
        (.) and a name, such as drag.foo and drag.bar; the name allows multiple
        listeners to be registered for the same type. The type must be one of
        the following:

        - :code:`"start"` - after a new pointer becomes active (on mousedown or
          touchstart).
        - :code:`"drag"` - after an active pointer moves (on mousemove or
          touchmove).
        - :code:`"end"` - after an active pointer becomes inactive (on mouseup,
          touchend or touchcancel).


        Changes to registered listeners via drag.on during a drag gesture do
        not affect the current drag gesture. Instead, you must use event.on,
        which also allows you to register temporary event listeners for the
        current drag gesture. Separate events are dispatched for each active
        pointer during a drag gesture. For example, if simultaneously dragging
        multiple subjects with multiple fingers, a start event is dispatched
        for each finger, even if both fingers start touching simultaneously.
        See Drag Events for more.

        Parameters
        ----------
        typenames : str
            Typenames
        callback : Callable[..., None]
            Callback

        Returns
        -------
        Drag
            Itself
        """
        self._listeners.on(typenames, callback)
        return self

    def set_click_distance(self, click_distance: float) -> TDrag:
        """
        Sets the maximum distance that the mouse can move between mousedown and
        mouseup that will trigger a subsequent click event. If at any point
        between mousedown and mouseup the mouse is greater than or equal to
        distance from its position on mousedown, the click event following
        mouseup will be suppressed.

        Parameters
        ----------
        click_distance : float
            Click distance value

        Returns
        -------
        Drag
            Itself
        """
        self._click_distance_2 = click_distance * click_distance
        return self

    def get_filter(self):
        return self._filter

    def get_subject(self):
        return self._subject

    def get_touchable(self):
        return self._touchable
