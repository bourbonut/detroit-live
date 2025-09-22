# https://observablehq.com/@d3/quadtree-findincircle
import detroit_live as d3live
import detroit as d3
from math import hypot
from random import random

style = """
circle {
  fill: #777;
  fill-opacity: 0.1;
}

circle.visited {
  fill-opacity: 1;
  stroke-width: 2px;
}

circle.all {
  fill: orange;
  fill-opacity: 1;
  stroke: orange;
  stroke-width: 4px;
}

circle.find {
  fill: green;
  fill-opacity: 1;
  stroke: red;
  stroke-width: 5px;
}

circle.radius {
  fill: none;
}

rect {
  fill: none;
  stroke: none;
  shape-rendering: crispEdges;
}

rect.visited {
  stroke: #888;
  stroke-width: 1px;
}
"""

width = 928
height = 500
radius = 80

def materialize(quadtree):
    rects = []
    def visit(node, x0, y0, x1, y1):
        rects.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "node": node})
    quadtree.visit(visit)
    return rects

def find_in_circle(quadtree, x, y, radius, filter_func):
    result = []
    radius2 = radius * radius
    if filter_func:
        def accept(d):
            if filter_func(d):
                result.append(d)
    else:
        def accept(d):
            result.append(d)

    def visit(node, x1, y1, x2, y2):
        if isinstance(node, list):
            return x1 >= x + radius or y1 >= y + radius or x2 < x - radius or y2 < y - radius
        dx = quadtree.get_x()(node["data"]) - x
        dy = quadtree.get_y()(node["data"]) - y
        if dx * dx + dy * dy < radius2:
            while True:
                accept(node["data"])
                node = node.get("next")
                if node is None:
                    break

    quadtree.visit(visit)
    return result

def find_in_circle_mark(quadtree, x, y, radius):
    result = []

    def accept(d):
        result.append(d)

    def visit(node, x1, y1, x2, y2):
        if isinstance(node, list):
            if len(node) == 4:
                node.append({"visited": True})
            else:
                node[4]["visited"] = True

            return x1 >= x + radius or y1 >= y + radius or x2 < x - radius or y2 < y - radius

        while True:
            d = node["data"]
            d["visited"] = True
            if hypot(d["x"] - x, d["y"] - y) < radius:
                accept(d)
            node = node.get("next")
            if node is None:
                break

    quadtree.visit(visit)
    return result

data = [{"x": random() * width, "y": random() * height} for _ in range(1000)]
quadtree = d3.quadtree().x(lambda d: d["x"]).y(lambda d: d["y"]).set_extent([[-1, -1], [width + 1, height + 1]]).add_all(data)

html = d3live.create("html")
head = html.append("head").append("style").text(style)
svg = (
    html.append("body")
    .append("svg")
    .attr("viewBox", " ".join(map(str, [0, 0, width, height])))
    .style("cursor", "crosshair")
)

quad = (
    svg.select_all(".node")
    .data(materialize(quadtree))
    .enter()
    .append("rect")
    .attr("class", "node")
    .attr("x", lambda d: d["x0"])
    .attr("y", lambda d: d["y0"])
    .attr("width", lambda d: d["y1"] - d["y0"])
    .attr("height", lambda d: d["x1"] - d["x0"])
)

circle = (
    svg.select_all(".radius")
    .data([radius])
    .join("circle")
    .attr("r", lambda d: d)
    .attr("class", "radius")
    .attr("stroke", "orange")
    .attr("fill", "none")
)

point = (
    svg.select_all("circle")
    .data(data)
    .enter()
    .append("circle")
    .attr("cx", lambda d: d["x"])
    .attr("cy", lambda d: d["y"])
    .attr("r", 2)
)

def quad_each(_, d):
    node = d["node"]
    if isinstance(node, list):
        if len(node) == 4:
            node.append({"visited": False})
        else:
            node[4]["visited"] = False
    else:
        node["visited"] = False

def point_each(_, d):
    d["visited"] = False

def move(event, _, node):
    x, y = (200, 200) if event is None else d3live.pointer(event, node)

    quad.each(quad_each)
    point.each(point_each)

    one = quadtree.find(x, y, radius)
    all_ = find_in_circle_mark(quadtree, x, y, radius)

    def update_quad_class(d):
        node = d["node"]
        visited = node[4]["visited"] if isinstance(node, list) else node["visited"]
        return "node visited" if visited else "node"

    def update_point_class(d):
        return " ".join(
            (
                "visited" if d["visited"] else "",
                "all" if d in all_ else "",
                "find" if d == one else "",
            )
        ).strip()

    quad.attr("class", update_quad_class)
    point.attr("class", update_point_class)

    circle.attr("cx", x).attr("cy", y)


svg.on("mousemove click", move, extra_nodes=quad.nodes() + point.nodes() + circle.nodes()) # mousemove
move(None, None, None)

html.create_app().run()
