import pytest

import detroit_live as d3
from detroit_live.events.types import MouseEvent, WheelEvent


def test_pointer_1():
    assert d3.pointer(
        MouseEvent(
            10,
            10,
            20,
            20,
            30,
            30,
            0,
            False,
            False,
            False,
            "svg",
            8,
            8,
        )
    ) == (30, 30)


def test_pointer_2():
    assert d3.pointer(
        WheelEvent(
            10,
            10,
            20,
            20,
            0,
            False,
            0,
            8,
            8,
        )
    ) == (10, 10)


@pytest.mark.parametrize(
    "transform, expected",
    [
        ["translate(10, 20)", (10.0, 0.0)],
        ["scale(10)", (2.0, 2.0)],
        ["translate(10, 20) scale(10)", (1.0, 0.0)],
        ["translate(10.5, -20.5)", (20 - 10.5, 20 + 20.5)],
        ["scale(-2.5)", (20 / -2.5, 20 / -2.5)],
        [
            "translate(10.5, -20.5) scale(-2.5)",
            ((20 - 10.5) / -2.5, (20 + 20.5) / -2.5),
        ],
    ],
)
def test_pointer_3(transform, expected):
    g = d3.create("g").attr("transform", transform)
    assert (
        d3.pointer(
            MouseEvent(
                10,
                10,
                20,
                20,
                30,
                30,
                0,
                False,
                False,
                False,
                "svg",
                8,
                8,
            ),
            g.node(),
        )
        == expected
    )
