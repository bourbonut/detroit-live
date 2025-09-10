# https://d3-graph-gallery.com/graph/interactivity_tooltip.html#template
import detroit_live as d3live
import detroit as d3
import polars as pl
from collections import namedtuple

style = """
.tooltip {
  position: absolute;
  display: block;
  margin: 0;
  font-size: 0.875rem;
  font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif,"Apple Color Emoji","Segoe UI Emoji","Segoe UI Symbol";
  font-weight: 400;
  word-wrap: break-word;
}
"""

URL = "https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/heatmap_data.csv"
Margin = namedtuple("Margin", ("top", "right", "bottom", "left"))

margin = Margin(20, 25, 30, 40)
width = 450 - margin.left - margin.right
height = 450 - margin.top - margin.bottom

heatmap = pl.read_csv(URL)
data = heatmap.to_dicts()

groups = heatmap["group"].unique().sort().to_list()
variables = heatmap["variable"].unique().to_list()
variables = sorted(variables, key=lambda v: int(v[1:]))

html = d3live.live_create("html")
html.append("style").text(style)
body = html.append("body").append("div")

svg = (
    body
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", f"translate({margin.left},{margin.top})")
)

tooltip = body.append("div")

x = d3.scale_band().set_range([0, width]).set_domain(groups).set_padding(0.05)
(
    svg.append("g")
    .style("font-size", 15)
    .attr("transform", f"translate(0,{height})")
    .call(d3.axis_bottom(x).set_tick_size(0))
    .select(".domain")
    .remove()
)

y = d3.scale_band().set_range([height, 0]).set_domain(variables).set_padding(0.05)
(
    svg.append("g")
    .style("font-size", 15)
    .call(d3.axis_left(y).set_tick_size(0))
    .select(".domain")
    .remove()
)

color = d3.scale_sequential().set_interpolator(d3.interpolate_inferno).set_domain([1, 100])

(
    tooltip
    .style("opacity", 0)
    .attr("class", "tooltip")
    .style("background-color", "white")
    .style("border", "solid")
    .style("border-width", "2px")
    .style("border-radius", "5px")
    .style("padding", "5px")
)

def mouseover(event, d, node):
    tooltip.style("opacity", 1)
    d3.select(node).style("stroke", "black").style("opacity", 1)

def mousemove(event, d, node):
    (
        tooltip.text(f"The exact value of<br>this cell is: {d['value']}")
        .style("left", f"{event.client_x + 30}px")
        .style("top", f"{event.client_y}px")
    )

def mouseleave(event, d, node):
    tooltip.style("opacity", 0)
    (
        d3.select(node)
        .style("stroke", "none")
        .style("opacity", 0.8)
    )

def key_data(d):
    if isinstance(d, str) or d is None:
        return ""
    else:
        return f"{d['group']}:{d['variable']}"

(
    svg.select_all()
    .data(data, key_data)
    .enter()
    .append("rect")
    .attr("x", lambda d: x(d["group"]))
    .attr("y", lambda d: y(d["variable"]))
    .attr("rx", 4)
    .attr("ry", 4)
    .attr("width", x.get_bandwidth())
    .attr("height", y.get_bandwidth())
    .style("fill", lambda d: color(d["value"]))
    .style("stroke-width", 4)
    .style("stroke", "none")
    .style("opacity", 0.8)
    .on("mouseover", mouseover, extra_nodes=[tooltip.node()])
    .on("mousemove", mousemove, extra_nodes=[tooltip.node()])
    .on("mouseleave", mouseleave, extra_nodes=[tooltip.node()])
)
html.live()
