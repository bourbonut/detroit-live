from collections.abc import Callable
from .event import DragEvent
from .nodrag import nodrag, yesdrag
from ..dispatch import dispatch
from ..selection import LiveSelection, select

def constant(x):
    def f(*args):
        return x

def default_filter(event, _):
    return not event.ctrl_key and not event.button

def default_subject(event, d):
    return {"x": event.x, "y": event.y} if d is None else d

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

    def _before_start(self, container, event, d, identifier, touch):
        dispatch_copy = self._listeners.copy()
        p = event
        drag_event = DragEvent(
            event_type="beforestart",
            source_event=event,
            subject=None,
            target=self,
            identifier=identifier,
            active=self._active,
            x=p.client_x,
            y=p.client_y,
            dx=0,
            dy=0,
            dispatch=dispatch_copy
        )
        s = self._subject(drag_event, d)
        if s is None:
            return

        dx = s.x - p.client_x
        dy = s.x - p.client_y

        def gesture(typename, event, touch):
            p0 = p
            n = 0
            match typename:
                case "start":
                    self._gestures[identifier] = gesture
                    n = self._active
                    self._active += 1
                case "end":
                    self._gestures.pop(identifier)
                    self._active -= 1
                    n = self._active
                case "drag":
                    n = self._active

            drag_event = DragEvent(
                event_type=typename,
                source_event=event,
                subject=s,
                target=self,
                identifier=identifier,
                active=n,
                x=p.client_x + dx,
                y=p.client_y + dy,
                dx=p.client_x - p0.client_x,
                dy=p.client_y - p0.client_y,
                dispatch=dispatch_copy,
            )
            dispatch_copy(typename, self, drag_event, d)


    def _mouse_downed(self, event, d, node):
        if self._touch_ended or self._filter(event, d):
            return
        gesture = self._before_start(self._container(event, d), event, d, "mouse")
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
        c = self._container(event, d)

        for touch in touches:
            if gesture := self._before_start(c, event, d, touch["identifier"], touch):
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
