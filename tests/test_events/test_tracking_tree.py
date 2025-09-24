from detroit_live.events import TrackingTree
import detroit_live as d3

def test_tracking_tree_1():
    ttree = TrackingTree()
    svg = d3.create("svg")
    circle1 = svg.append("g").append("circle")
    circle2 = svg.append("g").append("circle")
    ttree.set_root(circle1.node())
    assert ttree.root == svg.node()
    assert ttree.get_node("svg/g[1]/circle[1]") == circle1.node()
    assert ttree.get_node("svg/g[2]/circle[1]") == circle2.node()
    assert ttree.get_node("svg/g[1]/circle[2]") is None
    assert ttree.get_node("svg/g[2]/circle[2]") is None

    assert ttree.get_path(circle1.node()) == "/g[1]/circle[1]"
    assert ttree.get_path(circle2.node()) == "/g[2]/circle[1]"
    assert ttree.get_path(svg.node()) == "svg/.[1]"
