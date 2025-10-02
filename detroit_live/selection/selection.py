import asyncio
from collections.abc import Callable, Iterator
from typing import Any, Optional, TypeVar

import orjson
from detroit.selection import Selection
from detroit.selection.enter import EnterNode
from detroit.types import Accessor, EtreeFunction, Number, T
from lxml import etree
from quart import websocket

from ..dispatch import parse_typenames
from ..events import Event, TrackingTree
from .active import set_active
from .app import App
from .on import on_add, on_remove
from .shared import SharedState

TLiveSelection = TypeVar("LiveSelection", bound="LiveSelection")


def default_html(
    selection: TLiveSelection,
    script: str,
) -> str:
    """
    Returns a function which generates HTML content containing scripts for
    events.

    Parameters
    ----------
    selection : LiveSelection
        Selection
    script: str
        Event listeners are parsed and joined as a string which should be
        placed into a :code:`<script>` tag in order to communicate events via
        :code:`websocket`.

    Returns
    -------
    str
        HTML content
    """
    ttree = TrackingTree()
    if ttree.root is None:
        return "<html></html>"
    node = ttree.root
    tag = node.tag
    if tag != "html":
        return f"<html><body>{selection}<script>{script}</script></body></html>"
    body = selection.select("body")
    if body._groups:
        if not len(body.select("[id='detroit']").nodes()):
            body.append("script").attr("id", "detroit").text(script)
        return str(selection).replace("&lt;", "<").replace("&gt;", ">")
    else:
        selection.append("script").attr("id", "detroit").text(script)
        return str(selection).replace("&lt;", "<").replace("&gt;", ">")


