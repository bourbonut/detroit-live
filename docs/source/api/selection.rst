Selection
=========

Selection
---------

.. note::

   All methods, from `detroit.selection.Selection <https://detroit.readthedocs.io/en/latest/api/selection.html#detroit.selection.selection.Selection>`_, remain the same for :class:`LiveSelection <detroit_live.selection.selection.LiveSelection>` (except it returns a :code:`LiveSelection` and not a :code:`Selection`).

.. autofunction:: detroit_live.create
.. autofunction:: detroit_live.select

.. autoclass:: detroit_live.selection.selection.LiveSelection

   .. automethod:: on
   .. automethod:: set_event
   .. automethod:: create_app

Quart Application
-----------------

The following class inherits from `quart.app.Quart <https://quart.palletsprojects.com/en/latest/reference/source/quart.app/#quart.app.Quart>`_ class and has almost the same behavior. The only thing changed is its :code:`signal_handler` function :

.. code:: python

    def _signal_handler(*_: Any) -> None:
        # Patch from https://github.com/tf198/quart/commit/a6a9ec1e5bdaa4d5e410b4150fa95b5d870af262
        # See discussions in https://github.com/python/cpython/issues/123720
        # and the issue https://github.com/pallets/quart/issues/333
        for task in asyncio.all_tasks():
            if task.get_coro().__name__ in ["handle_websocket", "handle_request"]:
                task.cancel()
        shutdown_event.set()

This modification helps to have a better graceful exit.

.. autoclass:: detroit_live.selection.app.App

   .. automethod:: run


.. note::

   The parameters :code:`host` and :code:`port` from the original signature are passed through attributes to avoid copied arguments in :func:`LiveSelection.create_app <detroit_live.selection.selection.LiveSelection.create_app>` and :code:`App.run`.
