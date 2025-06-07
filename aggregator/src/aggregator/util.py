"""
Generally useful stuff that doesn't fit anywhere else
"""

import asyncio
from collections.abc import Callable, Iterable
import concurrent.futures
import time


def maybe[T](dangerous: Callable[[], T]) -> T | None:
    """
    Executes a callable (function, lambda, etc.) and returns the result. If the callable raises an exception, the
    exception is caught and discarded, and None is returned.
    """
    try:
        return dangerous()
    except Exception:  # pylint: disable=broad-exception-caught
        return None


async def _sleep_forever() -> None:
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass


async def as_asyncio[T](future: concurrent.futures.Future[T]) -> T:
    """
    Wraps a concurrent.futures.Future so that it can be used more naturally in an asyncio setting.
    """
    sleep_task = asyncio.create_task(_sleep_forever())
    result: T | None = None

    def callback(_future: concurrent.futures.Future[T]) -> None:
        nonlocal result
        sleep_task.cancel()
        result = _future.result()

    future.add_done_callback(callback)
    try:
        await sleep_task
    except asyncio.CancelledError:
        pass

    return result  # type: ignore


class LeakyDictionary[K, V]:
    """
    A dictionary whose items expire after a configurable length of time.
    """

    def __init__(self, expiry_secs: int):
        """
        Create a new leaky dictionary whose items expire `expiry_secs` seconds after being set.
        """
        super().__init__()
        self._expiry_secs = expiry_secs
        self._underlying = dict[K, tuple[float, V]]()

    def __getitem__(self, key: K) -> V:
        """
        Return the value for a key. If the item exists but has expired, raises KeyError as though the item didn't exist.
        """
        timestamp, value = self._underlying[key]
        if time.time() - timestamp > self._expiry_secs:
            del self._underlying[key]
            # Dictionary performance degrades over time when there are a lot of additions and deletions. Recreating it
            # gets it back into a good state.
            self._underlying = dict(self._underlying)
            raise KeyError(key)
        return value

    def __setitem__(self, key: K, value: V) -> None:
        """
        Set a value for a key. The item will expire in `self.expiry_secs` seconds. If the item already existed, its
        expiration time is refreshed as though this were a new insertion.
        """
        self._underlying[key] = (time.time(), value)

    def __contains__(self, key: object) -> bool:
        """
        Return True if the key exists in the dictionary and the item hasn't expired.
        """
        try:
            self[key]  # type: ignore
        except KeyError:
            return False
        return True

    def values(self) -> Iterable[V]:
        now = time.time()
        keys = list(self._underlying.keys())
        result: list[V] = []
        for key in keys:
            try:
                timestamp, value = self._underlying[key]
            except KeyError:
                continue
            if now - timestamp > self._expiry_secs:
                del self._underlying[key]
            else:
                result.append(value)
        self._underlying = dict(self._underlying)
        return result

    def get(self, key: K) -> V | None:
        try:
            return self[key]
        except KeyError:
            return None


class ExpiringValue[T]:
    def __init__(self, expiry_secs: int):
        self._expiry_secs = expiry_secs
        self._value: T | None = None
        self._expires_after = 0

    def get(self) -> T | None:
        if self._value is None or time.time() > self._expires_after:
            return None
        return self._value

    def set(self, value: T | None) -> None:
        self._value = value
        self._expires_after = time.time() + self._expiry_secs
