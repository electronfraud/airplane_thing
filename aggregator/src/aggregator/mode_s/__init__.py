from aggregator.mode_s.ingester import ModeSIngester


class DecodingError(ValueError):
    """
    Exception raised for any failure to decode a Mode S message.
    """


Ingester = ModeSIngester
