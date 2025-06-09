from abc import ABC, abstractmethod
import asyncio

from aggregator.log import log


class Runnable(ABC):
    """
    Runnable implements an asynchronous "run until told to stop" loop. The loop begins when `run` is awaited and can be
    stopped by calling `stop`. Subclasses implement `step`, which is awaited on each loop cycle. Subclasses can also
    implement `setup` and/or `teardown` if they need to do any pre- or post-loop work.
    """

    def __init__(self, name: str | None = None):
        if name is None:
            self._name = type(self).__name__
        else:
            self._name = name
        self._running = False

    async def run(self) -> None:
        log(f"{self._name} starting")
        self._running = True
        await self.setup()
        log(f"{self._name} started")

        while self._running:
            await self.step()

        await self.teardown()
        log(f"{self._name} stopped")

    def stop(self) -> None:
        log(f"{self._name} stopping")
        self._running = False

    def is_running(self) -> bool:
        return self._running

    @abstractmethod
    async def step(self) -> None: ...

    async def setup(self) -> None:
        pass

    async def teardown(self) -> None:
        pass
