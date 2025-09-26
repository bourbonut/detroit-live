# Source : https://observablehq.com/@eidietrich/mt-dept-labor-industry-job-growth-projections-2018-2028?collection=@observablehq/finance-and-strategy
import json
from collections import namedtuple
from pathlib import Path

import detroit as d3
import detroit_live as d3live
import polars as pl
import requests

URL = "https://gist.githubusercontent.com/eidietrich/0047db2bfcfae1543ff37c70474587d3/raw/51bcb25225d5517c40fc8328645973183ed140e6/trimmed-for-vis.json"
Margin = namedtuple("Margin", ("top", "right", "bottom", "left"))


def load_data() -> pl.DataFrame:
    pwd = Path(__file__).resolve().parent
    data_path = pwd / "data"
    if data_path.exists():
        path = data_path / "trimmed-for-vis.csv"
        if path.exists():
            return pl.read_csv(path)
    data_path.mkdir(exist_ok=True)
    df = pl.from_dicts(json.loads(requests.get(URL).content))
    df.write_csv(data_path / "trimmed-for-vis.csv")
    return df


color_domain = [
    "Natural Resources",
    "Construction",
    "Manufacturing",
    "Trade",
    "Services",
    "Healthcare",
    "Education/Government",
]
color_range = [
    "#1b9e77",
    "#d95f02",
    "#7570b3",
    "#e7298a",
    "#66a61e",
    "#e6ab02",
    "#a6761d",
]

sector_cats = {
    "Marketing": "Services",
    "Business Management & Administration": "Services",
    "Health Science": "Healthcare",
    "Hospitality & Tourism": "Services",
    "Architecture & Construction": "Construction",
    "Transportation, Distribution & Logistics": "Trade",
    "Human Services": "Healthcare",
    "Education & Training": "Education/Government",
    "Manufacturing": "Manufacturing",
    "Finance": "Services",
    "Agriculture, Food & Natural Resources": "Natural Resources",
    "Law, Public Safety, Corrections & Security": "Services",
    "Information Technology": "Services",
    "Arts, Audio/Video Technology & Communications": "Services",
    "Government & Public Adminstration": "Education/Government",
    "Science, Technology, Engineering & Mathematics": "Services",
}

clean_ed_level = {
    "No formal educational credential": "High school diploma or less",
    "High school diploma or equivalent": "High school diploma or less",
    "Some college, post-HS training or Associate's degree": "Some college or two-year degree",
    "Bachelor's degree": "Four-year degree",
    "Master's degree": "Graduate degree",
    "Doctoral or professional degree": "Graduate degree",
}


ed_order = {value: i for i, (key, value) in enumerate(clean_ed_level.items())}
ed_order["High school diploma or less"] = 0

df: pl.DataFrame = (
    load_data()
    .with_columns(
        pl.col("sector").replace_strict(sector_cats).alias("sector_cat"),
        pl.col("ed_level").replace_strict(clean_ed_level).alias("ed_level"),
    )
    .with_columns(
        pl.col("ed_level").replace_strict(ed_order).alias("ed_level_order"),
        pl.col("Annual Openings 2018-2028").round().alias("openings"),
        (
            (pl.col("Annual Exits 2018-2028") + pl.col("Annual Transfers 2018-2028"))
            / pl.col("Total Jobs 2018")
        ).alias("turnover"),
        pl.lit(33900).alias("yRef"),
    )
    .filter((pl.col("Median Wage 2018") > 0) & (pl.col("Median Wage 2018") <= 140_000))
)

width = 600
height = 300
margin = Margin(20, 30, 30, 40)

x = d3.scale_linear(
    [0, df["turnover"].max()], [margin.left, width - margin.right]
).nice()
y = d3.scale_linear([0, 140_000], [height - margin.bottom, margin.top]).nice()

radius = d3.scale_linear([df["openings"].min(), df["openings"].max()], [3, 20])
color = d3.scale_ordinal(color_domain, color_range)

html = d3live.create("html")
style = """
.tooltip {
    position: absolute;
    display: block;
    margin: 0;
    font-size: 0.875rem;
    font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif,"Apple Color Emoji","Segoe UI Emoji","Segoe UI Symbol";
    font-weight: 400;
    word-wrap: break-word;
    background-color: white;
    border: 1px solid lightgray;
    border-radius: 4px;
    padding-block: 25px;
    padding-inline: 10px;
    box-shadow: 1px 2px 2px lightgray;
}

.grid {
    display: grid;
    grid-template-columns:auto auto;
    gap: 0px 5px;
}

.category {
    text-align: end;
    color: grey;
}
"""
(html.append("head").append("style").text(style))
body = html.append("body")

