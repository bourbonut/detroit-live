from detroit_live.events.utils import get_root, to_string, xpath_to_query_selector, diffdict, inner_html, node_attribs, search
import detroit_live as d3
import pytest

def test_get_root():
    svg = d3.create("svg")
    circle = svg.append("g").append("g").append("g").append("circle")
    assert get_root(circle.node()) == svg.node()

def test_to_string():
    svg = d3.create("svg")
    circle = svg.append("g").append("g").append("g").append("circle")
    assert "circle" in to_string(svg.node())
    assert "g" in to_string(svg.node())
    assert "svg" not in to_string(circle.node())
    assert "g" not in to_string(circle.node())

@pytest.mark.parametrize(
    "path, expected",
    [
        [
            "html/body/svg/g[1]/rect[82]",
            "html body svg g:nth-of-type(1) rect:nth-of-type(82)"
        ],
        [
            "html/body/svg/g/rect[82]",
            "html body svg g rect:nth-of-type(82)"
        ],
        [
            "html/body/svg/g/rect",
            "html body svg g rect"
        ],
        [
            "html/body/svg/g/g/g/g/rect",
            "html body svg g g g g rect"
        ],
        [
            "html/body/svg/g[1]/g[2]/g[3]/g[4]/rect",
            "html body svg g:nth-of-type(1) g:nth-of-type(2)"
            " g:nth-of-type(3) g:nth-of-type(4) rect"
        ],
    ]
)
def test_xpath_to_query_selector(path, expected):
    assert xpath_to_query_selector(path) == expected

@pytest.mark.parametrize(
    "old, new, expected",
    [
        [{"a": 1}, {"b": 2}, {"remove": [["a", 1]], "change": [["b", 2]]}],
        [{"b": 1}, {"b": 2}, {"remove": [], "change": [["b", 2]]}],
        [{"a": 1}, {}, {"remove": [["a", 1]], "change": []}],
        [{}, {}, {"remove": [], "change": []}],
        [{"a": 1, "b": 2}, {"a": 1, "b": 2}, {"remove": [], "change": []}],
    ]
)
def test_diffdict(old, new, expected):
    assert diffdict(old, new) == expected

def test_inner_html():
    g = d3.create("g")
    circle = g.append("circle")
    assert "g" not in inner_html(g.node())
    assert "circle" in inner_html(g.node())
    assert "" == inner_html(circle.node())

def test_node_attribs_1():
    g = d3.create("g")
    g.attr("class", "test")
    g.attr("transform", "translate(1, 2)")

    g.append("circle").attr("cx", 10).attr("cy", 12)
    assert node_attribs(g.node()) == {"class": "test", "transform": "translate(1, 2)"}
    assert node_attribs(g.node(), True) == {
        "class": "test",
        "transform": "translate(1, 2)",
        "innerHTML": "<circle cx=\"10\" cy=\"12\"></circle>"
    }

def test_node_attribs_2():
    div = d3.create("div")
    div.attr("class", "test")
    div.attr("transform", "translate(1, 2)")

    div.text("Hello world")
    assert node_attribs(div.node()) == {"class": "test", "transform": "translate(1, 2)"}
    assert node_attribs(div.node(), True) == {
        "class": "test",
        "transform": "translate(1, 2)",
        "innerHTML": "Hello world"
    }

@pytest.mark.parametrize(
    "mapping, keys, expected",
    [
        [{"a": {"b": 1, "c": 2}, "d": {"e": 3, "f": 4}}, (None, None), [1, 2, 3, 4]],
        [{"a": {"b": 1, "c": 2}, "d": {"e": 3, "f": 4}}, (None, "b"), [1]],
        [{"a": {"b": 1, "c": 2}, "d": {"e": 3, "f": 4}}, ("a", None), [1, 2]],
        [{"a": {"b": 1, "c": 2}, "d": {"e": 3, "f": 4}}, ("a", "b"), [1]],
        [{"a": {"b": 1, "c": 2}, "d": {"b": 3, "c": 4}}, (None, "b"), [1, 3]],
    ]
)
def test_search(mapping, keys, expected):
    assert list(search(mapping, keys)) == expected
