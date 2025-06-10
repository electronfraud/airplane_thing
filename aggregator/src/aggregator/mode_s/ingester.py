import asyncio
from typing import cast

import pyModeS

from aggregator.log import log
from aggregator.mode_s import DecodingError
from aggregator.mode_s.message import (
    ADSBAirbornePositionMessage,
    ADSBAirborneVelocityMessage,
    ADSBIdentificationMessage,
    CommBReply,
    ModeSMessage,
    SurveillanceReplyAltitudeMessage,
    SurveillanceReplyIdentityCodeMessage,
)
from aggregator.mode_s.position_state import PositionState
from aggregator.model.position import Position
from aggregator.runnable import Runnable


class ModeSIngester(Runnable):
    """
    The Mode S ingester makes a TCP connection to a service that provides hex-formatted Mode S traffic, decodes that
    traffic, and then delivers each decoded message to an asyncio Queue. Each hex transmission must be separated by a
    newline.

    If the ingester is unable to connect to the Mode S service, or the existing connection fails, the ingester retries
    the connection indefinitely.
    """

    def __init__(
        self, out_queue: asyncio.Queue[ModeSMessage], host: str, port: int, receiver_position: Position | None = None
    ):
        super().__init__()
        self._queue = out_queue
        self._host = host
        self._port = port
        self._position_state = PositionState(receiver_position)
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
            decoded = self._decode(str(line[1:-2], encoding="ASCII"))
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

    def _decode(self, msg_hex: str) -> ModeSMessage:
        """
        This is the entry point to message decoding. `pkt` must be a Mode S message in ASCII hex--for example,
        "02e1971800755d". This is the format produced by dump1090 (not including the "*" and ";" framing bytes) when
        run with the --raw option. Returns a subclass of ModeSMessage, or if decoding fails, raises DecodingError.
        """
        df = pyModeS.df(msg_hex)
        match df:
            case 4:
                return SurveillanceReplyAltitudeMessage.from_hex(msg_hex)
            case 5:
                return SurveillanceReplyIdentityCodeMessage.from_hex(msg_hex)
            case 17:
                type_code = pyModeS.adsb.typecode(msg_hex)
                match type_code:
                    case 1 | 2 | 3 | 4:
                        return ADSBIdentificationMessage.from_hex(msg_hex)
                    case 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18:
                        return ADSBAirbornePositionMessage.from_hex(msg_hex, self._position_state)
                    case 19:
                        return ADSBAirborneVelocityMessage.from_hex(msg_hex)
                    case 20 | 21 | 22:
                        return ADSBAirbornePositionMessage.from_hex(msg_hex, self._position_state)
                    case _:
                        raise DecodingError(f"don't know how to decode ADS-B type code {type_code}")
            case 20 | 21:
                return CommBReply.from_hex(msg_hex)
            case _:
                raise DecodingError(f"don't know how to decode downlink format {df}")
