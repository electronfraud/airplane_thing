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
from aggregator.runnable import Runnable
from aggregator.swim_ingester import SWIMIngester, SWIMIngesterConfig


async def main() -> int:
    aggregator.log.set_src_root(os.path.dirname(__file__))

    correlator = Correlator()
    runnables = [
        correlator,
        api.Server("", 9999, correlator),
        ModeSIngester(
            correlator.in_queue, os.environ["RADIO_HOST"], int(os.environ["RADIO_PORT"]), Decoder()  # type: ignore
        ),
    ]
    try:
        swim_config = SWIMIngesterConfig(
            os.environ["SWIM_URL"],
            os.environ["SWIM_QUEUE"],
            os.environ["SWIM_USER"],
            os.environ["SWIM_PASSWORD"],
            os.environ["SWIM_VPN"],
        )
    except KeyError as exc:
        log(f"{exc.args[0]} not set; no SWIM data will be ingested")
    else:
        runnables.append(SWIMIngester(correlator.in_queue, swim_config))  # type: ignore

    def graceful_shutdown(signame: str) -> None:
        log(signame)
        [r.stop() for r in runnables]

    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(getattr(signal, signame), functools.partial(graceful_shutdown, signame))

    try:
        await asyncio.gather(*[r.run() for r in runnables])
    except Exception as exc:  # pylint: disable=broad-exception-caught
        log("uncaught exception")
        traceback_buffer = io.StringIO()
        traceback.print_exception(exc, file=traceback_buffer)
        log(traceback_buffer.getvalue())
        return os.EX_SOFTWARE

    return os.EX_OK


if __name__ == "__main__":
    _exit_status = asyncio.run(main())
    log(f"sys.exit({_exit_status})")
    sys.exit(_exit_status)
