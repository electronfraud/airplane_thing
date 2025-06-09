import asyncio
from typing import cast

from aggregator.decoder.message import ModeSMessage
from aggregator.decoder.decoder import DecodingError, Decoder
from aggregator.log import log
from aggregator.runnable import Runnable


class ModeSIngester(Runnable):
    """
    The Mode S ingester makes a TCP connection to a service that provides hex-formatted Mode S traffic, hands that
    traffic to a decoder (see the Decoder class and the ModeSMessage class hierarchy), and then delivers each decoded
    message to an asyncio Queue. Each message must be separated by a newline.

    If the ingester is unable to connect to the Mode S service, or the existing connection fails, the ingester retries
    the connection indefinitely.
    """

    def __init__(self, out_queue: asyncio.Queue[ModeSMessage], host: str, port: int, decoder: Decoder):
        super().__init__()
        self._queue = out_queue
        self._host = host
        self._port = port
        self._decoder = decoder
        self._errors_seen: set[str] = set()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def setup(self) -> None:
        while self.is_running():
            log(f"connecting to {self._host}:{self._port}")
            try:
                self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
                return
            except ConnectionRefusedError:
                log("connection refused")
            except OSError as exc:
                log(f"OSError: {exc}")
            await asyncio.sleep(1)

    async def step(self) -> None:
        line = await cast(asyncio.StreamReader, self._reader).readline()

        if not line:
            log("connection closed unexpectedly")
            await self.setup()
            return
        if not (line[0] == 0x2A and line[-2] == 0x3B):
            log(f"missing framing bytes: {line!r}")
            return

        try:
            decoded = self._decoder.decode(str(line[1:-2], encoding="ASCII"))
        except UnicodeDecodeError as exc:
            log(f"not 7-bit ASCII: {line!r}: {exc}")
            return
        except DecodingError as exc:
            error = str(exc)
            if error not in self._errors_seen:
                log(f"decoding error: {line!r}: {error} (future errors of this kind will be suppressed)")
                self._errors_seen.add(error)
            return

        try:
            self._queue.put_nowait(decoded)
        except asyncio.QueueShutDown:
            # If we get here this means the system is performing a graceful shutdown.
            pass

    async def teardown(self) -> None:
        if self._writer is not None:
            self._writer.close()
        self._reader = None
        self._writer = None
