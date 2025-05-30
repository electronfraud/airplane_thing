"""
Decoder for messages received from dump1090. This is mostly just a wrapper around pyModeS.
"""

from enum import Enum
import time

import pyModeS

from aggregator.util import LeakyDictionary


class DecodingError(ValueError):
    pass


class Message:
    def __init__(self, icao_address: str):
        self.icao_address = icao_address


class SurveillanceReplyAltitudeMessage(Message):
    def __init__(self, icao_address: str, baro_pressure_altitude: int):
        super().__init__(icao_address)
        self.baro_pressure_altitude = baro_pressure_altitude


class SurveillanceReplyIdentityCodeMessage(Message):
    def __init__(self, icao_address: str, identity_code: str):
        super().__init__(icao_address)
        self.identity_code = identity_code


class ADSBIdentificationMessage(Message):
    def __init__(self, icao_address: str, callsign: str, wake_category: "WakeCategory"):
        super().__init__(icao_address)
        self.callsign = callsign
        self.aircraft_category = wake_category


class ADSBAirbornePositionMessage(Message):
    def __init__(
        self,
        icao_address: str,
        altitude: int,
        altitude_type: "AltitudeType",
        position: tuple[float, float] | None,
    ):
        super().__init__(icao_address)
        self.altitude = altitude
        self.altitude_type = altitude_type
        self.position = position


class ADSBAirborneVelocityMessage(Message):
    def __init__(self, icao_address: str, ground_speed: int, track: float, vertical_speed: int):
        super().__init__(icao_address)
        self.ground_speed = ground_speed
        self.track = track
        self.vertical_speed = vertical_speed


class AltitudeType(Enum):
    BARO_PRESSURE = 0  # barometric pressure altitude
    GNSS = 1


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


class DownlinkFormat(Enum):
    # fmt:off
    SURVEILLANCE_REPLY_ALTITUDE      =  4
    SURVEILLANCE_REPLY_IDENTITY_CODE =  5 # "identity code" means transponder code (squawk)
    EXTENDED_SQUITTER                = 17 # also known as ADS-B
    # fmt:on

    @classmethod
    def from_msg(cls, hex_msg: str) -> "DownlinkFormat":
        df = pyModeS.df(hex_msg)
        try:
            return cls(df)
        except ValueError as exc:
            raise DecodingError(f"don't know how to decode downlink format {df}") from exc


