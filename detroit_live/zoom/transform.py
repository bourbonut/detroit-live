from typing import Any, TypeVar

TTransform = TypeVar("Transform", bound="Transform")


class Transform:
    """
    Transform object with scale :code:`k` and translation :code:`(x, y)`

    Parameters
    ----------
    k : float
        Scale factor
    x : float
        X-coordinate translation
    y : float
        Y-coordinate translation

    Attributes
    ----------
    k : float
        Scale factor
    x : float
        X-coordinate translation
    y : float
        Y-coordinate translation

    Examples
    --------

    >>> identity = d3.ZoomTransform(1, 0, 0)
    >>> identity == d3.zoom_identity
    True
    """

    def __init__(self, k: float, x: float, y: float):
        self.k = k
        self.x = x
        self.y = y

    def __call__(self, point: tuple[float, float]) -> tuple[float, float]:
        """
        Returns the transformation of the specified point which is a
        two-element array of numbers :code:`[x, y]`. The returned point is
        equal to :math:`[x \\ cdot k + t_x, y \\cdot k + t_y]`.


        Parameters
        ----------
        point : tuple[float, float]
            Point to transform

        Returns
        -------
        tuple[float, float]
            Transformed point
        """
        return [point[0] * self.k + self.x, point[1] * self.k + self.y]

    def __eq__(self, o: Any) -> bool:
        """
        Checks if the other object is the same as itself.

        Parameters
        ----------
        o : Any
           Other object

        Returns
        -------
        bool
            :code:`True` if the :code:`o` object is the same as :code:`self`
        """
        if isinstance(o, Transform):
            return self.k == o.k and self.x == o.x and self.y == o.y
        return False

    def scale(self, k: float) -> TTransform:
        """
        Returns a transform whose scale :code:`k`₁ is equal to :math:`k_0
        \\cdot k`, where :math:`k_0` is this transform's scale.

        Parameters
        ----------
        k : float
            Scale factor

        Returns
        -------
        Transform
            New transformation
        """
        return self if k == 1 else Transform(self.k * k, self.x, self.y)

    def translate(self, x: float, y: float) -> TTransform:
        """
        Returns a transform whose translation :math:`t_{x_1}` and
        :math:`t_{y_1}` is equal to :math:`t_{x_0} + t_k x` and :math:`t_{y_0}
        + t_k y`, where :math:`t_{x_0}` and :math:`t_{y_0}` is this transform's
        translation and :math:`t_k` is this transform's scale.

        Parameters
        ----------
        x : float
            X-coordinate translation
        y : float
            Y-coordinate translation

        Returns
        -------
        Transform
            New transformation
        """
        return (
            self
            if x == 0 and y == 0
            else Transform(self.k, self.x + self.k * x, self.y + self.k * y)
        )

    def apply_x(self, x: float) -> float:
        """
        Returns the transformation of the specified x-coordinate, :math:`x
        \\cdot k + t_x`.

        Parameters
        ----------
        x : float
            X-coordinate point

        Returns
        -------
        float
            Result of the transformation
        """
        return x * self.k + self.x

    def apply_y(self, y: float) -> float:
        """
        Returns the transformation of the specified y-coordinate, :math:`y
        \\cdot k + t_y`.

        Parameters
        ----------
        y : float
           Y-coordinate point

        Returns
        -------
        float
            Result of the transformation
        """
        return y * self.k + self.y

    def invert(self, location: tuple[float, float]) -> tuple[float, float]:
        """
        Returns the inverse transformation of the specified point which is a
        two-element array of numbers :code:`[x, y]`. The returned point is
        equal to :math:`[(x - t_x) / k, (y - t_y) / k]`.

        Parameters
        ----------
        location : tuple[float, float]
            Point to inverse

        Returns
        -------
        tuple[float, float]
            Inversed point
        """
        return [(location[0] - self.x) / self.k, (location[1] - self.y) / self.k]

    def invert_x(self, x: float) -> float:
        """
        Returns the inverse transformation of the specified x-coordinate,
        :math:`(x - t_x) / k`.

        Parameters
        ----------
        x : float
            X-coordinate point to inverse

        Returns
        -------
        float
            Inverse transformation result
        """
        return (x - self.x) / self.k

    def invert_y(self, y: float) -> float:
        """
        Returns the inverse transformation of the specified y-coordinate,
        :math:`(y - t_y) / k`.

        Parameters
        ----------
        y : float
            y-coordinate point to inverse

        Returns
        -------
        float
            Inverse transformation result
        """
        return (y - self.y) / self.k

    def rescale_x(self, x):
        # TODO
        return x.copy().set_domain(
            list(map(x.invert, map(self.invert_x, x.get_range())))
        )

    def rescale_y(self, y):
        # TODO
        return y.copy().set_domain(
            list(map(y.invert, map(self.invert_y, y.get_range())))
        )

    def __str__(self) -> str:
        """
        Returns :code:`"translate({x},{y}) scale({k})"`.
        """
        return f"translate({self.x},{self.y}) scale({self.k})"


identity = Transform(1, 0, 0)
