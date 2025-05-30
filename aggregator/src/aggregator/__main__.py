import asyncio
import functools
import io
import os
import signal
import sys
import traceback

from aggregator import api
from aggregator import logging
from aggregator.correlator import Correlator
from aggregator.decoder import Decoder
from aggregator.ingester import Ingester
from aggregator.logging import log


async def main() -> int:
    logging.set_src_root(os.path.dirname(__file__))

    api_server = api.Server("", 9999)
    ingester = Ingester("radio", 30002, Decoder())
    correlator = Correlator(ingester.out_queue, api_server.update)

    def graceful_exit(signame: str) -> None:
        log(signame)
        api_server.stop()
        ingester.stop()
        correlator.stop()

    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(getattr(signal, signame), functools.partial(graceful_exit, signame))

    try:
        await asyncio.gather(api_server.run(), ingester.run(), correlator.run())
    except Exception as exc:  # pylint: disable=broad-exception-caught
        log("uncaught exception")
        traceback_buffer = io.StringIO()
        traceback.print_exception(exc, file=traceback_buffer)
        log(traceback_buffer.getvalue())
        return 1

    return 0


if __name__ == "__main__":
    _exit_status = asyncio.run(main())
    log(f"sys.exit({_exit_status})")
    sys.exit(_exit_status)
