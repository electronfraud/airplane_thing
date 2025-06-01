import asyncio

from aggregator.decoder.message import ModeSMessage
from aggregator.decoder.decoder import DecodingError, Decoder
from aggregator.log import log
from aggregator.runnable import Runnable


class ModeSIngester(Runnable):
    def __init__(self, out_queue: asyncio.Queue[ModeSMessage], host: str, port: int, decoder: Decoder):
        super().__init__()
        self._queue = out_queue
        self._host = host
        self._port = port
        self._decoder = decoder
        self._errors_seen: set[str] = set()

    async def step(self) -> None:
        reader, _ = await self._connect()
        if not reader:
            return
        while self.is_running():
            line = await reader.readline()
            if not line:
                log("connection closed unexpectedly")
                break
            try:
                decoded = self._decoder.decode(line[:-1])
            except DecodingError as exc:
                error = str(exc)
                if error not in self._errors_seen:
                    log(f"decoding error: {error} (future errors of this kind will be suppressed)")
                    self._errors_seen.add(error)
            else:
                self._queue.put_nowait(decoded)

    async def _connect(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter] | tuple[None, None]:
        while self.is_running():
            log(f"connecting to {self._host}:{self._port}")
            try:
                res = await asyncio.open_connection(self._host, self._port)
                log("connected")
                return res
            except ConnectionRefusedError:
                log("connection refused")
            except OSError as exc:
                log(f"OSError: {exc}")
            await asyncio.sleep(1)
        return None, None

    def stop(self) -> None:
        super().stop()
        self._queue.shutdown()
