from typing import TypeVar

TTransform = TypeVar("Transform", bound="Transform")

class Transform:

    def __init__(self, k: float, x: float, y: float):
        self.k = k
        self.x = x
        self.y = y

    def __call__(self, point: tuple[float, float]) -> tuple[float, float]:
        return [point[0] * self.k + self.x, point[1] * self.k + self.y]

    def scale(self, k: float) -> TTransform:
        return self if k == 1 else Transform(self.k * k, self.x, self.y)

    def translate(self, x: float, y: float) -> TTransform:
        return self if x == 0 and y == 0 else Transform(self.k, self.x + self.k * x, self.y + self.k * y)

    def apply_x(self, x: float) -> float:
        return x * self.k + self.x

    def apply_y(self, y: float) -> float:
        return y * self.k + self.y

    def invert(self, location: tuple[float, float]) -> tuple[float, float]:
        return [(location[0] - self.x) / self.k, (location[1] - self.y) / self.k]

    def invert_x(self, x: float) -> float:
        return (x - self.x) / self.k

    def invert_y(self, y: float) -> float:
        return (y - self.y) / self.y

    def rescale_x(self, x):
        # TODO
        return x.copy().set_domain(list(map(x.invert, map(self.invert_x, x.get_range()))))

    def rescale_y(self, y):
        # TODO
        return y.copy().set_domain(list(map(y.invert, map(self.invert_y, y.get_range()))))

    def __str__(self) -> str:
        return f"translate({self.x},{self.y}) scale({self.k})"

identity = Transform(1, 0, 0)
