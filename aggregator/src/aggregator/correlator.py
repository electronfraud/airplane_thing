"""
Correlation is the last stage in the data pipeline before information is transmitted to the frontend. Mode S/ADS-B
messages are merged to produce a complete picture of each aircraft, and flight data from FAA SWIM is associated with
the appropriate aircraft to supplement the RF messages. This correlated data is then fed to the API server via a
callback function.

The primary key of every aircraft is their ICAO address, also known as a Mode S address or hex code. This address is
a permanent(?), globally(?) unique 24-bit identifier that is present in all Mode S transmissions. Its canonical
representation, at least as far as this software is concerned, is six uppercase hexadecimal digits.
"""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

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
from aggregator.log import log
from aggregator.model import ICAOAddress
from aggregator.runnable import Runnable
from aggregator.swim_ingester import Flight
from aggregator.util import ExpiringValue, LeakyDictionary


class Aircraft:
    """
    Represents an operating aircraft, which may be in flight or on the surface. Each Aircraft object is the result of
    merging data from multiple Mode S/ADS-S messages and FAA SWIM flight messages, filtered through expiration rules.
    An Aircraft object's properties also have individual expiration policies; reading the `altitude` property twice at
    different times, for example, may produce an integer the first time and `None` the second time. The correlator
    retains references to Aircraft objects that it manages, so properties may also be updated as new messages arrive.
    """

    def __init__(self, icao_address: ICAOAddress, expiry_secs: int = 10):
        self.icao_address = icao_address
        self._callsign = ExpiringValue[str](60 * 5)
        self._squawk = ExpiringValue[str](60 * 5)
        self._altitude = ExpiringValue[int](expiry_secs)
        self._position = ExpiringValue[tuple[float, float]](expiry_secs)
        self._ground_speed = ExpiringValue[int](expiry_secs)
        self._track = ExpiringValue[float](expiry_secs)
        self._vertical_speed = ExpiringValue[int](expiry_secs)
        self.flight_plan: Flight | None = None

    def as_dict(self) -> dict[str, Any]:
        """
        Create a dictionary representation of this Aircraft. The dictionary contains only properties whose values are
        not `None`.
        """
        result: dict[str, Any] = {"icao_address": self.icao_address}

        callsign = self.callsign
        if callsign is not None:
            result["callsign"] = callsign

        squawk = self.squawk
        if squawk is not None:
            result["squawk"] = squawk

        altitude = self.altitude
        if altitude is not None:
            result["altitude"] = altitude

        position = self.position
        if position is not None:
            result["position"] = list(position)

        ground_speed = self.ground_speed
        if ground_speed is not None:
            result["ground_speed"] = ground_speed

        track = self.track
        if track is not None:
            result["track"] = track

        vertical_speed = self.vertical_speed
        if vertical_speed is not None:
            result["vertical_speed"] = vertical_speed

        flight_plan = self.flight_plan
        if flight_plan is not None:
            result["flight_plan"] = flight_plan.as_dict()

        return result

    @property
    def callsign(self) -> str | None:
        return self._callsign.get()

    @callsign.setter
    def callsign(self, value: str | None) -> None:
        self._callsign.set(value)

    @property
    def squawk(self) -> str | None:
        return self._squawk.get()

    @squawk.setter
    def squawk(self, value: str) -> None:
        self._squawk.set(value)

    @property
    def altitude(self) -> int | None:
        return self._altitude.get()

    @altitude.setter
    def altitude(self, value: int) -> None:
        self._altitude.set(value)

    @property
    def position(self) -> tuple[float, float] | None:
        return self._position.get()

    @position.setter
    def position(self, value: tuple[float, float] | None) -> None:
        self._position.set(value)

    @property
    def ground_speed(self) -> int | None:
        return self._ground_speed.get()

    @ground_speed.setter
    def ground_speed(self, value: int) -> None:
        self._ground_speed.set(value)

    @property
    def track(self) -> float | None:
        return self._track.get()

    @track.setter
    def track(self, value: float) -> None:
        self._track.set(value)

    @property
    def vertical_speed(self) -> int | None:
        return self._vertical_speed.get()

    @vertical_speed.setter
    def vertical_speed(self, value: int) -> None:
        self._vertical_speed.set(value)


class Correlator(Runnable):
    def __init__(
        self,
        update_cb: Callable[[Iterable[Aircraft]], Awaitable[None]],
    ):
        super().__init__()
        self.in_queue: asyncio.Queue[ModeSMessage | Flight] = asyncio.Queue[ModeSMessage | Flight]()
        self._update_cb = update_cb
        self.aircraft: LeakyDictionary[str, Aircraft] = LeakyDictionary(10)
        self.flights: dict[str, Flight] = {}

    async def step(self) -> None:
        message = await self.in_queue.get()
        if message.icao_address is None:
            return
        try:
            aircraft = self.aircraft[message.icao_address]
        except KeyError:
            aircraft = Aircraft(message.icao_address)
            aircraft.flight_plan = self.flight_plans.get(message.icao_address)
            if aircraft.flight_plan:
                aircraft.callsign = aircraft.flight_plan.callsign

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
            case Flight():
                aircraft.flight_plan = message
                self.flight_plans[message.icao_address] = message
            case _:
                log(f"don't know about message class {type(message).__name__}")

        self.aircraft[message.icao_address] = aircraft
        await self._update_cb(self.aircraft.values())
