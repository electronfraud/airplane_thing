import asyncio
from collections.abc import Awaitable

from aggregator.correlator import Correlator
from aggregator.runnable import Runnable
import websockets
from websockets.asyncio.server import serve, ServerConnection, Server as WebsocketsServer

from aggregator.model.json import dumps
from aggregator.log import log


class Client:
    def __init__(self, ws: ServerConnection):
        self._ws = ws


class Server(Runnable):
    def __init__(self, listen_host: str, listen_port: int, correlator: Correlator):
        super().__init__()
        self._listen_host = listen_host
        self._listen_port = listen_port
        self._correlator = correlator
        self._server: WebsocketsServer | None = None
        self._clients: list[ServerConnection] = []

    async def setup(self) -> None:
        asyncio.create_task(self._serve())

    async def step(self) -> None:
        # Wait for new data to arrive, or for one second to pass, whichever comes first.
        try:
            async with asyncio.timeout(1):
                await self._correlator.new_data_event.wait()
        except TimeoutError:
            pass

        # Send a message with all known aircraft to the frontend clients.
        message = dumps([a for a in self._correlator.aircraft.values() if a.position is not None])

        futures: list[Awaitable[None]] = []
        try:
            for ws in self._clients:
                futures.append(ws.send(message))
            await asyncio.gather(*futures)
        except websockets.WebSocketException as exc:
            print(f"websocket exception: {exc}")

    async def teardown(self) -> None:
        if self._server:
            self._server.close()

    async def _serve(self) -> None:
        async with serve(self._handler, self._listen_host, self._listen_port) as server:
            log(f"listening on {self._listen_host}:{self._listen_port}")
            self._server = server
            await server.wait_closed()
        log("stopped listening")

    async def _handler(self, ws: ServerConnection) -> None:
        log(f"{ws.remote_address[0]}:{ws.remote_address[1]}: connection established")
        self._clients.append(ws)
        await ws.wait_closed()
        self._clients.remove(ws)
        log(f"{ws.remote_address[0]}:{ws.remote_address[1]}: connection closed")
