import detroit_live as d3
from detroit_live.zoom.transform import Transform
from math import inf

def test_zoom_1():
    div = d3.create("div").datum("hello")
    z = d3.zoom()
    div.call(z)
    assert d3.zoom_transform(div.node()) == Transform(1, 0, 0)
    div.call(z.transform, d3.zoom_identity.scale(2).translate(1, -3), None, None)
    assert d3.zoom_transform(div.node()) == Transform(2, 2, -6)

def test_zoom_2():
    div = d3.create("div").datum("hello")
    z = d3.zoom()
    div.call(z)
    assert d3.zoom_transform(div.node()) == Transform(1, 0, 0)
    div.call(z.translate_by, 10, 10, None)
    assert d3.zoom_transform(div.node()) == Transform(1, 10, 10)
    assert d3.zoom_transform(div.append("span").node()) == Transform(1, 10, 10)

def test_zoom_3():
    div = d3.create("div").datum("hello")
    z = d3.zoom()
    div.call(z)
    div.call(z.scale_by, 2, [0, 0], None)
    assert d3.zoom_transform(div.node()) == Transform(2, 0, 0)
    div.call(z.scale_by, 2, [2, -2], None)
    assert d3.zoom_transform(div.node()) == Transform(4, -2, 2)
    div.call(z.scale_by, 1/4, [2, -2], None)
    assert d3.zoom_transform(div.node()) == Transform(1, 1, -1)

def test_zoom_4():
    div = d3.create("div").datum("hello")
    z = d3.zoom()
    div.call(z.set_extent([[0, 0], [0, 0]]))
    div.call(z.scale_to, 2, None, None)
    assert d3.zoom_transform(div.node()) == Transform(2, 0, 0)
    div.call(z.scale_to, 2, None, None)
    assert d3.zoom_transform(div.node()) == Transform(2, 0, 0)
    div.call(z.scale_to, 1, None, None)
    assert d3.zoom_transform(div.node()) == Transform(1, 0, 0)

def test_zoom_5():
    div = d3.create("div").datum("hello")
    z = d3.zoom()
    div.call(z.set_extent([[0, 0], [0, 0]]))
    div.call(z.translate_by, 10, 10, None)
    assert d3.zoom_transform(div.node()) == Transform(1, 10, 10)
    div.call(z.scale_by, 2, None, None)
    div.call(z.translate_by, -10, -10, None)
    assert d3.zoom_transform(div.node()) == Transform(2, 0, 0)

def test_zoom_6():
    div = d3.create("div").datum("hello")
    z = d3.zoom()
    div.call(z.set_extent([[0, 0], [0, 0]]))
    a = [None]
    b = [None]
    def f1(*args):
        a[0] = list(args)
        return 2
    def f2(*args):
        b[0] = list(args)
        return [0, 0]
    div.call(z.scale_by, f1, f2, None)
    assert d3.zoom_transform(div.node()) == Transform(2, 0, 0)
    assert a[0][1] == "hello"
    assert a[0][2] == 0
    assert b[0][1] == "hello"
    assert b[0][2] == 0

def test_zoom_7():
    div = d3.create("div").datum("hello")
    z = d3.zoom()
    div.call(z.set_extent([[0, 0], [0, 0]]))
    a = [None]
    b = [None]
    def f1(*args):
        a[0] = list(args)
        return 2
    def f2(*args):
        b[0] = list(args)
        return [0, 0]
    div.call(z.scale_to, f1, f2, None)
    assert d3.zoom_transform(div.node()) == Transform(2, 0, 0)
    assert a[0][1] == "hello"
    assert a[0][2] == 0
    assert b[0][1] == "hello"
    assert b[0][2] == 0

def test_zoom_8():
    div = d3.create("div").datum("hello")
    z = d3.zoom()
    div.call(z.set_extent([[0, 0], [0, 0]]))
    a = [None]
    b = [None]
    def f1(*args):
        a[0] = list(args)
        return 2
    def f2(*args):
        b[0] = list(args)
        return 3
    div.call(z.translate_by, f1, f2, None)
    assert d3.zoom_transform(div.node()) == Transform(1, 2, 3)
    assert a[0][1] == "hello"
    assert a[0][2] == 0
    assert b[0][1] == "hello"
    assert b[0][2] == 0

def test_zoom_9():
    div = d3.create("div").datum("hello")
    z = d3.zoom()
    div.call(z.set_extent([[0, 0], [0, 0]]))
    a = [None]
    constrain = z.get_constrain()
    def f1(*args):
        a[0] = list(args)
        return constrain(*args)
    z.set_constrain(f1)
    div.call(z.translate_by, 10, 10, None)
    assert a[0][0] == Transform(1, 10, 10)
    assert a[0][1] == [[0, 0], [0, 0]]
    assert a[0][2] == [[-inf, -inf], [inf, inf]]
