import functools
import socket
import struct
from time import sleep

from . import const


def inject(control_type: int):
    """
    Inject control code, with this inject, we will be able to do unit test

    Args:
        control_type: event to send, TYPE_*
    """

    def wrapper(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            package = struct.pack(">B", control_type) + f(*args, **kwargs)
            if args[0].parent.control_socket is not None:
                with args[0].parent.control_socket_lock:
                    args[0].parent.control_socket.send(package)
            return package

        return inner

    return wrapper


class ControlSender:
    def __init__(self, parent):
        self.parent = parent

    @inject(const.TYPE_INJECT_TOUCH_EVENT)
    def touch(
        self,
        x: int,
        y: int,
        action: int = const.ACTION_DOWN,
        touch_id: int = 0x1234567887654321,
    ) -> bytes:
        """
        Touch screen

        Args:
            x: horizontal position
            y: vertical position
            action: ACTION_DOWN | ACTION_UP | ACTION_MOVE
            touch_id: Default using virtual id -1, you can specify it to emulate multi finger touch
        """
        x, y = max(x, 0), max(y, 0)

        pressure = 0 if action == const.ACTION_UP else 0xFFFF

        return struct.pack(
            ">BqiiHHHii",
            action,
            touch_id,
            int(x),
            int(y),
            int(self.parent.resolution[0]),
            int(self.parent.resolution[1]),
            pressure,
            0,
            0,
        )

    def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        move_step_length: int = 5,
        move_steps_delay: float = 0.005,
    ) -> None:
        """
        Swipe on screen

        Args:
            start_x: start horizontal position
            start_y: start vertical position
            end_x: start horizontal position
            end_y: end vertical position
            move_step_length: length per step
            move_steps_delay: sleep seconds after each step
        :return:
        """

        self.touch(start_x, start_y, const.ACTION_DOWN)
        next_x = start_x
        next_y = start_y

        if end_x > self.parent.resolution[0]:
            end_x = self.parent.resolution[0]

        if end_y > self.parent.resolution[1]:
            end_y = self.parent.resolution[1]

        decrease_x = True if start_x > end_x else False
        decrease_y = True if start_y > end_y else False
        while True:
            if decrease_x:
                next_x -= move_step_length
                if next_x < end_x:
                    next_x = end_x
            else:
                next_x += move_step_length
                if next_x > end_x:
                    next_x = end_x

            if decrease_y:
                next_y -= move_step_length
                if next_y < end_y:
                    next_y = end_y
            else:
                next_y += move_step_length
                if next_y > end_y:
                    next_y = end_y

            self.touch(next_x, next_y, const.ACTION_MOVE)

            if next_x == end_x and next_y == end_y:
                self.touch(next_x, next_y, const.ACTION_UP)
                break
            sleep(move_steps_delay)
