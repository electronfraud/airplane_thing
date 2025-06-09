"""
Decoder for messages received from dump1090. This is mostly just a wrapper around pyModeS.
"""

import pyModeS

from aggregator.decoder.message import (
    ADSBAirbornePositionMessage,
    ADSBAirborneVelocityMessage,
    ADSBIdentificationMessage,
    CommBReply,
    ModeSMessage,
    SurveillanceReplyAltitudeMessage,
    SurveillanceReplyIdentityCodeMessage,
)
from aggregator.decoder.position_state import PositionState


class DecodingError(ValueError):
    """
    Exception raised for any failure to decode a Mode S message.
    """


class Decoder:
    """
    The decoder takes Mode S messages in ASCII hex format and turns them into easy-to-use objects, specifically
    instances of subclasses of ModeSMessage. If a message can't be decoded, the decoder raises a DecodingError.
    """

    def __init__(self, receiver_longitude: float | None = None, receiver_latitude: float | None = None):
        self._position_state = PositionState(receiver_longitude, receiver_latitude)

    def decode(self, msg_hex: str) -> ModeSMessage:
        """
        This is the entry point to message decoding. `pkt` must be a Mode S message in ASCII hex--for example,
        "02e1971800755d". This is the format produced by dump1090 (not including the "*" and ";" framing bytes) when
        run with the --raw option. Returns a subclass of ModeSMessage, or if decoding fails, raises DecodingError.
        """
        df = pyModeS.df(msg_hex)
        match df:
            case 4:
                return SurveillanceReplyAltitudeMessage.from_hex(msg_hex)
            case 5:
                return SurveillanceReplyIdentityCodeMessage.from_hex(msg_hex)
            case 17:
                type_code = pyModeS.adsb.typecode(msg_hex)
                match type_code:
                    case 1 | 2 | 3 | 4:
                        return ADSBIdentificationMessage.from_hex(msg_hex)
                    case 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18:
                        return ADSBAirbornePositionMessage.from_hex(msg_hex, self._position_state)
                    case 19:
                        return ADSBAirborneVelocityMessage.from_hex(msg_hex)
                    case 20 | 21 | 22:
                        return ADSBAirbornePositionMessage.from_hex(msg_hex, self._position_state)
                    case _:
                        raise DecodingError(f"don't know how to decode ADS-B type code {type_code}")
            case 20 | 21:
                return CommBReply.from_hex(msg_hex)
            case _:
                raise DecodingError(f"don't know how to decode downlink format {df}")
