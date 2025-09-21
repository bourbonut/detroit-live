from collections.abc import Callable
from detroit.types import Accessor, EtreeFunction
from detroit.interpolate import interpolate_zoom
from lxml import etree
import warnings
from math import hypot, sqrt, inf, nan
from typing import TypeVar
from ..events import pointer, MouseEvent, WheelEvent, Event
from ..selection import select, LiveSelection
from ..types import T, Extent, EventFunction
from ..dispatch import Dispatch, dispatch
from .transform import Transform, identity
from .zoom_state import _zoom_state
from .zoom_event import ZoomEvent
from .noevent import noevent

TGesture = TypeVar("Gesture", bound="Gesture")
TZoom = TypeVar("Zoom", bound="Zoom")

def constant(x):
    def f(*args):
        return x
    return f

def default_filter(event: MouseEvent | WheelEvent, d: T | None, node: etree.Element) -> bool:
    return (not event.ctrl_key or isinstance(event, WheelEvent)) and not event.button

def default_extent(node: etree.Element) -> Extent:
    if node.tag == "svg":
        attrib = dict(node.attrib)
        if view_box := attrib.get("viewBox"):
            values = list(map(float, view_box.split(", ")))
            if len(values) == 4: # valid viewBox
                x, y, width, height = values
                return [[x, y], [width, height]]
            warnings.warn(
                f"Invalid 'viewBox' attribute, found {view_box}."
                " It should have the form of '<x>, <y>, <width>, <height>'",
                category=UserWarning,
            )
        if "width" in attrib and "height" in attrib:
            width = float(attrib["width"])
            height = float(attrib["height"])
            return [[0, 0], [width, height]]
    # Default arbitrary values
    return [[0, 0], [928, 500]]

def default_transform(node: etree.Element) -> Transform:
    _zoom_state.set_zoom(node, _zoom_state.get_zoom(node) or identity)

def default_wheel_delta(event: WheelEvent) -> float:
    k = 0.002
    if event.delta_mode == 1:
        k = 0.05
    elif event.delta_mode:
        k = 1
    return -event.delta_y * k * (10 if event.ctrl_key else 1)

def default_touchable(selection: LiveSelection) -> Accessor[T, bool]:
    def touchable(d: T, i: int, group: list[etree.Element]) -> bool:
        target = group[i]
        for event_listener in selection._events.values():
            if len(event_listener.search(target, "touchstart")):
                return True
        return False
    return touchable

def default_constrain(transform: Transform, extent: Extent, translate_extent: Extent) -> Transform:
    dx0 = transform.invert_x(extent[0][0]) - translate_extent[0][0]
    dx1 = transform.invert_x(extent[1][0]) - translate_extent[1][0]
    dy0 = transform.invert_x(extent[0][1]) - translate_extent[0][1]
    dy1 = transform.invert_x(extent[1][1]) - translate_extent[1][1]
    return transform.translate(
        (dx0 + dx1) * 0.5 if dx1 > dx0 else min(0, dx0) or max(0, dx1),
        (dy0 + dy1) * 0.5 if dy1 > dy0 else min(0, dy0) or max(0, dy1),
    )

def centroid(extent: Extent) -> tuple[float, float]:
    return [(extent[0][0] + extent[1][0]) * 0.5, (extent[0][1] + extent[1][1]) * 0.5]

class Gesture:

    _shared = _zoom_state

    def __init__(
        self,
        zoom: TZoom,
        node: etree.Element,
        extent: Callable[[etree.Element], Extent],
        listeners: Dispatch,
    ):
        self._zoom = zoom
        self._node = node
        self._active = 0
        self._source_event = None
        self._taps = 0
        self._listeners = listeners
        self.extent = extent(node)

        self.mouse = None
        self.wheel = None
        self.moved = False
        self.touch0 = None
        self.touch1 = None

    def event(self, event: Event):
        if event:
            self._source_event = event
        return self

    def start(self):
        self._active += 1
        if self._active == 1:
            self._shared.set_zooming(self._node, self)
            self.emit("start")
        return self

    def zoom(self, key, transform):
        if self.mouse and key != "mouse":
            self.mouse[1] = transform.invert(self.mouse[0])
        if self.touch0 and key != "touch":
            self.touch0[1] = transform.invert(self.touch0[0])
        if self.touch1 and key != "touch":
            self.touch1[1] = transform.invert(self.touch1[0])
        self._shared.set_zoom(self._node, transform)
        self.emit("zoom")
        return self

    def end(self):
        self._active -= 1
        if self._active == 0:
            self._shared.remove_zooming(self._node)
            self.emit("end")
        return self

    def emit(self, event_type):
        selection = select(self._node)
        d = selection._data.get(self._node)
        self._listeners(
            event_type,
            ZoomEvent(
                event_type,
                self._source_event,
                self._zoom,
                self._shared.get_zoom(self._node),
                self._listeners,
            ),
            d,
            self._node,
        )

