import time
from typing import Optional, Tuple

import numpy as np

from .scrcpy_client import ControlSender, ScrcpyClient


class AndroidDeviceDriver:
    """Android 设备驱动（纯技术层）。"""

    def __init__(self):
        self.client = ScrcpyClient()

    def start(self) -> None:
        """启动 scrcpy 客户端。"""
        self.client.start()

    def stop(self) -> None:
        """停止 scrcpy 客户端。"""
        self.client.stop()

    def get_frame(self) -> Optional[np.ndarray]:
        return self.client.latest_frame

    def get_control(self) -> ControlSender:
        """获取 scrcpy 控制发送器。"""
        return self.client.control

    def touch(self, coord: Tuple[int, int], action: Optional[int] = None) -> bool:
        """
        发送原始触摸指令。

        action=None 时执行一次点击（down + up）。
        """
        try:
            x, y = coord
            control = self.get_control()
            if action is None:
                control.touch(x, y, action=0)
                time.sleep(0.1)
                control.touch(x, y, action=1)
            else:
                control.touch(x, y, action=action)
            return True
        except Exception:
            return False

    def click(self, coord: Tuple[int, int]) -> bool:
        """点击指定坐标。"""
        return self.touch(coord)

    def touch_down(self, coord: Tuple[int, int]) -> bool:
        """按下指定坐标。"""
        return self.touch(coord, action=0)

    def touch_up(self, coord: Tuple[int, int]) -> bool:
        """抬起指定坐标。"""
        return self.touch(coord, action=1)

    def swipe(
        self,
        start_coord: Tuple[int, int],
        end_coord: Tuple[int, int],
        move_step_length: int = 5,
        move_steps_delay: float = 0.005,
    ) -> bool:
        """发送原始滑动指令。"""
        try:
            start_x, start_y = start_coord
            end_x, end_y = end_coord
            self.get_control().swipe(
                start_x,
                start_y,
                end_x,
                end_y,
                move_step_length,
                move_steps_delay,
            )
            return True
        except Exception:
            return False