class LiveSelection(Selection[T]):
    """
    A selection is a set of elements from the DOM. Typically these elements are
    identified by selectors such as .fancy for elements with the class fancy,
    or div to select DIV elements.

    Selection methods come in two forms, :code:`select` and :code:`select_all`:
    the former selects only the first matching element, while the latter
    selects all matching elements in document order. The top-level selection
    methods, d3.select and d3.select_all, query the entire document; the
    subselection methods, selection.select and selection.select_all, restrict
    selection to descendants of the selected elements.

    By convention, selection methods that return the current selection such as
    selection.attr use four spaces of indent, while methods that return a new
    selection use only two. This helps reveal changes of context by making them
    stick out of the chain:

    Parameters
    ----------
    groups : list[list[etree.Element]]
        List of groups of selected nodes given its parent.
    parents : list[etree.Element]
        List of parents related to groups.
    enter : list[EnterNode[T]] | None = None
        List of placeholder nodes for each datum that had no corresponding
        DOM element in the selection.
    exit : list[etree.Element] = None
        List of existing DOM elements in the selection for which no new datum was found.

    Examples
    --------

    >>> body = d3.create("body")
    >>> (
    ...     body
    ...     .append("svg")
    ...     .attr("width", 960)
    ...     .attr("height", 500)
    ...     .append("g")
    ...     .attr("transform", "translate(20, 20)")
    ...     .append("rect")
    ...     .attr("width", 920)
    ...     .attr("height", 460)
    ... )
    >>> print(body.to_string())
    <body>
      <svg xmlns="http://www.w3.org/2000/svg" weight="960" height="500">
        <g transform="translate(20, 20)">
          <rect width="920" height="460"/>
        </g>
      </svg>
    </body>
    >>> str(body)
    '<body><svg xmlns="http://www.w3.org/2000/svg" weight="960" height="500"><g transform="translate(20, 20)"><rect width="920" height="460"/></g></svg></body>'
    """

    _shared = SharedState()

    def __init__(
        self,
        groups: list[list[etree.Element]],
        parents: list[etree.Element],
        enter: list[EnterNode[T]] | None = None,
        exit: list[etree.Element] = None,
    ):
        super().__init__(groups, parents, enter, exit, self._shared.data)
        self._shared.set_tree_root(self._parents)
        self.event_listeners = self._shared.event_listeners
        self.event_producers = self._shared.event_producers
        self._tree = self._shared.tree

    def select(self, selection: str | None = None) -> TLiveSelection:
        """
        Selects the first element that matches the specified :code:`selection` string.

        Supported forms are:

        - :code:`{tag_name}{.class_name}{:last-of-type}`
        - :code:`{tag_name}{[attribute_name="value"]}{:last-of-type}`

        The :code:`tag_name` is any SVG element tag (ex: :code:`g`,
        :code:`rect`, :code:`line`, ...). You can chain selections by adding
        one space between them.

        The :code:`.class_name` is specified when a element is created such as:

        .. code:: python

            svg.append("g").attr("class", "my_class")

        In this example, the value of :code:`.class_name` is :code:`.my_class`.

        The :code:`:last-of-type` option is useful when you only need the last
        element.

        Using :code:`[attribute_name="value"]` allows you to get any element
        associated to a specific attribute. For instance, in the following
        code:

        .. code:: python

            svg.append("g").attr("aria-label", "my_group")

        To access this element, the value of :code:`[attribute_name="value"]`
        must be :code:`[aria-label="my_group"]`.

        Parameters
        ----------
        selection : str | None
            Selection string

        Returns
        -------
        LiveSelection
            Selection of first element

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> svg.append("g").attr("class", "ticks")
        Selection(
            groups=[[g.ticks]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7f2d1504cb80>: None},
        )
        >>> svg.append("g").attr("class", "labels")
        Selection(
            groups=[[g.labels]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7f2d1504cb80>: None, <Element g at 0x7f2d15052640>: None},
        )
        >>> svg.select("g.ticks")
        Selection(
            groups=[[g.ticks]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7f2d1504cb80>: None, <Element g at 0x7f2d15052640>: None},
        )
        >>> svg.select("g.points")
        Selection(
            groups=[[]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7f2d1504cb80>: None, <Element g at 0x7f2d15052640>: None},
        )
        """
        selection = super().select(selection)
        return LiveSelection(selection._groups, selection._parents)

    def select_all(self, selection: str | None = None) -> TLiveSelection:
        """
        Selects all elements that match the specified :code:`selection` string.

        Supported forms are:

        - :code:`{tag_name}{.class_name}{:last-of-type}`
        - :code:`{tag_name}{[attribute_name="value"]}{:last-of-type}`

        The :code:`tag_name` is any SVG element tag (ex: :code:`g`,
        :code:`rect`, :code:`line`, ...). You can chain selections by adding
        one space between them.

        The :code:`.class_name` is specified when a element is created such as:

        .. code:: python

            svg.append("g").attr("class", "my_class")

        In this example, the value of :code:`.class_name` is :code:`.my_class`.

        The :code:`:last-of-type` option is useful when you only need the last
        element.

        Using :code:`[attribute_name="value"]` allows you to get any element
        associated to a specific attribute. For instance, in the following
        code:

        .. code:: python

            svg.append("g").attr("aria-label", "my_group")

        To access this element, the value of :code:`[attribute_name="value"]`
        must be :code:`[aria-label="my_group"]`.

        Parameters
        ----------
        selection : str | None
            Selection string

        Returns
        -------
        LiveSelection
            Selection of all matched elements

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> scale = d3.scale_linear([0, 10], [0, 100])
        >>> print(svg.call(d3.axis_bottom(scale).set_ticks(3)).to_string())
        <svg xmlns:xmlns="http://www.w3.org/2000/svg" fill="none" font-size="10" font-family="sans-serif" text-anchor="middle">
          <path class="domain" stroke="currentColor" d="M0.5,6V0.5H100.5V6"/>
          <g class="tick" opacity="1" transform="translate(0.5, 0)">
            <line stroke="currentColor" y2="6"/>
            <text fill="currentColor" y="9" dy="0.71em">0</text>
          </g>
          <g class="tick" opacity="1" transform="translate(50.5, 0)">
            <line stroke="currentColor" y2="6"/>
            <text fill="currentColor" y="9" dy="0.71em">5</text>
          </g>
          <g class="tick" opacity="1" transform="translate(100.5, 0)">
            <line stroke="currentColor" y2="6"/>
            <text fill="currentColor" y="9" dy="0.71em">10</text>
          </g>
        </svg>
        >>> svg.select_all("g").select_all("line")
        Selection(
            groups=[[line], [line], [line]],
            parents=[g.tick, g.tick, g.tick],
            enter=None,
            exit=None,
            data={},
        )
        >>> svg.select_all("line")
        Selection(
            groups=[[line], [line], [line]],
            parents=[g.tick, g.tick, g.tick],
            enter=None,
            exit=None,
            data={},
        )
        """
        selection = super().select_all(selection)
        return LiveSelection(selection._groups, selection._parents)

    def enter(self) -> TLiveSelection:
        """
        Returns the enter selection: placeholder nodes for each datum that had
        no corresponding DOM element in the selection.

        Returns
        -------
        LiveSelection
            Enter selection

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> text = svg.select_all("text").data(["hello", "world"])
        >>> text_enter = text.enter()
        >>> text_enter
        Selection(
            groups=[[EnterNode(svg, hello), EnterNode(svg, world)]],
            parents=[svg],
            enter=None,
            exit=None,
            data={},
        )
        """
        selection = super().enter()
        return LiveSelection(selection._groups, selection._parents)

    def exit(self) -> TLiveSelection:
        """
        Returns the exit selection: existing DOM elements in the selection for
        which no new datum was found. (The exit selection is empty for
        selections not returned by selection.data.)


        Returns
        -------
        LiveSelection
            Exit selection

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> text = svg.select_all("text").data(["hello", "world"])
        >>> text_exit = text.exit()
        >>> text_exit
        Selection(
            groups=[[]],
            parents=[svg],
            enter=None,
            exit=None,
            data={},
        )
        """
        selection = super().exit()
        return LiveSelection(selection._groups, selection._parents)

    def merge(self, context: TLiveSelection) -> TLiveSelection:
        """
        Returns a new selection merging this selection with the specified other
        selection or transition. The returned selection has the same number of
        groups and the same parents as this selection. Any missing (None)
        elements in this selection are filled with the corresponding element,
        if present (not null), from the specified selection. (If the other
        selection has additional groups or parents, they are ignored.)

        Parameters
        ----------
        context : Selection
            Selection

        Returns
        -------
        LiveSelection
            Merged selection

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> text = svg.select_all("text").data(["hello", "world"])
        >>> text_enter = text.enter()
        >>> text_enter.append("text").text(lambda text: text)
        Selection(
            groups=[[text, text]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element text at 0x7f2d14b2a580>: 'hello', <Element text at 0x7f2d14457540>: 'world'},
        )
        >>> print(svg.to_string())
        <svg xmlns:xmlns="http://www.w3.org/2000/svg">
          <text>hello</text>
          <text>world</text>
        </svg>
        >>> text
        Selection(
            groups=[[None, None]],
            parents=[svg],
            enter=[[EnterNode(svg, hello), EnterNode(svg, world)]],
            exit=[[]],
            data={},
        )
        >>> text = text.merge(text_enter)
        >>> text
        Selection(
            groups=[[EnterNode(svg, hello), EnterNode(svg, world)]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element text at 0x7f2d14b2a580>: 'hello', <Element text at 0x7f2d14457540>: 'world'},
        )
        """
        selection = super().merge(context)
        return LiveSelection(selection._groups, selection._parents)

    def filter(self, match: Accessor[T, bool] | int | float | str) -> TLiveSelection:
        """
        Filters the selection, returning a new selection that contains only the
        elements for which the specified filter is true.

        Parameters
        ----------
        match : Accessor[T, bool] | int | float | str
            Constant to match or accessor which returns a boolean

        Returns
        -------
        LiveSelection
            Filtered selection

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> scale = d3.scale_linear([0, 10], [0, 100])
        >>> print(svg.call(d3.axis_bottom(scale).set_ticks(3)).to_string())
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" font-size="10" font-family="sans-serif" text-anchor="middle">
          <path class="domain" stroke="currentColor" d="M0.5,6V0.5H100.5V6"/>
          <g class="tick" opacity="1" transform="translate(0.5, 0)">
            <line stroke="currentColor" y2="6"/>
            <text fill="currentColor" y="9" dy="0.71em">0</text>
          </g>
          <g class="tick" opacity="1" transform="translate(50.5, 0)">
            <line stroke="currentColor" y2="6"/>
            <text fill="currentColor" y="9" dy="0.71em">5</text>
          </g>
          <g class="tick" opacity="1" transform="translate(100.5, 0)">
            <line stroke="currentColor" y2="6"/>
            <text fill="currentColor" y="9" dy="0.71em">10</text>
          </g>
        </svg>
        >>> result = svg.select_all("text").filter(lambda d, i: i % 2 != 0)
        >>> result
        Selection(
            groups=[[text]],
            parents=[svg],
            enter=None,
            exit=None,
            data={},
        )
        >>> result.node().text
        '5'
        """
        selection = super().filter(match)
        return LiveSelection(selection._groups, selection._parents)

    def append(self, name: str) -> TLiveSelection:
        """
        If the specified name is a string, appends a new element of this type
        (tag name) as the last child of each selected element, or before the
        next following sibling in the update selection if this is an enter
        selection. The latter behavior for enter selections allows you to
        insert elements into the DOM in an order consistent with the new bound
        data; however, note that selection.order may still be required if
        updating elements change order (i.e., if the order of new data is
        inconsistent with old data).

        Parameters
        ----------
        name : str
            Tag name

        Returns
        -------
        LiveSelection
            Selection

        Examples
        --------

        Simple append:

        >>> svg = d3.create("svg")
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg"/>
        >>> g = svg.append("g").attr("class", "labels")
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <g class="labels"/>
        </svg>

        Multiple append:

        >>> import detroit as d3
        >>> svg = d3.create("svg")
        >>> svg.select_all("g").data([None, None]).enter().append("g").append("text")
        Selection(
            groups=[[text], [text]],
            parents=[g, g],
            enter=None,
            exit=None,
            data={<Element g at 0x7f91d8360200>: None, <Element g at 0x7f91d8360240>: None, <Element text at 0x7f91d8bbb540>: None, <Element text at 0
        x7f91d8360140>: None},
        )
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <g>
            <text/>
          </g>
          <g>
            <text/>
          </g>
        </svg>
        """
        selection = super().append(name)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def each(self, callback: EtreeFunction[T, None]) -> TLiveSelection:
        """
        Invokes the specified function for each selected element, in order,
        being passed the current DOM element (nodes[i]), the current datum (d),
        the current index (i), and the current group (nodes).

        Parameters
        ----------
        callback : EtreeFunction[T, None]
            Function to call which takes as argument:

            * **node** (:code:`etree.Element`) - the node element
            * **data** (:code:`Any`) - current data associated to the node
            * **index** (:code:`int`) - the index of the node in its group
            * **group** (:code:`list[etree.Element]`) - the node's group with other nodes.

        Returns
        -------
        LiveSelection
            Itself
        """
        selection = super().each(callback)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def attr(
        self, name: str, value: Accessor[T, str | Number] | str | None = None
    ) -> TLiveSelection:
        """
        If a value is specified, sets the attribute with the specified name to
        the specified value on the selected elements and returns this
        selection.

        If the value is a function, it is evaluated for each selected element,
        in order, being passed the current datum (d), the current index (i),
        and the current group (nodes).

        Parameters
        ----------
        name : str
            Name of the attribute
        value : Accessor[T, str | Number] | str | None
            Value

        Returns
        -------
        LiveSelection
            Itself

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> print(
        ...     svg.append("g")
        ...     .attr("class", "labels")
        ...     .attr("transform", "translate(20, 10)")
        ...     .to_string()
        ... )
        <svg xmlns="http://www.w3.org/2000/svg">
          <g class="labels" transform="translate(20, 10)"/>
        </svg>
        """
        selection = super().attr(name, value)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def property(
        self, name: str, value: Accessor[T, Any] | list[Any] | Any | None = None
    ) -> TLiveSelection:
        """
        This method has no difference with :code:`Selection.attr`.

        Parameters
        ----------
        name : str
            Name of the property
        value : Accessor[T, Any] | list[Any] | Any | None
            Property value function or constant property value. The final value
            is converted to a string.

        Returns
        -------
        LiveSelection
            Itself

        Examples
        --------

        >>> import detroit as d3
        >>> svg = d3.create("svg")
        >>> print(
        ...     svg.append("g")
        ...     .property("class", "labels")
        ...     .property("transform", "translate(20, 10)")
        ...     .to_string()
        ... )
        <svg xmlns="http://www.w3.org/2000/svg">
          <g class="labels" transform="translate(20, 10)"/>
        </svg>
        """
        return self.attr(name, value)

    def style(
        self, name: str, value: Accessor[T, str] | str | None = None
    ) -> TLiveSelection:
        """
        If a value is specified, sets the style with the specified name to the
        specified value on the selected elements and returns this selection.

        If the value is a function, it is evaluated for each selected element,
        in order, being passed the current datum (d), the current index (i),
        and the current group (nodes).

        Parameters
        ----------
        name : str
            Name of the style
        value : Accessor[T, str] | str | None
            Value constant or function

        Returns
        -------
        LiveSelection
            Itself

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> print(
        ...     svg.append("text")
        ...     .style("fill", "black")
        ...     .style("stroke", "none")
        ...     .to_string()
        ... )
        <svg xmlns="http://www.w3.org/2000/svg">
          <text style="fill:black;stroke:none;"/>
        </svg>
        """
        selection = super().style(name, value)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def text(self, value: Accessor[T, str] | str | None = None) -> TLiveSelection:
        """
        If the value is a constant, then all elements are given the same text
        content; otherwise, if the value is a function, it is evaluated for
        each selected element, in order, being passed the current datum (d),
        the current index (i), and the current group (nodes).

        Parameters
        ----------
        value : Accessor[T, str] | str | None
            Value constant or function

        Returns
        -------
        LiveSelection
            Itself

        Examples
        --------

        Direct assignment:

        >>> svg = d3.create("svg")
        >>> print(svg.append("text").text("Hello, world!").to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <text>Hello, world!</text>
        </svg>

        Through data:

        >>> svg = d3.create("svg")
        >>> print(
        ...     svg.select_all("text")
        ...     .data(["Hello", "world"])
        ...     .enter()
        ...     .append("text")
        ...     .text(lambda text, i: f"{text} - index {i}")
        ...     .to_string()
        ... )
        <svg xmlns="http://www.w3.org/2000/svg">
          <text>Hello - index 0</text>
          <text>world - index 1</text>
        </svg>

        """
        selection = super().text(value)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def html(self, value: Accessor[T, Any] | Any | None = None) -> TLiveSelection:
        """
        This method has no difference with :code:`Selection.text`.

        Parameters
        ----------
        value : Accessor[T, Any] | Any | None
            Inner HTML function or constant inner HTML. The final value is
            converted to a string.

        Returns
        -------
        LiveSelection
            Itself

        Examples
        --------

        Direct assignment:

        >>> import detroit as d3
        >>> svg = d3.create("svg")
        >>> print(svg.append("text").html("Hello, world!").to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <text>Hello, world!</text>
        </svg>

        Through data:

        >>> import detroit as d3
        >>> svg = d3.create("svg")
        >>> print(
        ...     svg.select_all("text")
        ...     .data(["Hello", "world"])
        ...     .enter()
        ...     .append("text")
        ...     .html(lambda text, i: f"{text} - index {i}")
        ...     .to_string()
        ... )
        <svg xmlns="http://www.w3.org/2000/svg">
          <text>Hello - index 0</text>
          <text>world - index 1</text>
        </svg>
        """
        return self.text(value)

    def classed(
        self, names: str, value: Accessor[T, bool] | bool | None = None
    ) -> TLiveSelection:
        """
        Assigns or unassigns the specified CSS class names on the selected
        elements by setting the class attribute or modifying the class list
        property and returns this selection.

        Parameters
        ----------
        names : str
            Class names
        value : Accessor[T, bool] | bool | None
            Boolean function or constant boolean where the boolean indicates if
            the class names must be added or removed from the class property of
            the node.

        Returns
        -------
        LiveSelection
            Itself

        Examples
        --------

        >>> import detroit as d3
        >>> svg = d3.create("svg")
        >>> data = ["Hello", "world"]
        >>> (
        ...    svg.select_all()
        ...    .data(data)
        ...    .enter()
        ...    .append("g")
        ...    .classed("myclass", lambda d: d == "Hello")
        ... )
        Selection(
            groups=[[g.myclass, g]],
            parents=[svg],
        )
        >>> str(svg)
        '<svg xmlns="http://www.w3.org/2000/svg"><g class="myclass"/><g/></svg>'
        """
        selection = super().classed(names, value)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def datum(self, value: T) -> TLiveSelection:
        """
        Sets the bound data for the first selected node.

        Parameters
        ----------
        value : T
            Value

        Returns
        -------
        LiveSelection
            Itself

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> g1 = svg.append("g").attr("class", "g1")
        >>> g2 = svg.append("g").attr("class", "g2")
        >>> g = svg.select_all("g")
        >>> g
        Selection(
            groups=[[g.g1, g.g2]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7f3eda0be4c0>: None, <Element g at 0x7f3eda029700>: None},
        )
        >>> g.datum("Hello, world")
        Selection(
            groups=[[g.g1, g.g2]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7f3eda0be4c0>: 'Hello, world', <Element g at 0x7f3eda029700>: None},
        )
        >>> g1.node()
        <Element g at 0x7f3eda0be4c0>
        """
        selection = super().datum(value)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def data(
        self,
        values: list[T] | EtreeFunction[T, list[T]],
        key: Accessor[T, float | str] | None = None,
    ) -> TLiveSelection:
        """
        Binds the specified list of data with the selected elements, returning
        a new selection that represents the update selection: the elements
        successfully bound to data. Also defines the enter and exit selections
        on the returned selection, which can be used to add or remove elements
        to correspond to the new data. The specified data is an array of
        arbitrary values (e.g., numbers or objects), or a function that returns
        an array of values for each group.

        Parameters
        ----------
        values : list[T] | EtreeFunction[T, list[T]]
            List of data to bind
        key : Accessor[T, float | str] | None
            Optional accessor which returns a key value

        Returns
        -------
        LiveSelection
            Itself

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> svg.append("g")
        Selection(
            groups=[[g]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7f3eda09b540>: None},
        )
        >>> svg.append("g")
        Selection(
            groups=[[g]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7f3eda09b540>: None, <Element g at 0x7f3edac50240>: None},
        )
        >>> svg.select_all("text").data(["Hello", "world"])
        Selection(
            groups=[[None, None]],
            parents=[svg],
            enter=[[EnterNode(svg, Hello), EnterNode(svg, world)]],
            exit=[[]],
            data={<Element g at 0x7f3eda09b540>: None, <Element g at 0x7f3edac50240>: None},
        )
        >>> svg.select_all("g").data(["Hello", "world"])
        Selection(
            groups=[[g, g]],
            parents=[svg],
            enter=[[None, None]],
            exit=[[None, None]],
            data={<Element g at 0x7f3eda09b540>: 'Hello', <Element g at 0x7f3edac50240>: 'world'},
        )
        """
        selection = super().data(values, key)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def order(self) -> TLiveSelection:
        """
        Re-inserts elements into the document such that the document order of
        each group matches the selection order.

        Returns
        -------
        LiveSelection
            Itself
        """
        selection = super().order()
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def join(
        self,
        onenter: Callable[[TLiveSelection], TLiveSelection] | str,
        onupdate: Callable[[TLiveSelection], TLiveSelection] | None = None,
        onexit: Callable[[TLiveSelection], None] | None = None,
    ) -> TLiveSelection:
        """
        Appends, removes and reorders elements as necessary to match the data
        that was previously bound by selection.data, returning the merged enter
        and update selection. This method is a convenient alternative to the
        explicit general update pattern, replacing selection.enter,
        selection.exit, selection.append, selection.remove, and
        selection.order.

        Parameters
        ----------
        onenter : Callable[[Selection], Selection] | str
            Enter selection or function
        onupdate : Callable[[Selection], Selection] | None
            Function
        onexit : Callable[[Selection], None] | None
            Function

        Returns
        -------
        LiveSelection
            Selection with joined elements

        Examples
        --------

        >>> data = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
        >>> svg = d3.create("svg")
        >>> table = (
        ...     svg.append("table")
        ...     .select_all("tr")
        ...     .data(data)
        ...     .join("tr")
        ...     .select_all("td")
        ...     .data(lambda _, d: d)
        ...     .join("td")
        ...     .text(lambda d: str(d))
        ... )
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <table>
            <tr>
              <td>0</td>
              <td>1</td>
              <td>2</td>
              <td>3</td>
            </tr>
            <tr>
              <td>4</td>
              <td>5</td>
              <td>6</td>
              <td>7</td>
            </tr>
            <tr>
              <td>8</td>
              <td>9</td>
              <td>10</td>
              <td>11</td>
            </tr>
            <tr>
              <td>12</td>
              <td>13</td>
              <td>14</td>
              <td>15</td>
            </tr>
          </table>
        </svg>

        Another usage could be to specify functions :

        >>> data = [None] * 3
        >>> svg = d3.create("svg")
        >>> svg.append("circle").attr("fill", "yellow")
        Selection(
            groups=[[circle]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element circle at 0x7f5e219fd300>: None},
        )
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <circle fill="yellow"/>
        </svg>
        >>> (
        ...     svg.select_all("circle")
        ...     .data(data)
        ...     .join(
        ...         onenter=lambda enter: enter.append("circle").attr("fill", "green"),
        ...         onupdate=lambda update: update.attr("fill", "blue")
        ...     )
        ...     .attr("stroke", "black")
        ... )
        Selection(
            groups=[[circle, circle, None]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element circle at 0x7f5e219fd300>: 0, <Element circle at 0x7f5e2251f040>: 1, <Element circle at 0x7f5e22517a80>: 2},
        )
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <circle fill="blue"/>
          <circle fill="green" stroke="black"/>
          <circle fill="green" stroke="black"/>
        </svg>

        In this example, the attribute :code:`fill` of the existing circle was
        updated, by :code:`onupdate`, from :code:`yellow` to :code:`blue`. And
        since :code:`data` has 3 elements, :code:`onenter` has generated the
        last circles.
        """
        selection = super().join(onenter, onupdate, onexit)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def insert(self, name: str, before: str) -> TLiveSelection:
        """
        If the specified name is a string, inserts a new element of this type
        (tag name) before the first element matching the specified
        :code:`before` selector for each selected element.

        Parameters
        ----------
        name : str
            Tag name
        before : str
            Node element selection

        Returns
        -------
        LiveSelection
            Selection with inserted element(s)

        Examples
        --------

        Since :code:`before` refers to a selected tag, this method will operate
        multiple insertions.

        >>> import detroit as d3
        >>> svg = d3.create("svg")
        >>> (
        ...     svg.select_all("g")
        ...     .data([None, None])
        ...     .enter()
        ...     .append("g")
        ...     .append("text")
        ... )
        Selection(
            groups=[[text], [text]],
            parents=[g, g],
            enter=None,
            exit=None,
            data={<Element g at 0x7fc5748c2f00>: None, <Element g at 0x7fc5748c2300>: None, <Element text at 0x7fc575105280>: None, <Element text at 0x7fc5748c2100>: None},
        )
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <g>
            <text/>
          </g>
          <g>
            <text/>
          </g>
        </svg>
        >>> svg.insert("circle", "text")
        Selection(
            groups=[[circle], [circle]],
            parents=[g, g],
            enter=None,
            exit=None,
            data={<Element circle at 0x7fc5748f9980>: None, <Element circle at 0x7fc5748f8c80>: None},
        )
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <g>
            <circle/>
            <text/>
          </g>
          <g>
            <circle/>
            <text/>
          </g>
        </svg>

        If you prefer to insert an element at a specific location, you need to
        select first the specific node and then insert your element.

        >>> svg = d3.create("svg")
        >>> (
        ...     svg.select_all("g")
        ...     .data(["class1", "class2"])
        ...     .enter()
        ...     .append("g")
        ...     .append("text")
        ...     .attr("class", lambda d: d)
        ... )
        Selection(
            groups=[[text.class1], [text.class2]],
            parents=[g, g],
            enter=None,
            exit=None,
            data={<Element g at 0x7fc5748e9340>: 'class1', <Element g at 0x7fc5748e9b80>: 'class2', <Element text at 0x7fc5753f7140>: 'class1', <Eleme
        nt text at 0x7fc5748e8180>: 'class2'},
        )
        >>> svg.insert("circle", ".class1")
        Selection(
            groups=[[circle]],
            parents=[g],
            enter=None,
            exit=None,
            data={<Element circle at 0x7fc5753f0500>: None},
        )
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <g>
            <circle/>
            <text class="class1"/>
          </g>
          <g>
            <text class="class2"/>
          </g>
        </svg>
        """
        selection = super().insert(name, before)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def remove(self) -> TLiveSelection:
        """
        Removes the selected elements from the document. Returns this selection
        (the removed elements) which are now detached from the DOM.

        Returns
        -------
        LiveSelection
            Selection with removed elements

        Examples
        --------

        >>> import detroit as d3
        >>> svg = d3.create("svg")
        >>> (
        ...     svg.select_all("g")
        ...     .data([None] * 10)
        ...     .enter()
        ...     .append("g")
        ...     .attr("class", "domain")
        ... )
        Selection(
            groups=[[g.domain, g.domain, g.domain, g.domain, g.domain, g.domain, g.domain, g.domain, g.domain, g.domain]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7fd461822100>: None, <Element g at 0x7fd461822800>: None, <Element g at 0x7fd461821980>: None, <Element g at 0x7fd4618219c0>: None, <Element g at 0x7fd461821380>: None, <Element g at 0x7fd461822ec0>: None, <Element g at 0x7fd461821580>: None, <Element g at 0x7fd461822180>: None, <Element g at 0x7fd461823300>: None, <Element g at 0x7fd461821200>: None},
        )
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <g class="domain"/>
          <g class="domain"/>
          <g class="domain"/>
          <g class="domain"/>
          <g class="domain"/>
          <g class="domain"/>
          <g class="domain"/>
          <g class="domain"/>
          <g class="domain"/>
          <g class="domain"/>
        </svg>
        >>> svg.select_all(".domain").remove()
        Selection(
            groups=[[]],
            parents=[svg],
            enter=None,
            exit=None,
            data={},
        )
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg"/>
        """
        selection = super().remove()
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def call(
        self, func: Callable[[TLiveSelection, ...], Any], *args: Any
    ) -> TLiveSelection:
        """
        Invokes the specified function exactly once, passing in this selection
        along with any optional arguments. Returns this selection.

        Parameters
        ----------
        func : Callable[[Selection, ...], Any]
            Function to call
        args : Any
            Arguments for the function to call

        Returns
        -------
        LiveSelection
            Itself

        Examples
        --------

        This is equivalent to invoking the function by hand but facilitates
        method chaining. For example, to set several styles in a reusable
        function:

        >>> def name(selection, first, last):
        ...     selection.attr("first-name", first).attr("last-name", last)

        Now say:

        >>> d3.select_all("div").call(name, "John", "Snow")

        This is roughly equivalent to:

        >>> name(d3.select_all("div"), "John", "Snow")
        """
        selection = super().call(func, *args)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def clone(self, deep: bool = False) -> TLiveSelection:
        """
        Inserts clones of the selected elements immediately following the
        selected elements and returns a selection of the newly added clones.

        Parameters
        ----------
        deep : bool
            :code:`True` for deep copy

        Returns
        -------
        LiveSelection
            Clone of itself
        """
        selection = super().clone(deep)
        return LiveSelection(
            selection._groups,
            selection._parents,
            enter=selection._enter,
            exit=selection._exit,
        )

    def node(self) -> etree.Element:
        """
        Returns the first (non-None) element in this selection.

        Returns
        -------
        etree.Element
            Node

        Examples
        --------
        >>> svg = d3.create("svg")
        >>> g = (
        ...     svg.select_all("g")
        ...     .data(list(reversed(range(10))))
        ...     .enter()
        ...     .append("g")
        ...     .attr("class", lambda d: f"class{d}")
        ... )
        >>> g
        Selection(
            groups=[[g.class9, g.class8, g.class7, g.class6, g.class5, g.class4, g.class3, g.class2, g.class1, g.class0]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7fac2cf609c0>: 9, <Element g at 0x7fac2c4e1880>: 8, <Element g at 0x7fac2c4e0840>: 7, <Element g at 0x7fac2cca92c0>:6, <Element g at 0x7fac2cca8800>: 5, <Element g at 0x7fac2cca99c0>: 4, <Element g at 0x7fac2cca9940>: 3, <Element g at 0x7fac2cca9200>: 2, <Element g at 0x7fac2ccaa980>: 1, <Element g at 0x7fac2ccaa400>: 0},
        )
        >>> g.node()
        <Element g at 0x7fac2cf609c0>
        """
        return super().node()

    def nodes(self) -> list[etree.Element]:
        """
        Returns a list of all (non-None) elements in this selection.

        Returns
        -------
        list[etree.Element]
            List of nodes

        Examples
        --------
        >>> svg = d3.create("svg")
        >>> g = (
        ...     svg.select_all("g")
        ...     .data(list(reversed(range(10))))
        ...     .enter()
        ...     .append("g")
        ...     .attr("class", lambda d: f"class{d}")
        ... )
        >>> g
        Selection(
            groups=[[g.class9, g.class8, g.class7, g.class6, g.class5, g.class4, g.class3, g.class2, g.class1, g.class0]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7fac2cf609c0>: 9, <Element g at 0x7fac2c4e1880>: 8, <Element g at 0x7fac2c4e0840>: 7, <Element g at 0x7fac2cca92c0>:6, <Element g at 0x7fac2cca8800>: 5, <Element g at 0x7fac2cca99c0>: 4, <Element g at 0x7fac2cca9940>: 3, <Element g at 0x7fac2cca9200>: 2, <Element g at 0x7fac2ccaa980>: 1, <Element g at 0x7fac2ccaa400>: 0},
        )
        >>> g.nodes()
        [<Element g at 0x7fac2cf609c0>, <Element g at 0x7fac2c4e1880>, <Element g at 0x7fac2c4e0840>, <Element g at 0x7fac2cca92c0>, <Element g at 0x7fac2cca8800>, <Element g at 0x7fac2cca99c0>, <Element g at 0x7fac2cca9940>, <Element g at 0x7fac2cca9200>, <Element g at 0x7fac2ccaa980>, <Element g at 0x7fac2ccaa400>]
        """
        return list(self)

    def __iter__(self) -> Iterator[etree.Element]:
        """
        Make the selection as an iterator

        Returns
        -------
        Iterator[etree.Element]
            Iterator of non-None nodes
        """
        return super().__iter__()

    def selection(self) -> TLiveSelection:
        """
        Returns the selection without any modification.

        Returns
        -------
        LiveSelection
            Itself
        """
        return self

    def on(
        self,
        typename: str,
        listener: Callable[[Event, T | None, Optional[etree.Element]], None]
        | None = None,
        extra_nodes: list[etree.Element] | None = None,
        html_nodes: list[etree.Element] | None = None,
        active: bool = True,
        target: str | None = None,
    ) -> TLiveSelection:
        """
        Adds a listener to each selected element for the specified event
        typename if the specified :code:`listener` is not :code:`None`. Else,
        it removes the listener given the specified event typename.

        Parameters
        ----------
        typename : str
            Event typename
        listener : Callable[[Event, T | None, Optional[etree.Element]], None] | None
            Listener function
        extra_nodes : list[etree.Element] | None
            Extra nodes to update when the listener is called
        active: bool
            :code:`False` if you want to create the event listener but not
            active when the application is launched. It is useful when you want
            to activate this event listener only when another event listener
            was activated.
        target : str | None
            Javascript target on which the event listener is added.

        Returns
        -------
        LiveSelection
            Itself
        """
        extra_nodes = [] if extra_nodes is None else extra_nodes
        html_nodes = [] if html_nodes is None else html_nodes
        typenames = list(parse_typenames(typename))

        on = (
            on_remove(self.event_listeners)
            if listener is None
            else on_add(
                self.event_listeners,
                listener,
                self._data.get,
                extra_nodes,
                html_nodes,
                active,
                target,
            )
        )
        nodes = [node for group in self._groups for node in group]
        for node in filter(lambda n: n is not None, nodes):
            if isinstance(node, EnterNode):
                node = node._parent
            for typename, name in typenames:
                on(typename, name, node)
        return self

    def set_event(self, typename: str, active: bool) -> TLiveSelection:
        """
        Updates selected event listeners for being active or not given the
        specified :code:`active` value.

        Parameters
        ----------
        typename : str
            Event typename
        active : bool
            :code:`True` for activating event listeners else :code:`False`

        Returns
        -------
        LiveSelection
            Itself
        """
        set_event = set_active(self.event_listeners, active)
        typenames = list(parse_typenames(typename))
        nodes = [node for group in self._groups for node in group]
        for node in filter(lambda n: n is not None, nodes):
            if isinstance(node, EnterNode):
                node = node._parent
            for typename, name in typenames:
                set_event(typename, name, node)
        return self

    def create_app(
        self,
        name: str | None = None,
        html: Callable[[TLiveSelection, str], str] | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> App:
        """
        Creates an application for allowing interactivity.
        Use :code:`App.run` to start the application.

        This is best used for development only, see Hypercorn for production
        servers.

        Parameters
        ----------
        name : str | None
            Name of the application
        html : Callable[[LiveSelection, str], str] | None
            Function to transform the selection and a script content into a
            HTML content. Event listeners are parsed and joined as a string
            variable :code:`script` which should be placed into a
            :code:`<script>` tag in order to communicate events via
            :code:`websocket`.
        host : str | None
            Hostname to listen on. By default this is loopback only, use
            0.0.0.0 to have the server listen externally.
        port : int | None
            Port number to listen on.

        Returns
        -------
        App
            Application for allowing interactivity.
        """
        import logging

        logging.basicConfig(
            format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
            datefmt="[%Y-%m-%d %H:%M:%S %z]",
            level=logging.WARNING,
        )
        app = App("detroit-live" if name is None else name)
        script = self.event_listeners.into_script(host, port)

        @app.websocket("/ws")
        async def ws():
            # Create pending asynchronous tasks
            # Websocket task
            pending = {asyncio.create_task(websocket.receive())}
            # Timer tasks for starting event producers (timers)
            if next_tasks := self.event_producers.next_tasks():
                pending.update(next_tasks)
            # Queue task to gather updated node changes
            if queue_task := self.event_producers.queue_task():
                pending.add(queue_task)
            while True:
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                queue_added = False
                for task in done:
                    result = task.result()
                    # Result from websocket task
                    if isinstance(result, str):
                        event = orjson.loads(result)
                        for json in self.event_listeners(event):
                            await websocket.send(orjson.dumps(json))
                        pending.add(asyncio.create_task(websocket.receive()))
                        result = None
                    # Result from event producers (timers)
                    elif isinstance(result, tuple):
                        _source, values = result
                        await websocket.send(orjson.dumps(values))

                    # Updates next tasks and queue tasks from event producers
                    if next_tasks := self.event_producers.next_tasks(result):
                        pending.update(next_tasks)
                    if not queue_added:
                        if queue := self.event_producers.queue_task(result):
                            queue_added = True
                            pending.add(queue)

        @app.route("/")
        async def index():
            return default_html(self, script) if html is None else html(self, script)

        app._host = host
        app._port = port
        return app

    def to_string(self, pretty_print: bool = True) -> str:
        """
        Convert selection to string

        Parameters
        ----------
        pretty_print : bool
            :code:`True` to prettify output

        Returns
        -------
        str
            String

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> g = (
        ...     svg.select_all("g")
        ...     .data(list(reversed(range(10))))
        ...     .enter()
        ...     .append("g")
        ...     .attr("class", lambda d: f"class{d}")
        ... )
        >>> print(svg.to_string())
        <svg xmlns="http://www.w3.org/2000/svg">
          <g class="class9"/>
          <g class="class8"/>
          <g class="class7"/>
          <g class="class6"/>
          <g class="class5"/>
          <g class="class4"/>
          <g class="class3"/>
          <g class="class2"/>
          <g class="class1"/>
          <g class="class0"/>
        </svg>
        >>> print(svg.to_string(False))
        <svg xmlns="http://www.w3.org/2000/svg"><g class="class9"/><g class="class8"/><g class="class7"/><g class="class6"/><g class="class5"/><g class="class4"/><g class="class3"/><g class="class2"/><g class="class1"/><g class="class0"/></svg>
        >>> svg.to_string(False) == str(svg)
        True
        """
        if len(self._parents) == 0:
            return ""
        return (
            etree.tostring(self._parents[0], pretty_print=pretty_print, method="html")
            .decode("utf-8")
            .removesuffix("\n")
        )

    def to_repr(
        self, show_enter: bool = True, show_exit: bool = True, show_data: bool = True
    ) -> str:
        """
        Represents the selection with optional parameters.

        Parameters
        ----------
        show_enter : bool
            Show enter elements associated to this selection
        show_exit : bool
            Show exit elements associated to this selection
        show_data : bool
            Show data associated to this selection

        Returns
        -------
        str
            String

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> g = (
        ...     svg.select_all("g")
        ...     .data(list(reversed(range(10))))
        ...     .enter()
        ...     .append("g")
        ...     .attr("class", lambda d: f"class{d}")
        ... )
        >>> print(g.to_repr())
        Selection(
            groups=[[g.class9, g.class8, g.class7, g.class6, g.class5, g.class4, g.class3, g.class2, g.class1, g.class0]],
            parents=[svg],
            enter=None,
            exit=None,
            data={<Element g at 0x7287cf850040>: 9, <Element g at 0x7287cfa50bc0>: 8, <Element g at 0x7287cf883ac0>: 7, <Element g at 0x7287cf8837c0>:
         6, <Element g at 0x7287cf883e00>: 5, <Element g at 0x7287cf883a40>: 4, <Element g at 0x7287cf882fc0>: 3, <Element g at 0x7287cf883a80>: 2, <E
        lement g at 0x7287cf880d80>: 1, <Element g at 0x7287cf881000>: 0},
        )
        """
        return super().to_repr(show_enter, show_exit, show_data)

    def __str__(self) -> str:
        """
        Returns the SVG content. Equivalent to
        :code:`Selection.to_string(False)`.

        Returns
        -------
        str
            String
        """
        return super().__str__()

    def __repr__(self) -> str:
        """
        Represents the selection

        Returns
        -------
        str
            String

        Examples
        --------

        >>> svg = d3.create("svg")
        >>> g = (
        ...     svg.select_all("g")
        ...     .data(list(reversed(range(10))))
        ...     .enter()
        ...     .append("g")
        ...     .attr("class", lambda d: f"class{d}")
        ... )
        >>> print(repr(g))
        Selection(
            groups=[[g.class9, g.class8, g.class7, g.class6, g.class5, g.class4, g.class3, g.class2, g.class1, g.class0]],
            parents=[svg],
        )
        """
        return super().__repr__()