class Decoder:
    def __init__(self, receiver_longitude: float | None=None, receiver_latitude: float | None=None):
        self._receiver_longitude = receiver_longitude
        self._receiver_latitude = receiver_latitude
        # Prior positions of aircraft, used to disambiguate position data in messages from aircraft we've seen before.
        # This dictionary is ICAO address: (latitude, longitude). The 648-second expiration is based on pyModeS's
        # requirement that prior position references for airborne aircraft be within 180 nautical miles of the
        # aircraft's presumed current position, and an arbitrarily chosen maximum speed of 1000 knots. I.e.,
        # 180 nmi / 1000 kts = 648 s.
        self._prior_positions = LeakyDictionary[str, tuple[float, float]](648)
        # Prior Compact Position Reporting (CPR) messages, used to disambiguate position data in messages from aircraft
        # whose position we haven't yet disambiguated. These dictionaries are ICAO address: (timestamp, hex message);
        # the first dictionary is for even messages and the second is for odd. The 10-second expiration is convention.
        self._prior_cpr_msgs = (LeakyDictionary[str, tuple[int, str]](10), LeakyDictionary[str, tuple[int, str]](10))

    def decode(self, pkt: bytes) -> Message:
        """
        Decode a Mode S transmission. `pkt` must consist of hex digits framed by b"*" at the beginning and b";" at
        the end.
        """
        if not (pkt[0] == 0x2A and pkt[-1] == 0x3B):
            raise ValueError("missing framing bytes")

        msg_hex = str(pkt[1:-1], encoding="ASCII")
        icao_address = pyModeS.icao(msg_hex)
        if not icao_address:
            raise DecodingError(f"failed to extract ICAO address from {msg_hex}")
        icao_address = icao_address.lower()
        downlink_format = DownlinkFormat.from_msg(msg_hex)
        # TODO: transponder level

        match downlink_format:
            case DownlinkFormat.SURVEILLANCE_REPLY_ALTITUDE:
                return SurveillanceReplyAltitudeMessage(icao_address, pyModeS.altitude(pyModeS.hex2bin(msg_hex)[19:32]))
                # TODO: flight status, downlink request?, utility message?
            case DownlinkFormat.SURVEILLANCE_REPLY_IDENTITY_CODE:
                return SurveillanceReplyIdentityCodeMessage(icao_address, pyModeS.idcode(msg_hex))
                # TODO: flight status, downlink request?, utility message?
            case DownlinkFormat.EXTENDED_SQUITTER:
                type_code = pyModeS.adsb.typecode(msg_hex)
                match type_code:
                    case 1 | 2 | 3 | 4:
                        category = pyModeS.adsb.category(msg_hex)
                        try:
                            wake_category = WakeCategory((type_code, category))
                        except ValueError as exc:
                            raise DecodingError(
                                f"don't know what wake category type_code={type_code} and category={category} is"
                            ) from exc
                        return ADSBIdentificationMessage(
                            icao_address, pyModeS.adsb.callsign(msg_hex).rstrip("_"), wake_category
                        )
                    case 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18:
                        altitude = pyModeS.adsb.altitude(msg_hex)
                        if altitude is None:
                            raise DecodingError("invalid altitude")
                        return ADSBAirbornePositionMessage(
                            icao_address,
                            int(round(altitude)),
                            AltitudeType.BARO_PRESSURE,
                            self._position(icao_address, msg_hex),
                        )
                        # TODO: surveillance status, single antenna flag, time
                    case 19:
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
                        return ADSBAirborneVelocityMessage(icao_address, velocity[0], velocity[1], velocity[2])
                    case 20 | 21 | 22:
                        altitude = pyModeS.adsb.altitude(msg_hex)
                        if altitude is None:
                            raise DecodingError("invalid altitude")
                        return ADSBAirbornePositionMessage(
                            icao_address,
                            int(round(altitude)),
                            AltitudeType.GNSS,
                            self._position(icao_address, msg_hex),
                        )
                        # TODO: surveillance status, single antenna flag, time
                    case _:
                        raise DecodingError(f"don't know how to decode ADS-B type code {type_code}")

    def _position(self, icao_address: str, msg_hex: str) -> tuple[float, float] | None:
        """
        Try to extract an unambiguous position from a Mode S Extended Squitter (ADS-B) message.
        """
        try:
            lat_ref, lon_ref = self._prior_positions[icao_address]
        except KeyError:
            position = self._position_from_cpr_pair(icao_address, msg_hex)
        else:
            position = pyModeS.adsb.position_with_ref(msg_hex, lat_ref, lon_ref)

        if position is not None:
            self._prior_positions[icao_address] = position

        return position

    def _position_from_cpr_pair(self, icao_address: str, msg_hex: str) -> tuple[float, float] | None:
        timestamp = int(round(time.time()))
        odd_even_flag = pyModeS.adsb.oe_flag(msg_hex)

        try:
            prior_timestamp, prior_msg = self._prior_cpr_msgs[odd_even_flag ^ 1][icao_address]
        except KeyError:
            self._prior_cpr_msgs[odd_even_flag][icao_address] = (timestamp, msg_hex)
            return None

        if odd_even_flag == 0:
            msg0, msg1 = msg_hex, prior_msg
            t0, t1 = timestamp, prior_timestamp
        else:
            msg0, msg1 = prior_msg, msg_hex
            t0, t1 = prior_timestamp, timestamp

        try:
            position = pyModeS.adsb.position(msg0, msg1, t0, t1, self._receiver_latitude, self._receiver_longitude)
        except RuntimeError:
            raise DecodingError("can't decode surface position without reference position")

        return position
