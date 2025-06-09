import asyncio
from collections.abc import Awaitable, Callable, Iterable

from aggregator.decoder.message import (
    ADSBAirbornePositionMessage,
    ADSBAirborneVelocityMessage,
    ADSBIdentificationMessage,
    AltitudeType,
    CommBReply,
    ModeSMessage,
    SurveillanceReplyAltitudeMessage,
    SurveillanceReplyIdentityCodeMessage,
)
from aggregator.model.aircraft import Aircraft
from aggregator.model.flight import Flight
from aggregator.model.icao_address import ICAOAddress
from aggregator.runnable import Runnable
from aggregator.util import LeakyDictionary


class Correlator(Runnable):
    """
    Correlation is the last stage in the data pipeline before information is transmitted to the frontend. Mode S/ADS-B
    messages are merged to produce a complete picture of each aircraft, and flight data from FAA SWIM is attached to
    the appropriate aircraft to supplement the data receiver over RF. This combined data is then fed to the API server
    via a callback function.
    """

    def __init__(
        self,
        update_cb: Callable[[Iterable[Aircraft]], Awaitable[None]],
    ):
        super().__init__()

        self._update_cb = update_cb
        self._aircraft: LeakyDictionary[ICAOAddress, Aircraft] = LeakyDictionary(10)
        self._flights: dict[ICAOAddress, Flight] = {}

        self.in_queue: asyncio.Queue[ModeSMessage | Flight] = asyncio.Queue()

    async def step(self) -> None:
        match await self.in_queue.get():
            case ModeSMessage() as message:
                self._receive_mode_s(message)
            case Flight() as flight:
                self._receive_flight(flight)
        await self._update_cb(self._aircraft.values())
        self.in_queue.task_done()

    async def teardown(self) -> None:
        self.in_queue.shutdown(immediate=True)

    def _receive_mode_s(self, message: ModeSMessage) -> None:
        try:
            aircraft = self._aircraft[message.icao_address]
        except KeyError:
            aircraft = Aircraft(message.icao_address, flight=self._flights.get(message.icao_address))
            self._aircraft[message.icao_address] = aircraft

        match message:
            case SurveillanceReplyAltitudeMessage():
                aircraft.altitude = message.baro_pressure_altitude
            case SurveillanceReplyIdentityCodeMessage():
                aircraft.squawk = message.identity_code
            case ADSBIdentificationMessage():
                aircraft.callsign = message.callsign
            case ADSBAirbornePositionMessage():
                if message.altitude_type == AltitudeType.BARO_PRESSURE:
                    aircraft.altitude = message.altitude
                aircraft.position = message.position
            case ADSBAirborneVelocityMessage():
                aircraft.ground_speed = message.ground_speed
                aircraft.track = message.track
                aircraft.vertical_speed = message.vertical_speed
            case CommBReply():
                if message.altitude is not None:
                    aircraft.altitude = message.altitude
                if message.identity_code is not None:
                    aircraft.squawk = message.identity_code
                if message.callsign is not None:
                    aircraft.callsign = message.callsign

    def _receive_flight(self, flight: Flight) -> None:
        if flight.icao_address is None:
            return

        self._flights[flight.icao_address] = flight
        try:
            self._aircraft[flight.icao_address].flight = flight
        except KeyError:
            pass
