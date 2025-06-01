from abc import ABC, abstractmethod
import asyncio

from aggregator.log import log


class Runnable(ABC):
    """
    Implements an asynchronous "run forever" loop. The loop begins when `run` is awaited and can be stopped by calling
    `stop`. Subclasses implement `step`, which is awaited on each loop cycle.

    As a convenience, if `step` raises asyncio.queues.QueueShutDown after `stop` has been called, Runnable assumes the
    exception is part of an orderly shutdown and ignores it. `run` will then exit normally.
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
            try:
                await self.step()
            except asyncio.queues.QueueShutDown:
                if self._running:
                    raise
                break

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
