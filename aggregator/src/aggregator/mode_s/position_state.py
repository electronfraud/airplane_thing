import time

import pyModeS

from aggregator.mode_s import DecodingError
from aggregator.model.icao_address import ICAOAddress
from aggregator.model.position import Position
from aggregator.util import EphemeralMap


class PositionState:
    def __init__(self, receiver_position: Position | None):
        if receiver_position is None:
            self._receiver_longitude = None
            self._receiver_latitude = None
        else:
            self._receiver_longitude = receiver_position.longitude
            self._receiver_latitude = receiver_position.latitude

        # These are known prior positions of aircraft, used to disambiguate position data in messages from aircraft
        # we've seen before. The 648-second expiration is based on pyModeS's requirement that prior position references
        # for airborne aircraft be within 180 nautical miles of the aircraft's presumed current position, and an
        # arbitrarily chosen maximum speed of 1000 knots, giving 180 nmi / 1000 kts = 648 s.
        self._prior_positions = EphemeralMap[ICAOAddress, Position](648)

        # These dictionaries store Compact Position Reporting (CPR) messages, used to disambiguate position data in
        # messages from aircraft whose position we haven't yet disambiguated. The first dictionary is for even messages
        # and the second is for odd messages. The 10-second expiration is convention.
        self._prior_cpr_msgs = (
            EphemeralMap[ICAOAddress, tuple[int, str]](10),
            EphemeralMap[ICAOAddress, tuple[int, str]](10),
        )

    def locate(self, icao_address: ICAOAddress, msg_hex: str) -> Position | None:
        """
        Try to extract an unambiguous position from a Mode S Extended Squitter (ADS-B) message.
        """
        try:
            ref_pos = self._prior_positions[icao_address]
        except KeyError:
            position = self._position_from_cpr_pair(icao_address, msg_hex)
        else:
            position = Position.from_lat_lon(
                pyModeS.adsb.position_with_ref(msg_hex, ref_pos.latitude, ref_pos.longitude)
            )

        if position is not None:
            self._prior_positions[icao_address] = position

        return position

    def _position_from_cpr_pair(self, icao_address: ICAOAddress, msg_hex: str) -> Position | None:
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
            lat_lon = pyModeS.adsb.position(msg0, msg1, t0, t1, self._receiver_latitude, self._receiver_longitude)
        except RuntimeError as exc:
            raise DecodingError("can't decode surface position without reference position") from exc

        return Position.from_lat_lon(lat_lon) if lat_lon is not None else None
