from dataclasses import dataclass
import time

from aggregator.model.lifetimes import limited_lifetime_field


def test_lifetimes():
    @dataclass
    class VehicleState:
        position: tuple[float, float] | None = limited_lifetime_field(seconds=1)
        speed: int | None = limited_lifetime_field(seconds=3)

    vs = VehicleState()
    vs.position = (0, 0)
    vs.speed = 100

    assert vs.position == (0, 0)
    assert vs.speed == 100
    time.sleep(1.1)
    assert vs.position is None
    assert vs.speed == 100
    time.sleep(2)
    assert vs.position is None
    assert vs.speed is None
