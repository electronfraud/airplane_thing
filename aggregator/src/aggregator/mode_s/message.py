"""
These are the objects returned by Decoder's `decode` method, and the exception it raises when decoding fails.
"""

from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Self

from aggregator.mode_s import DecodingError
from aggregator.mode_s.position_state import PositionState
import pyModeS

from aggregator.model.icao_address import ICAOAddress
from aggregator.model.position import Position


@dataclass
class ModeSMessage(ABC):
    """
    Base class for all decoded messages. Every message has an ICAO address, a unique 24-bit address that is assigned to
    an aircraft as part of its registration.
    """

    icao_address: ICAOAddress


@dataclass
class SurveillanceReplyAltitudeMessage(ModeSMessage):
    """
    A Mode S surveillance reply with altitude information. Represents downlink format 4.
    """

    baro_pressure_altitude: int

    @classmethod
    def from_hex(cls, msg_hex: str) -> Self:
        # TODO: flight status, downlink request?, utility message?
        return cls(_icao_address(msg_hex), pyModeS.altitude(pyModeS.hex2bin(msg_hex)[19:32]))


@dataclass
class SurveillanceReplyIdentityCodeMessage(ModeSMessage):
    """
    A Mode S surveillance reply with identity information. Represents downlink format 5.
    """

    identity_code: str

    @classmethod
    def from_hex(cls, msg_hex: str) -> Self:
        # TODO: flight status, downlink request?, utility message?
        try:
            return cls(_icao_address(msg_hex), pyModeS.idcode(msg_hex))
        except RuntimeError as exc:
            raise DecodingError(f"pyModeS exception: {exc}") from exc


class WakeCategory(Enum):
    SURFACE_EMERGENCY_VEHICLE = (2, 1)
    SURFACE_SERVICE_VEHICLE = (2, 3)
    GROUND_OBSTRUCTION = (2, 4)
    GLIDER = (3, 1)
    LIGHTER_THAN_AIR = (3, 2)
    PARACHUTIST = (3, 3)
    ULTRALIGHT = (3, 4)
    UAV = (3, 6)
    SPACE_VEHICLE = (3, 7)
    LIGHT = (4, 1)
    MEDIUM_1 = (4, 2)
    MEDIUM_2 = (4, 3)
    HIGH_VORTEX = (4, 4)
    HEAVY = (4, 5)
    HIGH_PERF_HIGH_SPEED = (4, 6)
    ROTOCRAFT = (4, 7)


@dataclass
class ADSBIdentificationMessage(ModeSMessage):
    """
    An ADS-B message with callsign and wake category information. Represents downlink format 17, type codes 1-4.
    """

    callsign: str
    wake_category: WakeCategory

    @classmethod
    def from_hex(cls, msg_hex: str) -> Self:
        type_code = pyModeS.adsb.typecode(msg_hex)
        category = pyModeS.adsb.category(msg_hex)
        try:
            wake_category = WakeCategory((type_code, category))
        except ValueError as exc:
            raise DecodingError(
                f"don't know what wake category type_code={type_code} and category={category} is"
            ) from exc
        return cls(_icao_address(msg_hex), pyModeS.adsb.callsign(msg_hex).rstrip("_"), wake_category)


class AltitudeType(Enum):
    BARO_PRESSURE = 0  # barometric pressure altitude
    GNSS = 1


@dataclass
class ADSBAirbornePositionMessage(ModeSMessage):
    """
    An ADS-B message with altitude and position information. Represents downlink format 17, type codes 9-18 and 20-22.
    """

    altitude: int
    altitude_type: AltitudeType
    position: Position | None

    @classmethod
    def from_hex(cls, msg_hex: str, position_state: PositionState) -> Self:
        # TODO: surveillance status, single antenna flag, time?
        altitude = pyModeS.adsb.altitude(msg_hex)
        type_code = pyModeS.adsb.typecode(msg_hex)
        if altitude is None:
            raise DecodingError("invalid altitude")
        icao_address = _icao_address(msg_hex)
        return cls(
            icao_address,
            int(round(altitude)),
            AltitudeType.BARO_PRESSURE if type_code < 19 else AltitudeType.GNSS,  # type: ignore
            position_state.locate(icao_address, msg_hex),
        )


@dataclass
class ADSBAirborneVelocityMessage(ModeSMessage):
    """
    An ADS-B message with ground speed, track, and vertical speed information. Represents downlink format 17, type
    code 19.
    """

    ground_speed: int
    track: float
    vertical_speed: int

    @classmethod
    def from_hex(cls, msg_hex: str) -> Self:
        velocity = pyModeS.adsb.airborne_velocity(msg_hex)
        if velocity is None:
            raise DecodingError("failed to decode airborne velocity")
        if velocity[3] != "GS":
            raise DecodingError("airborne velocity message is not ground speed")
        if velocity[0] is None:
            raise DecodingError("airborne velocity message is missing ground speed")
        if velocity[1] is None:
            raise DecodingError("airborne velocity message is missing track")
        if velocity[2] is None:
            raise DecodingError("airborne velocity message is missing vertical speed")
        return cls(_icao_address(msg_hex), velocity[0], velocity[1], velocity[2])


@dataclass
class CommBReply(ModeSMessage):
    """
    A Mode S reply with variable information. Represents downlink formats 20 and 21.
    """

    altitude: int | None
    identity_code: str | None
    callsign: str | None

    @classmethod
    def from_hex(cls, msg_hex: str) -> Self:
        result = cls(_icao_address(msg_hex), None, None, None)
        try:
            result.identity_code = pyModeS.idcode(msg_hex)
        except RuntimeError:
            result.altitude = pyModeS.altitude(pyModeS.hex2bin(msg_hex)[19:32])
        for bds in (pyModeS.bds.infer(msg_hex) or "").split(","):
            match bds:
                case "BDS20":
                    result.callsign = pyModeS.commb.cs20(msg_hex).rstrip("_")
                case "BDS10" | "EMPTY":
                    pass
                case _:
                    raise DecodingError(f"don't know how to decode Comm-B reply with {bds}")
        return result


def _icao_address(msg_hex: str) -> ICAOAddress:
    raw = pyModeS.icao(msg_hex)
    if not raw:
        raise DecodingError(f"failed to extract ICAO address from {msg_hex}")
    return ICAOAddress(raw)