class Zoom:
    _shared = _zoom_state

    def __init__(self, extra_nodes: list[etree.Element] | None = None):
        self._extra_nodes = extra_nodes
        self._filter = default_filter
        self._extent = default_extent
        self._constrain = default_constrain
        self._wheel_delta = default_wheel_delta
        self._touchable = default_touchable
        self._scale_extent = [0, inf]
        self._translate_extent = [[-inf, -inf], [inf, inf]]
        self._duration = 250
        self._interpolate = interpolate_zoom
        self._listeners = dispatch("start", "zoom", "end")
        self._touch_starting = None
        self._touch_first = None
        self._touch_ending = None
        self._touch_delay = 500
        self._wheel_delay = 150
        self._click_distance2 = 0
        self._tap_distance = 10

        self._x0 = nan
        self._y0 = nan
        self._g = None
        self._v = None

    def __call__(self, selection: LiveSelection):
        selection.each(default_transform)
        (
            selection
            .on("wheel.zoom", self._wheeled, extra_nodes=self._extra_nodes)
            .on("mousedown.zoom", self._mouse_downed, extra_nodes=self._extra_nodes)
            .on("mousemove.zoom", self._mouse_moved, extra_nodes=self._extra_nodes, active=False)
            .on("mouseup.zoom", self._mouse_upped, extra_nodes=self._extra_nodes, active=False)
            .on("dblclick.zoom", self._dbl_clicked, extra_nodes=self._extra_nodes)
            .filter(self._touchable)
            .on("touchstart.zoom", self._touch_started, extra_nodes=self._extra_nodes)
            .on("touchmove.zoom", self._touch_moved, extra_nodes=self._extra_nodes)
            .on("touchend.zoom touchcancel.zoom", self._touch_ended, extra_nodes=self._extra_nodes)
            .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)")
        )

    def transform(
        self,
        collection: LiveSelection,
        transform: EtreeFunction[T, Transform] | Transform,
        point: tuple[float, float],
        event: Event,
    ):
        selection = collection.selection() if hasattr(collection, "selection") else collection
        selection.each(default_transform)
        if collection != selection:
            self._schedule(collection, transform, point, event)
        else:
            def each_func(node: etree.Element, d: T, i: int, group: list[etree.Element]):
                (
                    self._gesture(node)
                    .event(event)
                    .start()
                    .zoom(None, transform if isinstance(transform, Transform) else transform(node, d, i, group))
                    .end()
                )
            # selection.interrupt
            selection.each(each_func)

    def scale_by(
        self,
        selection: LiveSelection,
        k: EtreeFunction[T, float] | float,
        p: tuple[float, float],
        event: Event,
    ):
        def kfunc(
            node: etree.Element,
            d: T,
            i: int,
            group: list[etree.Element]
        ) -> float:
            k0 = self._shared.get_zoom(node).k
            k1 = k(node, d, i, group) if callable(k) else k
            return k0 * k1
        self.scale_to(selection, kfunc, p, event)

    def scale_to(
        self,
        selection: LiveSelection,
        k: EtreeFunction[T, float],
        p: EtreeFunction[T, tuple[float, float]] | tuple[float, float] | None,
        event: Event,
    ):
        def transform(
            node: etree.Element,
            d: T,
            i: int,
            group: list[etree.Element],
        ) -> Transform:
            e = self._extent(node)
            t0 = self._shared.get_zoom(node)
            p0 = p
            if p is None:
                p0 = centroid(e)
            elif callable(p):
                p0 = p(node, d, i, group)
            p1 = t0.invert(p0)
            k1 = k(node, d, i, group) if callable(k) else k
            return self._constrain(self._translate(self._scale(t0, k1), p0, p1), e, self._translate_extent)
        self.transform(selection, transform, p, event)

    def transform_by(
        self,
        selection: LiveSelection,
        x: EtreeFunction[T, float] | float,
        y: EtreeFunction[T, float] | float,
        event: Event,
    ):
        def transform(
            node: etree.Element,
            d: T,
            i: int,
            group: list[etree.Element],
        ) -> Transform:
            return self._constrain(
                self._zoom[node].translate(
                    x(node, d, i, group) if callable(x) else x,
                    y(node, d, i, group) if callable(y) else y,
                ),
                self._extent(node),
                self._translate_extent,
            )
        self.transform(selection, transform, None, event)

    def translate_to(
        self,
        selection: LiveSelection,
        x: EtreeFunction[T, float],
        y: EtreeFunction[T, float],
        p: EtreeFunction[T, tuple[float, float]] | tuple[float, float] | None,
        event: Event,
    ):
        def transform(
            node: etree.Element,
            d: T,
            i: int,
            group: list[etree.Element],
        ) -> Transform:
            e = self._extent(node, d, i, group)
            t = self._shared.get_zoom(node)
            p0 = p
            if p is None:
                p0 = centroid(e)
            elif callable(p):
                p0 = p(node, d, i, group)
            return self._constrain(identity.translate(p0[0], p0[1]).scale(t.k).translate(
                -x(node, d, i, group) if callable(x) else -x,
                -y(node, d, i, group) if callable(y) else -y,
            ), e, self._translate_extent)
        self.transform(selection, transform, p, event)

    def _scale(
        self,
        transform: Transform,
        k: float,
    ) -> Transform:
        k = max(self._scale_extent[0], min(self._scale_extent[1], k))
        if k == transform.k:
            return transform
        else:
            return Transform(k, transform.x, transform.y)

    def _translate(
        self,
        transform: Transform,
        p0: tuple[float, float],
        p1: tuple[float, float],
    ) -> Transform:
        x = p0[0] - p1[0] * transform.k
        y = p0[1] - p1[1] * transform.k
        if x == transform.x and y == transform.y:
            return transform
        else:
            return Transform(transform.k, x, y)


    def _schedule(transition, transform, point, event):
        # TODO
        pass

    def _gesture(
        self,
        node: etree.Element,
        clean: bool = False
    ) -> Gesture:
        return (
            None if clean else self._shared.get_zooming(node)
        ) or Gesture(
            self,
            node,
            self._extent,
            self._listeners,
        )

    def _wheeled(self, event: WheelEvent, d: T | None, node: etree.Element):
        if not self._filter(event, d, node):
            return
        g = self._gesture(node).event(event)
        t = self._shared.get_zoom(node)
        k = max(self._scale_extent[0], min(self._scale_extent[1], t.k * pow(2, self._wheel_delta(event))))
        p = pointer(event)

        if g.wheel:
            if g.mouse[0][0] != p[0] or g.mouse[0][1] != p[1]:
                g.mouse[0] = p
                g.mouse[1] = t.invert(p)
            # clearTimeout(g.wheel)
        elif t.k == k:
            return
        else:
            g.mouse = [p, t.invert(p)]
            # interrupt(node)
            g.start()

        noevent(event, d, node)
        # def wheel_idled():
        #     ._wheel = None
        #     g.end()
        # g.wheel = setTimeout(wheel_idled, self._wheel_delay)
        g.zoom(
            "mouse",
            self._constrain(
                self._translate(
                    self._scale(t, k),
                    g.mouse[0],
                    g.mouse[1],
                ),
                g.extent,
                self._translate_extent
            ),
        )

    def _mouse_downed(self, event: MouseEvent, d: T | None, node: etree.Element):
        if self._touch_ending or not self._filter(event, d, node):
            return
        self._g = g = self._gesture(node, clean=True).event(event)
        self._v = (
            select(node)
            .set_event("mousemove.zoom mouseup.zoom", True)
        )
        p = pointer(event)
        self._x0 = event.client_x
        self._y0 = event.client_y

        g.mouse = [p, self._shared.get_zoom(node).invert(p)]
        # interrupt(node)
        g.start()

    def _mouse_moved(self, event: MouseEvent, d: T | None, node: etree.Element):
        noevent(event, d, node)
        g = self._g
        if not g.moved:
            dx = event.client_x - self._x0
            dy = event.client_y - self._y0
            g.moved = dx * dx + dy * dy > self._click_distance2

        g.mouse[0] = pointer(event)
        g.event(event).zoom(
            "mouse",
            self._constrain(
                self._translate(
                    self._shared.get_zoom(g._node),
                    g.mouse[0],
                    g.mouse[1]
                ),
                g.extent,
                self._translate_extent,
            )
        )

    def _mouse_upped(self, event: MouseEvent, d: T | None, node: etree.Element):
        g = self._g
        v = self._v
        v.set_event("mousemove.zoom mouseup.zoom", False)
        noevent(event, d, node)
        g.event(event).end()

    def _dbl_clicked(self, event: MouseEvent, d: T | None, node: etree.Element):
        if not self._filter(event, d, node):
            return
        t0 = self._shared.get_zoom(node)
        p0 = pointer(event.changed_touches[0] if hasattr(event, "changed_touches") else event)
        p1 = t0.invert(p0)
        k1 = t0.k * (0.5 if event.shift_key else 2)
        t1 = self._constrain(self._translate(self._scale(t0, k1), p0, p1), self._extent(node), self._translate_extent)

        noevent(event, d, node)
        # Transition not supported for the moment
        # if self._duration > 0:
        #     select(node).transition().duration(duration).call(self._schedule, t1, p0, event)
        # else:
        select(node).call(self.transform, t1, p0, event)

    def _touch_started(self, event: Event, d: T | None, node: etree.Element):
        if not self._filter(event, d, node):
            return
        touches = event.touches
        n = len(touches)
        g = self._gesture(node, len(event.changed_touches) == n).event(event)

        started = False
        for touch in touches:
            p = pointer(touch)
            p = [p, self._shared.get_zoom(node).invert(p), touch.identifier]
            if not g.touch0:
                g.touch0 = p
                started = True
                g.taps = 1 + bool(self._touch_starting)
            elif not g.touch1 and g.touch0[2] != p[2]:
                g.touch1 = p
                g.taps = 0

            # if self._touch_starting:
            #     self._touch_starting = clearTimeout(self._touch_starting)

            if started:
                if g.taps < 2:
                    self._touch_first = p[0]
                    # def timeout():
                    #     self._touch_starting = None
                    # self._touch_starting = setTimeout(timeout, self._touch_delay)
                # interrupt(node)
                g.start()

    def _touch_moved(self, event: Event, d: T | None, node: etree.Element):
        if not self._shared.get_zooming(node):
            return
        g = self._gesture(node).event(event)
        touches = event.changed_touches

        for touch in touches:
            p = pointer(touch)
            if g.touch0 and g.touch0[2] == touch.identifier:
                g.touch0[0] = p
            elif g.touch1 and g.touch1 == touch.identifier:
                g.touch1[0] = p

        t = self._shared.get_zoom(g.node)
        if g.touch1:
            p0 = g.touch0[0]
            l0 = g.touch0[1]
            p1 = g.touch1[0]
            l1 = g.touch1[1]
            dpx = p1[0] - p0[0]
            dpy = p1[1] - p1[1]
            dp = dpx * dpx + dpy * dpy
            dlx = l1[0] - l0[0]
            dly = l1[1] - l0[1]
            dl = dlx * dlx + dly * dly
            t = self._scale(t, sqrt(dp / dl))
            p = [(p0[0] + p1[0]) * 0.5, (p0[1] + p1[1]) * 0.5]
            l = [(l0[0] + l1[0]) * 0.5, (l0[1] + l1[1]) * 0.5]
        elif g.touch0:
            p = g.touch0[0]
            l = g.touch0[1]
        else:
            return

        g.zoom(
            "touch",
            self._constrain(
                self._translate(t, p, l),
                g.extent,
                self._translate_extent
            )
        )

    def _touch_ended(self, event: Event, d: T | None, node: etree.Element):
        if not self._shared.get_zooming(node):
            return

        g = self._gesture(node).event(event)
        touches = event.changed_touches

        # if self._touch_ending:
        #     clearTimeout(self._touch_ending)
        # def timeout():
        #     self._touch_ending = None
        # self._touch_ending = setTimeout(timeout, self._touch_delay)
        for touch in touches:
            if g.touch0 and g.touch0[2] == touch.identifier:
                del g.touch0
            elif g.touch1 and g.touch1[2] == touch.identifier:
                del g.touch1
        if g.touch1 and not g.touch0:
            g.touch0 = g.touch1
            del g.touch1
        if g.touch0:
            g.touch0[1] = self._shared.get_zoom(node).invert(g.touch0[0])
        else:
            g.end()
            if g.taps == 2:
                t = pointer(touches[-1])
                if hypot(self._touch_first[0] - t[0], self._touch_first[1] - t[1]) < self._tap_distance:
                    p = select(node).on("dblclick.zoom")
                    if p:
                        p(event, d, node)

    def on(self, typename: str, callback: Callable[..., None]) -> TZoom:
        self._listeners.on(typename, callback)
        return self

    def set_wheel_delta(self, wheel_delta: Callable[[Event], float] | float) -> TZoom:
        if callable(wheel_delta):
            self._wheel_delta = wheel_delta
        else:
            self._wheel_delta = constant(wheel_delta)
        return self

    def set_filter(self, filter_func: EventFunction[T | None, bool] | bool) -> TZoom:
        if callable(filter_func):
            self._filter = filter_func
        else:
            self._filter = constant(filter_func)
        return self

    def set_touchable(self, touchable: Callable[[LiveSelection], EventFunction[T | None, bool]] | Callable[..., bool]) -> TZoom:
        if callable(touchable(None)):
            self._touchable = touchable
        else:
            def lambda_touchable(
                selection: LiveSelection,
            ) -> EventFunction[T | None, bool]:
                return constant(touchable(selection))
            self._touchable = lambda_touchable
        return self

    def set_extent(self, extent: Callable[[etree.Element], Extent] | Extent) -> TZoom:
        if callable(extent):
            self._extent = extent
        else:
            self._extent = constant(extent)
        return self

    def set_scale_extent(self, scale_extent: tuple[float, float]) -> TZoom:
        self._scale_extent[0] = scale_extent[0]
        self._scale_extent[1] = scale_extent[1]
        return self

    def set_translate_extent(self, translate_extent: Extent) -> TZoom:
        self._translate_extent[0][0] = translate_extent[0][0]
        self._translate_extent[1][0] = translate_extent[1][0]
        self._translate_extent[0][1] = translate_extent[0][1]
        self._translate_extent[1][1] = translate_extent[1][1]
        return self

    def set_constrain(self, constrain: Callable[[Transform, Extent, Extent], Transform]) -> TZoom:
        self._constrain = constrain
        return self

    def set_duration(self, duration: int | float) -> TZoom:
        self._duration = duration
        return self

    def set_interpolate(self, interpolation: Callable[[float, float], Callable[[float], float]]) -> TZoom:
        self._interpolate = interpolation
        return self

    def set_click_distance(self, click_distance: int | float) -> TZoom:
        self._click_distance2 = click_distance * click_distance
        return self

    def set_tap_distance(self, tap_distance: int | float) -> TZoom:
        self._tap_distance = tap_distance
        return self

    def get_wheel_delta(self) -> Callable[[Event], float]:
        return self._wheel_delta

    def get_filter(self) -> EventFunction[T | None, bool]:
        return self._filter

    def get_touchable(self) -> Callable[[LiveSelection], EventFunction[T | None, bool]]:
        return self._touchable

    def get_extent(self) -> Callable[[etree.Element], Extent]:
        return self._extent

    def get_scale_extent(self) -> tuple[float, float]:
        return [self._scale_extent[0], self._scale_extent[1]]

    def get_translate_extent(self) -> tuple[float, float]:
        return [
            [self._translate_extent[0][0], self._translate_extent[0][1]],
            [self._translate_extent[1][0], self._translate_extent[1][1]]
        ]

    def get_constrain(self) -> Callable[[Transform, Extent, Extent], Transform]:
        return self._constrain

    def get_duration(self) -> float:
        return self._duration

    def get_interpolation(self) -> Callable[[float, float], Callable[[float], float]]:
        return self._interpolate

    def get_click_distance(self) -> float:
        return sqrt(self._click_distance2)

    def get_tap_distance(self) -> float:
        return self._tap_distance
