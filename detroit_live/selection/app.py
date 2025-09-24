import asyncio
import os
import signal
import warnings
from typing import Any

from quart import Quart
from quart.app import _cancel_all_tasks
from quart.helpers import get_debug_flag
from quart.utils import MustReloadError, observe_changes, restart


class App(Quart):
    _host = None
    _port = None

    def run(
        self,
        debug: bool | None = None,
        use_reloader: bool = True,
        loop: asyncio.AbstractEventLoop | None = None,
        ca_certs: str | None = None,
        certfile: str | None = None,
        keyfile: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Run this application.

        This is best used for development only, see Hypercorn for production
        servers.

        Parameters
        ----------
        debug : bool | None
            If set enable (or disable) debug mode and debug output.
        use_reloader : bool
            Automatically reload on code changes.
        loop : asyncio.AbstractEventLoop | None
            Asyncio loop to create the server in, if None, take default one. If
            specified it is the caller's responsibility to close and cleanup
            the loop.
        ca_certs : str | None
            Path to the SSL CA certificate file.
        certfile : str | None
            Path to the SSL certificate file.
        keyfile : str | None
            Path to the SSL key file.
        """
        if kwargs:
            warnings.warn(
                f"Additional arguments, {','.join(kwargs.keys())}, are not supported.\n"
                "They may be supported by Hypercorn, which is the ASGI server Quart "
                "uses by default. This method is meant for development and debugging.",
                stacklevel=2,
            )

        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if "QUART_DEBUG" in os.environ:
            self.debug = get_debug_flag()

        if debug is not None:
            self.debug = debug

        loop.set_debug(self.debug)

        shutdown_event = asyncio.Event()

        def _signal_handler(*_: Any) -> None:
            # Patch from https://github.com/tf198/quart/commit/a6a9ec1e5bdaa4d5e410b4150fa95b5d870af262
            # See discussions in https://github.com/python/cpython/issues/123720
            # and the issue https://github.com/pallets/quart/issues/333
            for task in asyncio.all_tasks():
                if task.get_coro().__name__ in ["handle_websocket", "handle_request"]:
                    task.cancel()
            shutdown_event.set()

        for signal_name in {"SIGINT", "SIGTERM", "SIGBREAK"}:
            if hasattr(signal, signal_name):
                try:
                    loop.add_signal_handler(
                        getattr(signal, signal_name), _signal_handler
                    )
                except NotImplementedError:
                    # Add signal handler may not be implemented on Windows
                    signal.signal(getattr(signal, signal_name), _signal_handler)

        server_name = self.config.get("SERVER_NAME")
        sn_host = None
        sn_port = None
        if server_name is not None:
            sn_host, _, sn_port = server_name.partition(":")

        host = self._host or sn_host or "127.0.0.1"
        port = self._port or int(sn_port or "5000")

        task = self.run_task(
            host,
            port,
            debug,
            ca_certs,
            certfile,
            keyfile,
            shutdown_trigger=shutdown_event.wait,  # type: ignore
        )
        print(f" * Serving Quart app '{self.name}'")  # noqa: T201
        print(f" * Debug mode: {self.debug or False}")  # noqa: T201
        print(" * Please use an ASGI server (e.g. Hypercorn) directly in production")  # noqa: T201
        scheme = "https" if certfile is not None and keyfile is not None else "http"
        print(f" * Running on {scheme}://{host}:{port} (CTRL + C to quit)")  # noqa: T201

        tasks = [loop.create_task(task)]

        if use_reloader:
            tasks.append(
                loop.create_task(observe_changes(asyncio.sleep, shutdown_event))
            )

        reload_ = False
        try:
            loop.run_until_complete(asyncio.gather(*tasks))
        except MustReloadError:
            reload_ = True
        finally:
            try:
                _cancel_all_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                asyncio.set_event_loop(None)
                loop.close()

        if reload_:
            restart()
