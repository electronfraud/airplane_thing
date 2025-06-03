class ICAOAddress:
    """
    A 24-bit address identifying an aircraft.
    """

    MAX = 2**24 - 1
    MIN = 0

    def __init__(self, value: str | int) -> None:
        if isinstance(value, str):
            value = int(value, 16)
        if isinstance(value, int):
            if ICAOAddress.MIN <= value <= ICAOAddress.MAX:
                self._value = value
            else:
                raise ValueError(f"initializing value out of range")
        else:
            raise TypeError(f"initializing values must be strings or integers, not {repr(type(value).__name__)}")

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

    def __repr__(self) -> str:
        return f"ICAOAddress(0x{self._value:x})"

    def __str__(self) -> str:
        return "%06X" % self._value
