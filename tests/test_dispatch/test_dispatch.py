import pytest

import detroit_live as d3
from detroit_live.dispatch import Dispatch


def test_dispatch_1():
    d = d3.dispatch("foo", "bar")
    assert isinstance(d, Dispatch)


def test_dispatch_2():
    d = d3.dispatch("on")
    assert isinstance(d, Dispatch)


def test_dispatch_3():
    with pytest.raises(ValueError):
        d3.dispatch("")


def test_dispatch_4():
    with pytest.raises(ValueError):
        d3.dispatch("foo", "foo")


def test_dispatch_5():
    foo = [0]
    bar = [0]

    def f1():
        foo[0] += 1

    def f2():
        bar[0] += 1

    d = d3.dispatch("foo", "bar").on("foo", f1).on("bar", f2)
    d("foo")
    assert foo[0] == 1
    assert bar[0] == 0
    d("foo")
    d("bar")
    assert foo[0] == 2
    assert bar[0] == 1


def test_dispatch_6():
    results = []
    foo = {}
    bar = {}

    def f1(*args):
        results.append({"this": f1, "arguments": list(args)})

    d = d3.dispatch("foo").on("foo", f1)
    d("foo", foo, bar)
    assert results == [{"this": f1, "arguments": [foo, bar]}]
    d("foo", bar, foo, 42, "baz")
    assert results == [
        {"this": f1, "arguments": [foo, bar]},
        {"this": f1, "arguments": [bar, foo, 42, "baz"]},
    ]


def test_dispatch_7():
    results = []
    d = d3.dispatch("foo")

    def f1():
        results.append("A")

    def f2():
        results.append("B")

    def f3():
        results.append("C")

    def f4():
        results.append("A")

    d.on("foo.a", f1)
    d.on("foo.b", f2)
    d("foo")
    d.on("foo.c", f3)
    d.on("foo.a", f4)
    d("foo")
    assert results, ["A", "B", "B", "C", "A"]


def test_dispatch_8():
    d = d3.dispatch("foo")
    assert d("foo") is None


def test_dispatch_9():
    d = d3.dispatch("foo")

    def f():
        return

    assert d.on("foo", f) == d


def test_dispatch_10():
    foo = [0]
    bar = [0]
    d = d3.dispatch("foo", "bar")

    def f1():
        foo[0] += 1

    d.on("foo", f1)

    d("foo")
    assert foo[0] == 1
    assert bar[0] == 0

    def f2():
        bar[0] += 1

    d.on("foo", f2)
    d("foo")
    assert foo[0] == 1
    assert bar[0] == 1


def test_dispatch_11():
    foo = [0]

    def FOO():
        foo[0] += 1

    d = d3.dispatch("foo").on("foo", FOO)
    d("foo")
    assert foo[0] == 1
    d.on("foo", FOO).on("foo", FOO).on("foo", FOO)
    d("foo")
    assert foo[0] == 2


def test_dispatch_12():
    d = d3.dispatch("foo")
    foos = [0]
    bars = [0]

    def foo():
        foos[0] += 1

    def bar():
        bars[0] += 1

    assert d.on("foo.", foo) == d
    assert d.get_callback("foo.") == foo
    assert d.get_callback("foo") == foo
    assert d.on("foo.", bar) == d
    assert d.get_callback("foo.") == bar
    assert d.get_callback("foo") == bar
    assert d("foo") is None
    assert foos[0] == 0
    assert bars[0] == 1

    def noop():
        return

    assert d.on(".", noop) == d
    assert d.get_callback("foo") is bar
    assert d("foo") is None
    assert foos[0] == 0
    assert bars[0] == 2


def test_dispatch_13():
    foo = [0]

    def f1(*args):
        foo[0] += 1

    d = d3.dispatch("foo", "bar").on("foo", f1)
    d("foo")
    assert foo[0] == 1

    def noop():
        return

    d.on("foo", noop)
    d("foo")
    assert foo[0] == 1


def test_dispatch_14():
    a = [0]

    def A():
        a[0] += 1

    d = d3.dispatch("foo", "bar").on("foo", A).on("bar", A)
    d("foo")
    d("bar")

    def noop():
        return

    assert a[0] == 2
    d.on("foo", noop)
    d("bar")
    assert a[0] == 3


def test_dispatch_15():
    a = [0]
    d = d3.dispatch("foo")

    def A():
        a[0] += 1

    def noop():
        return

    d.on("foo.a", noop).on("foo", A).on("foo", noop).on("foo", noop)
    d("foo")
    assert a[0] == 0


def test_dispatch_16():
    a = [0]
    b = [0]
    c = [0]

    def noop():
        return

    def A():
        a[0] += 1
        d.on("foo.B", noop)  # remove B

    def B():
        b[0] += 1

    d = d3.dispatch("foo").on("foo.A", A).on("foo.B", B)
    d("foo")
    assert a[0] == 1
    assert b[0] == 0
    assert c[0] == 0


