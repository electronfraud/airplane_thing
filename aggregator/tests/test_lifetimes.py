import time

from aggregator.model.lifetimes import lifetimes, expires, Expired


def test_lifetimes():
    @lifetimes
    class VehicleState:
        position: tuple[float, float] | Expired = expires(seconds=1)
        speed: int | Expired = expires(seconds=3)

    vs = VehicleState()
    vs.position = (0, 0)
    vs.speed = 100

    assert vs.position == (0, 0)
    assert vs.speed == 100
    time.sleep(1.1)
    assert vs.position is Expired
    assert vs.speed == 100
    time.sleep(2.1)
    assert vs.position is Expired
    assert vs.speed is Expired
