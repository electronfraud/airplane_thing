import asyncio

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
from aggregator.util import EphemeralMap


class Correlator(Runnable):
    """
    Correlation is the last stage in the data pipeline before information is transmitted to the frontend. The
    Correlator instance receives ModeSMessage and Flight objects through its `in_queue`, an asyncio Queue. Mode S
    messages are merged to produce a complete picture of each aircraft, and flight data is attached to the appropriate
    aircraft to supplement the data received over RF. The correlator then sets its `new_data_event` asyncio Event to
    notify interested parties (in practice, the API server) that its data has changed.

    Correlated data is ephemeral. Each field in a Aircraft object has a limited lifetime, and Aircraft objects are
    removed from the correlator's in-memory database after an hour passes with no messages about the aircraft. No event
    is sent when this happens.
    """

    def __init__(self):
        super().__init__()

        self.in_queue: asyncio.Queue[ModeSMessage | Flight] = asyncio.Queue()
        self.new_data_event = asyncio.Event()

        self.aircraft: EphemeralMap[ICAOAddress, Aircraft] = EphemeralMap(60 * 60)
        self._flights: dict[ICAOAddress, Flight] = {}

    async def step(self) -> None:
        self.new_data_event.clear()

        match await self.in_queue.get():
            case ModeSMessage() as message:
                self._receive_mode_s(message)
            case Flight() as flight:
                self._receive_flight(flight)

        self.new_data_event.set()
        self.in_queue.task_done()

    async def teardown(self) -> None:
        self.in_queue.shutdown(immediate=True)
        self.new_data_event.set()

    def _receive_mode_s(self, message: ModeSMessage) -> None:
        try:
            aircraft = self.aircraft[message.icao_address]
        except KeyError:
            aircraft = Aircraft(message.icao_address, flight=self._flights.get(message.icao_address))
        self.aircraft[message.icao_address] = aircraft

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
            self.aircraft[flight.icao_address].flight = flight
        except KeyError:
            pass
