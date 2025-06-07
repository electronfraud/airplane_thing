import asyncio
from collections.abc import Awaitable, Iterable

import websockets
from websockets.asyncio.server import serve, ServerConnection, Server as WebsocketsServer

from aggregator.model.json import dumps
from aggregator.model.aircraft import Aircraft
from aggregator.log import log


class Client:
    def __init__(self, ws: ServerConnection):
        self._ws = ws


class Server:
    def __init__(self, listen_host: str, listen_port: int):
        self._listen_host = listen_host
        self._listen_port = listen_port
        self._server: WebsocketsServer | None = None
        self._clients: list[ServerConnection] = []

    async def run(self) -> None:
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

    def stop(self) -> None:
        if self._server:
            log("stopping")
            self._server.close()

    async def update(self, aircraft: Iterable[Aircraft]) -> None:
        message = dumps([a for a in aircraft if a.position is not None])
        futures: list[Awaitable[None]] = []
        for ws in self._clients:
            try:
                futures.append(ws.send(message))
            except websockets.WebSocketException as exc:
                print(exc)
        try:
            await asyncio.gather(*futures)
        except websockets.WebSocketException as exc:
            print(exc)
