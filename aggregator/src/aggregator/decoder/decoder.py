"""
Decoder for messages received from dump1090. This is mostly just a wrapper around pyModeS.
"""

import pyModeS

from aggregator.decoder.message import (
    ADSBAirbornePositionMessage,
    ADSBAirborneVelocityMessage,
    ADSBIdentificationMessage,
    CommBReply,
    DecodingError,
    ModeSMessage,
    SurveillanceReplyAltitudeMessage,
    SurveillanceReplyIdentityCodeMessage,
)
from aggregator.decoder.position import PositionDisambiguator


class Decoder:
    """
    Decodes Mode S messages.
    """

    def __init__(self, receiver_longitude: float | None = None, receiver_latitude: float | None = None):
        self._position_disambiguator = PositionDisambiguator(receiver_longitude, receiver_latitude)

    def decode(self, pkt: bytes) -> ModeSMessage:
        """
        Decode a Mode S transmission. `pkt` must consist of hex digits framed by b"*" at the beginning and b";" at
        the end.
        """
        if not (pkt[0] == 0x2A and pkt[-1] == 0x3B):
            raise ValueError("missing framing bytes")

        msg_hex = str(pkt[1:-1], encoding="ASCII")

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
                        return ADSBAirbornePositionMessage.from_hex(msg_hex, self._position_disambiguator)
                    case 19:
                        return ADSBAirborneVelocityMessage.from_hex(msg_hex)
                    case 20 | 21 | 22:
                        return ADSBAirbornePositionMessage.from_hex(msg_hex, self._position_disambiguator)
                    case _:
                        raise DecodingError(f"don't know how to decode ADS-B type code {type_code}")
            case 20 | 21:
                return CommBReply.from_hex(msg_hex)
            case _:
                raise DecodingError(f"don't know how to decode downlink format {df}")
