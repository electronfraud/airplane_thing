import asyncio
from dataclasses import dataclass
import os
from typing import Any
from xml.etree import ElementTree

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


class SWIMIngester(Runnable, MessageHandler):
    """
    Ingests flight plan data from FAA SWIM.
    """

    def __init__(
        self, out_queue: asyncio.Queue[Flight], url: str, queue_name: str, username: str, password: str, vpn_name: str
    ):
        super().__init__()

        self._queue = out_queue
        self._url = url
        self._queue_name = queue_name
        self._receiver: PersistentMessageReceiver | None = None

        self._messaging_service = (
            MessagingService.builder()
            .from_properties(  # type: ignore
                {
                    "solace.messaging.transport.host": url,
                    "solace.messaging.service.vpn-name": vpn_name,
                    "solace.messaging.authentication.scheme.basic.username": username,
                    "solace.messaging.authentication.scheme.basic.password": password,
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
        raw_xml = message.get_payload_as_string() or ""
        xml_root = ElementTree.fromstring(raw_xml)
        if xml_root.tag != "{http://www.faa.aero/nas/3.0}MessageCollection":
            log(f"unexpected root element: {xml_root.tag}")
            log(raw_xml)
            return

        for message_tag in xml_root:
            message_type = message_tag.get("{http://www.w3.org/2001/XMLSchema-instance}type")
            if message_type != "ns5:FlightMessageType":
                log(f"unexpected message type: {message_type}")
                log(raw_xml)
                continue
            flight_tag = message_tag[0]
            flight_status = flight_tag.find("flightStatus").get("fdpsFlightStatus")
            if flight_status in ("COMPLETED", "DROPPED"):
                log("interesting flight status")
                log(raw_xml)
            if flight_status != "ACTIVE":  # type: ignore
                continue

            aircraft_desc_tag = flight_tag.find("aircraftDescription")
            if aircraft_desc_tag is None:
                log("schema violation")
                continue

            icao_address = aircraft_desc_tag.get("aircraftAddress", "").upper() or None
            flight_id_tag = flight_tag.find("flightIdentification")
            callsign = None if flight_id_tag is None else flight_id_tag.get("aircraftIdentification")
            registration = aircraft_desc_tag.get("registration")
            if not (icao_address or callsign or registration):
                continue

            # assigned_altitude = flight_tag.find("assignedAltitude/simple").text.strip()
            self._queue.put_nowait(
                Flight(
                    icao_address=ICAOAddress(icao_address) if icao_address else None,
                    callsign=callsign,
                    registration=registration,
                    icao_type=aircraft_desc_tag.find("aircraftType/icaoModelIdentifier").text.strip(),  # type: ignore
                    wake_category=aircraft_desc_tag.get("wakeTurbulence"),
                    cid=flight_tag.find("flightIdentification").get("computerId"),  # type: ignore
                    departure=flight_tag.find("departure").get("departurePoint"),  # type: ignore
                    route=flight_tag.find("agreed/route").get("nasRouteText"),  # type: ignore
                    arrival=flight_tag.find("arrival").get("arrivalPoint"),  # type: ignore
                    assigned_cruise_altitude=_assigned_altitude(flight_tag),
                )
            )


def _assigned_altitude(flight_tag: ElementTree.Element) -> int | None:
    simple_tag = flight_tag.find("assignedAltitude/simple")
    if simple_tag is None:
        return None
    return int((simple_tag.text or "").strip().removesuffix(".0"))