svg = (
    body.append("div")
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .attr("viewBox", [0, 0, width, height])
)

(
    svg.append("g")
    .attr("transform", f"translate(0,{height - margin.bottom})")
    .call(d3.axis_bottom(x).set_ticks(None, "%"))
    .call(lambda g: g.select(".domain").remove())
)

(
    svg.append("g")
    .attr("transform", f"translate({margin.left},0)")
    .call(d3.axis_left(y).set_ticks(width / 80, "$,~s"))
    .call(lambda g: g.select(".domain").remove())
)

svg.append("g").call(
    lambda g: (
        g.attr("stroke", "currentColor")
        .attr("stroke-opacity", 0.1)
        .call(
            lambda g: (
                g.append("g")
                .select_all("line")
                .data(x.ticks())
                .join("line")
                .attr("x1", lambda d: 0.5 + x(d))
                .attr("x2", lambda d: 0.5 + x(d))
                .attr("y1", margin.top)
                .attr("y2", height - margin.bottom)
            )
        )
        .call(
            lambda g: (
                g.append("g")
                .select_all("line")
                .data(y.ticks()[::2])
                .join("line")
                .attr("y1", lambda d: 0.5 + y(d))
                .attr("y2", lambda d: 0.5 + y(d))
                .attr("x1", margin.left)
                .attr("x2", width - margin.right)
            )
        )
    )
)

circles = (
    svg.append("g")
    .attr("fill-opacity", 0.5)
    .attr("stroke-width", 0.75)
    .select_all()
    .data(df.to_dicts())
    .enter()
    .append("circle")
    .attr("cx", lambda d: x(d["turnover"]))
    .attr("cy", lambda d: y(d["Median Wage 2018"]))
    .attr("r", lambda d: radius(d["openings"]))
    .attr("fill", lambda d: color(d["sector_cat"]))
    .attr("stroke", lambda d: color(d["sector_cat"]))
)

line = (
    svg.append("g")
    .append("line")
    .attr("x1", x.get_range()[0])
    .attr("x2", x.get_range()[1])
    .attr("y1", y(33900))
    .attr("y2", y(33900))
    .attr("stroke", "grey")
    .attr("stroke-width", 1.5)
    .attr("stroke-opacity", 0.75)
    .attr("fill", "none")
    .style("user-select", "none")
)

tooltip = body.append("div")

(tooltip.style("opacity", 0).attr("class", "tooltip"))


def mouseover(event, d, node):
    tooltip.style("opacity", 0.95)
    d3.select(node).style("stroke", "#222")


def mousemove(event, d, node):
    point = d3live.pointer(event)
    local_data = [
        "Occupation",
        d["SOCTitle"],
        "Sector",
        d["sector"],
        "Median Wage 2018",
        d3.format("$,")(d["Median Wage 2018"]),
        "Turnover",
        d3.format(".0%")(d["turnover"]),
    ]
    tooltip.select_all().remove()
    (
        tooltip.style("left", f"{point[0] + 30}px")
        .style("top", f"{point[1] + 30}px")
        .append("div")
        .attr("class", "grid")
        .select_all()
        .data(local_data)
        .enter()
        .append("span")
        .attr("class", lambda _, i: "category" if i % 2 == 0 else "")
        .text(lambda d: d)
    )


def mouseleave(event, d, node):
    tooltip.style("opacity", 0).style("left", f"{width + 30}px").style(
        "top", f"{height + 30}px"
    )

    d3.select(node).style("stroke", color(d["sector_cat"]))


(
    circles.on(
        "mouseover",
        mouseover,
        extra_nodes=tooltip.nodes(),
        html_nodes=tooltip.nodes(),
    )
    .on(
        "mousemove",
        mousemove,
        extra_nodes=tooltip.nodes(),
        html_nodes=tooltip.nodes(),
    )
    .on(
        "mouseleave",
        mouseleave,
        extra_nodes=tooltip.nodes(),
        html_nodes=tooltip.nodes(),
    )
)

html.create_app().run()
