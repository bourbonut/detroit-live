Detroit Live's documentation!
=============================

:code:`detroit-live` is based on `detroit <https://github.com/bourbonut/detroit>`_ and aims to bring interactivity to visualizations.

Installation
------------

.. code:: shell

   pip install git+https://github.com/bourbonut/detroit-live.git


Getting starting
----------------

If you are not familiar with `detroit <https://github.com/bourbonut/detroit>`_, please have a look at the `detroit's documentation <https://detroit.readthedocs.io>`_.

In :code:`detroit_live`, `Selection <https://detroit.readthedocs.io/en/latest/api/selection.html#detroit.selection.selection.Selection>`_ becomes :class:`LiveSelection <detroit_live.selection.selection.LiveSelection>`. A :code:`LiveSelection` has the distinctive feature to share data, event listeners and event producers without explicit code.

To add interactivity to your visualization, there are two ways:

* Add an *listener callback* by using :func:`LiveSelection.on <detroit_live.selection.selection.LiveSelection.on>`; it creates an :class:`EventListener <detroit_live.events.event_listeners.EventListener>` stored in the shared class :class:`EventListeners <detroit_live.events.event_listeners.EventListeners>`. These :code:`EventListener` objects are requested when a message is received through a `websocket <https://quart.palletsprojects.com/en/latest/how_to_guides/websockets/>`_.
* Add an *producer callback* by using :func:`d3.event_producers().add_timer <detroit_live.events.event_producers.EventProducers.add_timer>`. It makes an infinite asynchronous task which exists as long as the :class:`TimerEvent <detroit_live.timer.timer.TimerEvent>` argument is not set. For each iteration during the infinite loop in the task, an update is sent to the `websocket <https://quart.palletsprojects.com/en/latest/how_to_guides/websockets/>`_.

Listener callbacks
******************

Listener callbacks are attached to selected nodes. They are defined as functions which take three parameters and return nothing:

* **event** (`Event`) - Event received by the :code:`websocket`. Most of the time, this event is a :class:`MouseEvent <detroit_live.events.types.MouseEvent>`. See :doc:`event types<api/events/event_types>` for predefined events.
* **d** (`Any | None`) - The data associated to the selected node
* **node** (`lxml.etree.Element`) - The selected node which has the event listener

For example, in the :doc:`example heatmap <heatmap>`, you must create listener callbacks when the mouse hovers an rectangle:

.. code:: python

   # <div> added in <body>
   tooltip = body.append("div").attr("class", "tooltip")

   # Listener callback
   def mouseover(event, d, node):
       tooltip.style("opacity", 1)
       d3.select(node).style("stroke", "black").style("opacity", 1)

Here, there are two nodes which are updated : :code:`node` from :code:`mouseover` function and :code:`tooltip` (global variable).

To create an event listener, you must call :func:`LiveSelection.on <detroit_live.selection.selection.LiveSelection.on>`:

.. code:: python

   svg.on("mouseover", mouseover, extra_nodes=[tooltip.node()])
   # or extra_nodes = tooltip.nodes()

The parameter :code:`extra_nodes` must be filled when there are additional nodes to update apart from the selected node :code:`node` (in this example, :code:`node != tooltip`).
Mouse events will be propagated into this function and **only attribute changes are updated**. In some cases, you want to update the inner HTML (or the text content of the element), you must fill the parameter :code:`html_nodes`:


.. code:: python

   svg.on(
     "mouseover",
     mouseover,
     extra_nodes=[tooltip.node()],
     html_nodes=[tooltip.node()],
   )

By default, only attributes are updated (i.e. :code:`node.attrib`). However, for performance reasons, inner HTML or text content are not automatically updated.

Producer callbacks
******************

Producers callbacks are functions called into infinite loop packed into asynchronous task. They are independant to selected nodes, and instead, you must specify which nodes must be updated by using the parameters :code:`updated_nodes` and :code:`html_nodes` like for event listeners.

Producer callbacks must have two arguments and returns nothing:

* **elapsed** (`float`) - The elapsed time since the timer started in milliseconds
* **timer_event** (:class:`TimerEvent <detroit_live.timer.timer.TimerEvent>`) -  A timer event which when it is set (by using :code:`timer_event.set()`), it stops the event producers.

Here is an example when you want to update:

.. code:: python

   date = 1800

   # Producer callback
   def update_date(elapsed, timer_event):
        global date
        if date == 2005:
            # Stop the timer
            timer_event.set()
            return

        date += 1
        current_data = data_at(datetime(date, 1, 1))
        (
            circle.data(current_data, lambda d: d.name)
            .attr("cx", lambda d: x(d.income))
            .attr("cy", lambda d: y(d.life_expectancy))
            .attr("r", lambda d: radius(d.population))
        )
        span.text(f"Year: {date}")

   event_producers = d3.event_producers()
   timer_modifier = event_producers.add_interval(
       update_date,
       updated_nodes=circle.nodes() + span.nodes(),
       html_nodes=span.nodes(),
       delay=50, # milliseconds
   )
  
   # timer_modifier.restart() to restart the timer
   # timer_modifier.stop() to stop the timer

In the function :code:`update_date`, :code:`circle` and :code:`span` nodes are updated. The parameter :code:`updated_nodes` must be filled in in order to send updates through :code:`websocket`. Also, in :code:`updated_date` function, the text content of :code:`span` nodes is updated. Like event listeners, you must indicate it by filling the :code:`html_nodes` parameter.

Run the application
*******************

Once you have added all necessary event listeners and event producers, you can start a web application to get interactivity:

.. code:: python
  
   svg.create_app().run()

Default host is :code:`localhost` and default port is :code:`5000`. You can open the web application in your browser at :code:`localhost:5000`.

Table of Content
----------------

.. toctree::
   :maxdepth: 2

   heatmap
   rainbow
   index_chart
   force_graph
   quadtree
   job_projections
   api/index
