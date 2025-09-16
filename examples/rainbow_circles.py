# https://observablehq.com/@d3/drag-zoom
import detroit_live as d3live
import detroit as d3
from math import pi, sqrt, cos, sin
from operator import itemgetter

theta = pi * (3 - sqrt(5))
radius = 6
step = radius * 2
width = 928
height = 500

data = [
    {"x": width * 0.5 + radius * cos(a), "y": height * 0.5 + radius * sin(a)}
    for radius, a in ((step * sqrt(i + 0.5), theta * (i + 0.5)) for i in range(2000))
]

svg = (
    d3live.create("svg")
    .attr("width", width)
    .attr("height", height)
    .attr("viewBox", "".join(map(str, [0, 0, width, height])))
)

g = svg.append("g").attr("cursor", "grab")

def drag_started(event, d, node):
    # d3live.select(node).raise()
    g.attr("cursor", "grabbing")

def dragged(event, d, node):
    d["x"] = event.x
    d["y"] = event.y
    d3.select(node).attr("cx", event.x).attr("cy", event.y)

def drag_ended(event, d, node):
    g.attr("cursor", "grab")

(
    g.select_all("circle")
    .data(data)
    .join("circle")
    .attr("cx", itemgetter("x"))
    .attr("cy", itemgetter("y"))
    .attr("r", radius)
    .attr("fill", lambda d, i: d3.interpolate_rainbow(i / 360))
    .call(
        d3live.drag()
        .on("start", drag_started)
        .on("drag", dragged)
        .on("end", drag_ended)
    )
)

svg.create_app().run()
