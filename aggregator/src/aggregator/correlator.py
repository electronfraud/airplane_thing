import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from aggregator import decoder
from aggregator.logging import log
from aggregator.runnable import Runnable
from aggregator.util import ExpiringValue, LeakyDictionary


class Aircraft:
    def __init__(self, icao_address: str, expiry_secs: int = 10):
        self.icao_address = icao_address
        self._callsign = ExpiringValue[str](60)
        self._squawk = ExpiringValue[str](60)
        self._altitude = ExpiringValue[int](expiry_secs)
        self._position = ExpiringValue[tuple[float, float]](expiry_secs)
        self._ground_speed = ExpiringValue[int](expiry_secs)
        self._track = ExpiringValue[float](expiry_secs)
        self._vertical_speed = ExpiringValue[int](expiry_secs)

    def as_dict(self) -> dict[str, Any]:
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

        return result

    @property
    def callsign(self) -> str | None:
        return self._callsign.get()

    @callsign.setter
    def callsign(self, value: str) -> None:
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
        self, in_queue: asyncio.Queue[decoder.Message], update_cb: Callable[[Iterable[Aircraft]], Awaitable[None]]
    ):
        super().__init__()
        self._queue = in_queue
        self._update_cb = update_cb
        self.aircraft = LeakyDictionary[str, Aircraft](10)

    async def step(self) -> None:
        message = await self._queue.get()
        try:
            aircraft = self.aircraft[message.icao_address]
        except KeyError:
            aircraft = Aircraft(message.icao_address)

        match message:
            case decoder.SurveillanceReplyAltitudeMessage():
                aircraft.altitude = message.baro_pressure_altitude
            case decoder.SurveillanceReplyIdentityCodeMessage():
                aircraft.squawk = message.identity_code
            case decoder.ADSBIdentificationMessage():
                aircraft.callsign = message.callsign
            case decoder.ADSBAirbornePositionMessage():
                if message.altitude_type == decoder.AltitudeType.BARO_PRESSURE:
                    aircraft.altitude = message.altitude
                aircraft.position = message.position
            case decoder.ADSBAirborneVelocityMessage():
                aircraft.ground_speed = message.ground_speed
                aircraft.track = message.track
                aircraft.vertical_speed = message.vertical_speed
            case _:
                log(f"don't know about Message subclass {type(message).__name__}")

        self.aircraft[message.icao_address] = aircraft
        await self._update_cb(self.aircraft.values())
