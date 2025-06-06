class ICAOAddress:
    """
    A 24-bit address identifying an aircraft equipped with a Mode S transponder. These globally unique identifiers are
    assigned to aircraft as part of their registation certificate, and normally never change. On a time scale of single
    flight, this makes them suitable keys for relating information from disparate sources. Their canonical
    representation, at least as far as this software is concerned, is six uppercase hexadecimal digits.
    """

    MAX = 2**24 - 1
    MIN = 0

    def __init__(self, value: str | int) -> None:
        if isinstance(value, str):
            value = int(value, 16)
        if ICAOAddress.MIN <= value <= ICAOAddress.MAX:
            self._value = value
        else:
            raise ValueError("initializing value out of range")

    def __eq__(self, other: object) -> bool:
        """
        ICAOAddress has equality with other ICAOAddress objects, integers, and strings of hexadecimal digits.
        """
        if isinstance(other, ICAOAddress):
            return self._value == other._value
        if isinstance(other, int):
            return self._value == other
        if isinstance(other, str):
            try:
                return self._value == int(other, 16)
            except ValueError:
                return False
        return False

    def __hash__(self) -> int:
        return self._value

    def __repr__(self) -> str:
        return f"ICAOAddress(0x{self._value:x})"

    def __str__(self) -> str:
        return f"{self._value:06X}"
