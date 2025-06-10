from dataclasses import dataclass
import time

from aggregator.model.lifetimes import ephemeral_field


def test_lifetimes():
    @dataclass
    class VehicleState:
        position: tuple[float, float] | None = ephemeral_field(seconds=1)
        speed: int | None = ephemeral_field(seconds=3)

    vs = VehicleState()
    vs.position = (0, 1)
    vs.speed = 100

    assert vs.position == (0, 1)
    assert vs.speed == 100
    time.sleep(1.1)
    assert vs.position is None
    assert vs.speed == 100
    time.sleep(2)
    assert vs.position is None
    assert vs.speed is None


def test_multiple_instances():
    @dataclass
    class VehicleState:
        position: tuple[float, float] | None = ephemeral_field(seconds=1)
        speed: int | None = ephemeral_field(seconds=3)

    vs0 = VehicleState()
    vs0.position = (0, 1)
    vs0.speed = 100

    vs1 = VehicleState()

    time.sleep(0.5)
    vs1.position = (2, 3)
    time.sleep(0.6)
    assert vs0.position is None
