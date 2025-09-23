# For the moment, this example is not working
import detroit_live as d3live

html = d3live.create("html")
body = html.append("body")

cars = ["volvo", "saab", "mercedes", "audi"]
colors = {
    "volvo": ["blue", "red"],
    "saab": ["green", "grey"],
    "mercedes": ["blue"],
    "audi": ["white", "black"],
}

select1 = (
    body.append("select")
    .attr("name", "cars")
)

(
    select1
    .select_all()
    .data(cars)
    .enter()
    .append("option")
    .attr("value", lambda d: d)
    .text(lambda d: d)
)

select2 = (
    body.append("select")
    .attr("name", "color")
)

(
    select2
    .select_all()
    .data(colors["volvo"]) # default value
    .enter()
    .append("option")
    .attr("value", lambda d: d)
    .text(lambda d: d)
)

def foo(event, d, node):
    select1.select_all().remove()
    index = cars.index(event.value)
    options = (
        select1
        .select_all()
        .data(cars)
        .enter()
        .append("option")
        .attr("value", lambda d: d)
        .text(lambda d: d)
    )
    def each(node, _, i):
        node.set("selected", "") if i == index else None
    options.each(each)

    select2.select_all().remove()
    (
        select2
        .select_all()
        .data(colors[event.value]) # default value
        .enter()
        .append("option")
        .attr("value", lambda d: d)
        .text(lambda d: d)
    )

select1.on("change", foo, extra_nodes=[select2.node()], html_nodes=[select1.node(), select2.node()])

html.create_app().run()
