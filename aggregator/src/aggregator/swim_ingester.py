import asyncio
from dataclasses import dataclass
import traceback
from typing import Any, cast

from lxml import etree
from solace.messaging.config.transport_security_strategy import TLS  # type: ignore
from solace.messaging.config.retry_strategy import RetryStrategy  # type: ignore
from solace.messaging.messaging_service import MessagingService  # type: ignore
from solace.messaging.receiver.inbound_message import InboundMessage  # type: ignore
from solace.messaging.receiver.message_receiver import MessageHandler  # type: ignore
from solace.messaging.receiver.persistent_message_receiver import PersistentMessageReceiver  # type: ignore
from solace.messaging.resources.queue import Queue  # type: ignore

from aggregator.log import log
from aggregator.model.flight import Flight
from aggregator.model.icao_address import ICAOAddress
from aggregator.runnable import Runnable
from aggregator.util import as_asyncio


_NAS30_URI = "http://www.faa.aero/nas/3.0"
_NAS30 = "{" + _NAS30_URI + "}"
_XSI_URI = "http://www.w3.org/2001/XMLSchema-instance"
_XSI = "{" + _XSI_URI + "}"


@dataclass
class SWIMIngesterConfig:
    url: str
    queue_name: str
    username: str
    password: str
    vpn_name: str


class SWIMIngester(Runnable, MessageHandler):
    """
    Ingests flight plan data from FAA SWIM.
    """

    def __init__(self, out_queue: asyncio.Queue[Flight], config: SWIMIngesterConfig):
        super().__init__()

        self._queue = out_queue
        self._url = config.url
        self._queue_name = config.queue_name
        self._receiver: PersistentMessageReceiver | None = None

        self._messaging_service = (
            MessagingService.builder()
            .from_properties(  # type: ignore
                {
                    "solace.messaging.transport.host": config.url,
                    "solace.messaging.service.vpn-name": config.vpn_name,
                    "solace.messaging.authentication.scheme.basic.username": config.username,
                    "solace.messaging.authentication.scheme.basic.password": config.password,
                }
            )
            .with_reconnection_retry_strategy(RetryStrategy.forever_retry(1000))
            .with_transport_security_strategy(
                TLS.create().with_certificate_validation(False, trust_store_file_path="/etc/ssl/certs")
            )
            .build()
        )

    async def setup(self) -> None:
        log(f"connecting to {self._url}")
        await as_asyncio(self._messaging_service.connect_async())  # type: ignore
        log("connected")

        queue = Queue.durable_non_exclusive_queue(self._queue_name)
        self._receiver = self._messaging_service.create_persistent_message_receiver_builder().build(queue)
        await as_asyncio(self._receiver.start_async())  # type: ignore

        self._receiver.receive_async(self)  # type: ignore

    async def step(self) -> None:
        await asyncio.sleep(1)

    async def teardown(self) -> None:
        log("terminating receiver")
        await as_asyncio(self._receiver.terminate_async())  # type: ignore

    def on_message(self, message: InboundMessage) -> None:
        # Solace "helpfully" catches all exceptions raised in callbacks and prints terribly unhelpful messages, so we
        # have to catch and print the information we need ourselves.
        try:
            self._on_message(message)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            for line in traceback.format_exception(exc):
                log(line)

    def _on_message(self, message: InboundMessage) -> None:
        self._receiver.ack(message)

        raw_xml = bytes(message.get_payload_as_bytes() or b"")
        try:
            root = cast(etree._Element, etree.fromstring(raw_xml))
        except etree.XMLSyntaxError as exc:
            log(f"XML syntax error: {exc}")
            return

        assert root.tag == f"{_NAS30}MessageCollection"
        assert len(root) == 1
        assert root[0].tag == "message"
        assert len(root[0]) == 1

        flight_tag = root[0][0]

        assert flight_tag.tag == "flight"
        nas30_prefix = {v: k for k, v in root.nsmap.items()}[_NAS30_URI]
        assert flight_tag.get(f"{_XSI}type") == f"{nas30_prefix}:NasFlightType"

        if flight_tag.find("flightStatus").get("fdpsFlightStatus") != "ACTIVE":
            return

        aircraft_desc_tag = flight_tag.find("aircraftDescription")
        flight_id_tag = flight_tag.find("flightIdentification")

        icao_address = aircraft_desc_tag.get("aircraftAddress")
        callsign = flight_id_tag.get("aircraftIdentification")
        registration = aircraft_desc_tag.get("registration")

        if not (icao_address or callsign or registration):
            return

        try:
            self._queue.put_nowait(
                Flight(
                    icao_address=ICAOAddress(icao_address) if icao_address else None,
                    callsign=callsign,
                    registration=registration,
                    icao_type=aircraft_desc_tag.find("aircraftType/icaoModelIdentifier").text.strip(),
                    wake_category=aircraft_desc_tag.get("wakeTurbulence"),
                    cid=flight_id_tag.get("computerId"),
                    departure=flight_tag.find("departure").get("departurePoint"),
                    route=flight_tag.find("agreed/route").get("nasRouteText"),
                    arrival=flight_tag.find("arrival").get("arrivalPoint"),
                    assigned_cruise_altitude=_assigned_cruise_altitude(flight_tag),
                )
            )
        except asyncio.QueueShutDown:
            # If we get here this means the system is performing a graceful shutdown.
            pass


def _assigned_cruise_altitude(flight_tag: Any) -> int | None:
    simple_tag = flight_tag.find("assignedAltitude/simple")
    if simple_tag is None:
        return None
    return int(simple_tag.text.strip().removesuffix(".0"))
