from pcdsdevices.sim import SlowMotor
import time


def fly_axis(axis=None, velocity=None, pos_min=None, pos_max=None):
    if axis is None:
        axis = SlowMotor()

    if not isinstance(axis, SlowMotor) and velocity is not None:
        velocity_0 = axis.velocity.get()
        axis.velocity.put(velocity)

    position_0 = axis.position

    try:
        while True:
            st = axis.move(pos_min, wait=True)
            print(f"Position: {axis.position}")
            st = axis.move(pos_max, wait=True)
            print(f"Position: {axis.position}")

    except KeyboardInterrupt:
        print('Fly axis aborted')
        axis.stop()
        time.sleep(2)

    finally:
        print('Returning to original position')
        axis.move(position_0, wait=True)


class User:

    def __init__(self):
        self.fly_axis = fly_axis
