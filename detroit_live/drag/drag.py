from collections.abc import Callable
from .event import DragEvent
from .nodrag import nodrag, yesdrag
from ..dispatch import dispatch
from ..live import pointer, MouseEvent
from ..selection import LiveSelection, select

def constant(x):
    def f(*args):
        return x

def default_filter(event, _):
    return not event.ctrl_key and not event.button

def default_subject(event, d):
    return {"x": event.x, "y": event.y} if d is None else d


class Gesture:

    def __init__(
        self,
        drag,
        event,
        d,
        identifier,
        dispatch,
        subject,
        p: tuple[float, float]
    ):
        self._dispatch = dispatch
        self._d = d
        self._drag = drag
        self._p = p
        self._subject = subject
        self._event = event
        self._identifier = identifier
        self._dx = subject.x - p[0]
        self._dy = subject.y - p[1]

    def gesture(self, typename: str, event: MouseEvent, touch=None):
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
                n = self._active
            case "drag":
                self._p = pointer(touch or event)
                n = self._active

        self._dispatch(
            typename,
            self,
            DragEvent(
                event_type=typename,
                source_event=event,
                subject=self._subject,
                target=self,
                identifier=self._identifier,
                active=n,
                x=self._p[0] + self._dx,
                y=self._p[1] + self._dy,
                dx=self._p[0] - p0[0],
                dy=self._p[1] - p0[1],
                dispatch=self._dispatch,
            ),
            self._d
        )


class Drag:

    def __init__(self):
        self._filter = default_filter
        self._container = self._default_container
        self._subject = default_subject
        self._touchable = self._default_touchable
        self._gestures = {}
        self._listeners = dispatch("start", "drag", "end")
        self._active = 0
        self._mouse_down_x = None
        self._mouse_down_y = None
        self._mouse_moving = None
        self._touch_ending = None
        self._click_distance_2 = 0

    def _default_container(self, *args):
        return self.parent_node

    def _default_touchable(self):
        return "ontouchstart" in self

    def __call__(self, selection: LiveSelection):
        (
            selection.on("mousedown.drag", self._mouse_downed)
            # .filter(self._default_touchable)
            # .on("touchstart.drag", self._touch_started)
            # .on("touchmove.drag", self._touch_moved)
            # .on("touchend.drag touchcancel.drag", self._touch_ended)
            .style("touch-action", "none")
            .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)")
        )

    def _before_start(self, event, d, identifier, touch=None):
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
            else Gesture(self, event, d, identifier, dispatch, subject, p)
        )

    def _mouse_downed(self, event, d, node):
        if self._touch_ended or self._filter(event, d):
            return
        gesture = self._before_start(event, d, "mouse")
        if gesture is None:
            return
        (
            select(node)
            .on("mousemove.drag", self._mouse_moved)
            .on("mouseup.drag", self._mouse_upped)
        )
        nodrag(node)
        self._mouse_moving = False
        self._mouse_down_x = event.client_x
        self._mouse_down_y = event.client_y
        gesture("start", event)

    def _mouse_moved(self, event, d, node):
        if not self._mouse_moving:
            dx = event.client_x - self._mouse_down_x
            dy = event.client_y - self._mouse_down_y
            self._mouse_moving = dx * dx + dy * dy > self._click_distance_2
        self._gestures["mouse"]("drag", event)

    def _mouse_upped(self, event, d, node):
        select(node).on("mousemove.drag mouseup.drag", None)
        yesdrag(node, self._mouse_moving)
        self._gestures["mouse"]("end", event)

    def _touch_started(self, event, d, node):
        if not self._filter(event, d):
            return
        touches = event.changed_touches
        for touch in touches:
            if gesture := self._before_start(event, d, touch["identifier"], touch):
                # nopropagation(event)
                gesture("start", event, touch)

    def _touch_moved(self, event, d, node):
        touches = event.changed_touches
        for touch in touches:
            if gesture := self._gestures.get(touch["identifier"]):
                # noevent(event)
                gesture("drag", event, touch)

    def _touch_end(self, event, d, node):
        touches = event.changed_touches
        if self._touch_ending:
            pass
            # clear_timeout(self._touch_ending)
        # self._touch_ending = set_timeout(...)
        for touch in touches:
            if gesture := self._gestures.get(touch["identifier"]):
                # nopropagation(event)
                gesture("end", event, touch)


    def set_filter(self, filter_):
        if callable(filter_):
            self._filter = filter_
        else:
            self._filter = constant(filter_)
        return self

    def set_container(self, container):
        if callable(container):
            self._container = container
        else:
            self._container = constant(container)
        return self

    def set_subject(self, subject):
        if callable(subject):
            self._subject = subject
        else:
            self._subject = constant(subject)
        return self

    def set_touchable(self, touchable):
        if callable(touchable):
            self._touchable = touchable
        else:
            self._touchable = constant(touchable)
        return self


    def on(self, typename: str, callback: Callable[..., None]):
        self._listeners.on(typename, callback)
        return self

    def set_click_distance(self, click_distance):
        self._click_distance_2 = click_distance * click_distance
        return self

    def get_filter(self):
        return self._filter

    def get_container(self):
        return self._container

    def get_subject(self):
        return self._subject

    def get_touchable(self):
        return self._touchable