def test_dispatch_17():
    a = [0]
    b = [0]
    c = [0]

    def noop():
        return

    def A():
        a[0] += 1
        d.on("foo.B", C)  # replace B with C

    def B():
        b[0] += 1

    def C():
        c[0] += 1

    d = d3.dispatch("foo").on("foo.A", A).on("foo.B", B)
    d("foo")
    assert a[0] == 1
    assert b[0] == 0
    assert c[0] == 1


def test_dispatch_18():
    a = [0]
    b = [0]

    def A():
        a[0] += 1
        d.on("foo.B", B)  # add B

    def B():
        b[0] += 1

    d = d3.dispatch("foo").on("foo.A", A)
    d("foo")
    assert a[0] == 1
    assert b[0] == 1


def test_dispatch_19():
    def f():
        return

    def g():
        return

    d = d3.dispatch("f", "g").on("f", f).on("g", g)
    assert d.get_callback("f") == f
    assert d.get_callback("g") == g


def test_dispatch_20():
    foos = [0]

    def foo():
        foos[0] += 1

    d = d3.dispatch("foo", "bar").on("foo bar", foo)
    assert d.get_callback("foo") == foo
    assert d.get_callback("bar") == foo
    d("foo")
    assert foos[0] == 1
    d("bar")
    assert foos[0] == 2


def test_dispatch_21():
    foos = [0]

    def foo():
        foos[0] += 1

    d = d3.dispatch("foo").on("foo.one foo.two", foo)
    assert d.get_callback("foo.one") == foo
    assert d.get_callback("foo.two") == foo
    d("foo")
    assert foos[0] == 2


def test_dispatch_22():
    def foo():
        return

    def noop():
        return

    d = d3.dispatch("foo", "bar")
    d.on("foo", foo)
    assert d.get_callback("foo bar") == foo
    assert d.get_callback("bar foo") == foo
    d.on("foo", noop).on("bar", foo)
    assert d.get_callback("foo bar") == noop
    assert d.get_callback("bar foo") == foo


def test_dispatch_23():
    def noop():
        return

    def foo():
        return

    d = d3.dispatch("foo")
    d.on("foo.one", foo)
    assert d.get_callback("foo.one foo.two") == foo
    assert d.get_callback("foo.two foo.one") == foo
    assert d.get_callback("foo foo.one") == foo
    assert d.get_callback("foo.one foo") == foo
    d.on("foo.one", noop).on("foo.two", foo)
    assert d.get_callback("foo.one foo.two") == noop
    assert d.get_callback("foo.two foo.one") == foo
    assert d.get_callback("foo foo.two") == foo
    assert d.get_callback("foo.two foo") == foo


def test_dispatch_24():
    def noop():
        return

    def foo():
        return

    d = d3.dispatch("foo")
    d.on("foo.one", foo)
    d.on("foo.two", foo)
    d.on("foo.one foo.two", noop)
    assert d.get_callback("foo.one") == noop
    assert d.get_callback("foo.two") == noop


def test_dispatch_25():
    with pytest.raises(TypeError):
        d3.dispatch("foo").on("foo", 42)


def test_dispatch_26():
    def noop():
        return

    with pytest.raises(ValueError):
        d3.dispatch("foo").on("bar", noop)
        d3.dispatch("foo").on("__proto__", noop)


def test_dispatch_27():
    with pytest.raises(ValueError):
        d3.dispatch("foo").on("bar")
        d3.dispatch("foo").on("__proto__")


def test_dispatch_28():
    d = d3.dispatch("foo")

    def A():
        return

    def B():
        return

    def C():
        return

    d.on("foo.a", A).on("foo.b", B).on("foo", C)
    assert d.get_callback("foo.a") == A
    assert d.get_callback("foo.b") == B
    assert d.get_callback("foo") == C


def test_dispatch_29():
    def noop():
        return

    d = d3.dispatch("foo").on("foo.a", noop)
    assert d.get_callback(".a") is None


def test_dispatch_30():
    a = {}
    b = {}
    c = {}
    those = []
    d = d3.dispatch("foo", "bar")

    def A():
        those.append(a)

    def B():
        those.append(b)

    def C():
        those.append(c)

    def noop():
        return

    d.on("foo.a", A).on("bar.a", B).on("foo", C).on(".a", noop)
    d("foo")
    d("bar")
    assert those == [a, b, c]


def test_dispatch_31():
    a = {}
    b = {}
    those = []
    d = d3.dispatch("foo", "bar")

    def A():
        those.append(a)

    def B():
        those.append(b)

    d.on(".a", A).on("foo.a", B).on("bar", B)
    d("foo")
    d("bar")
    assert those == [b, b]
    assert d.get_callback(".a") is None


def test_dispatch_32():
    def foo():
        return

    def bar():
        return

    d0 = d3.dispatch("foo", "bar").on("foo", foo).on("bar", bar)
    d1 = d0.copy()
    assert d1.get_callback("foo") == foo
    assert d1.get_callback("bar") == bar

    def noop():
        return

    # Changes to d1 don’t affect d0.
    assert d1.on("bar", noop) == d1
    assert d1("bar") is None
    assert d0.get_callback("bar") == bar

    # Changes to d0 don’t affect d1.
    assert d0.on("foo", noop) == d0
    assert d0("foo") is None
    assert d1.get_callback("foo") == foo
