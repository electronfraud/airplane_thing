import asyncio
import functools
import io
import os
import signal
import sys
import traceback

from aggregator import api
import aggregator.log
from aggregator.correlator import Correlator
from aggregator.decoder import Decoder
from aggregator.log import log
from aggregator.mode_s_ingester import ModeSIngester
from aggregator.swim_ingester import SWIMIngester


async def main() -> int:
    aggregator.log.set_src_root(os.path.dirname(__file__))

    api_server = api.Server("", 9999)
    correlator = Correlator(api_server.update)
    mode_s_ingester = ModeSIngester(
        correlator.in_queue, os.environ["RADIO_HOST"], int(os.environ["RADIO_PORT"]), Decoder()  # type: ignore
    )
    swim_ingester = SWIMIngester(
        correlator.in_queue,  # type: ignore
        os.environ["SWIM_URL"],
        os.environ["SWIM_QUEUE"],
        os.environ["SWIM_USER"],
        os.environ["SWIM_PASSWORD"],
        os.environ["SWIM_VPN"]
    )

    def graceful_exit(signame: str) -> None:
        log(signame)
        api_server.stop()
        correlator.stop()
        mode_s_ingester.stop()
        swim_ingester.stop()

    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(getattr(signal, signame), functools.partial(graceful_exit, signame))

    try:
        await asyncio.gather(api_server.run(), correlator.run(), mode_s_ingester.run(), swim_ingester.run())
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
