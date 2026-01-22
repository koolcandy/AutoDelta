"""
控制器模块，处理屏幕触摸和模板匹配
"""
import time
import threading
from typing import Tuple, Optional
import scrcpy.const as const
from scrcpy.control import ControlSender
from ..utils.matcher import TemplateMatcher
from .device import DeviceController


class ScreenController:
    """屏幕控制器，负责触摸操作和模板匹配"""
    
    def __init__(self, device: DeviceController):
        self.device = device
        self.matcher = TemplateMatcher()
        self._scrcpy_lock = threading.Lock()
        self.package_name = "com.tencent.tmgp.dfm"

    def _touch_at(
        self, control: ControlSender, coord: Tuple[int, int], action: Optional[int] = None
    ) -> bool:
        """在指定坐标执行触摸操作"""
        try:
            x, y = coord
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
        """点击指定坐标"""
        return self._touch_at(self.device.get_control(), coord)

    def click_down(self, coord: Tuple[int, int]) -> bool:
        """按下指定坐标（长按开始）"""
        return self._touch_at(self.device.get_control(), coord, action=0)

    def click_up(self, coord: Tuple[int, int]) -> bool:
        """抬起指定坐标（长按结束）"""
        return self._touch_at(self.device.get_control(), coord, action=1)

    def has_template(self, template_name: str) -> bool:
        """检查是否存在指定模板"""
        return self.fetch_template_coords(template_name) is not None

    def get_template_center(self, template_name: str) -> Optional[Tuple[int, int]]:
        """从 coords.json 获取模板的静态中心坐标"""
        if template_name in self.matcher.coords:
            x1, y1, x2, y2 = self.matcher.coords[template_name]
            return (x1 + x2) // 2, (y1 + y2) // 2
        return None

    def fetch_template_coords(
        self,
        template_name: str,
    ) -> Optional[Tuple[int, int]]:
        """获取模板在屏幕上的实际坐标"""
        frame = self.device.get_frame()
        if frame is None:
            return None

        try:
            match = self.matcher.find_template(frame, template_name)
            if match is None:
                return None

            coords = match.get("center")
            if not coords:
                return None
            return (int(coords[0]), int(coords[1]))
        except Exception:
            return None

    def _safe_touch(
        self, control: ControlSender, coord: Tuple[int, int], action: int, touch_id: int
    ):
        """线程安全的触摸操作"""
        with self._scrcpy_lock:
            control.touch(coord[0], coord[1], action, touch_id=touch_id)

    def _spam_tap(
        self,
        control: ControlSender,
        coord: Tuple[int, int],
        touch_id: int,
        duration: float,
    ) -> int:
        """快速连续点击"""
        start = time.time()
        count = 0
        while time.time() - start < duration:
            self._safe_touch(control, coord, const.ACTION_DOWN, touch_id)
            time.sleep(0.05)
            self._safe_touch(control, coord, const.ACTION_UP, touch_id)
            count += 1
        return count

    def _single_tap(
        self, control: ControlSender, coord: Tuple[int, int], touch_id: int
    ):
        """单次点击"""
        self._safe_touch(control, coord, const.ACTION_DOWN, touch_id)
        time.sleep(0.05)
        self._safe_touch(control, coord, const.ACTION_UP, touch_id)

    def multitouch(
        self,
        main_coord: Tuple[int, int],
        sub_coord: Tuple[int, int],
        duration: float = 1.0,
        sub_delay: float = 0.5,
    ) -> bool:
        """多点触控操作"""
        try:
            ctrl = self.device.get_control()

            id_main = 1
            id_sub = 2

            def thread_main():
                self._spam_tap(ctrl, main_coord, touch_id=id_main, duration=duration)

            def thread_sub():
                time.sleep(sub_delay)
                self._single_tap(ctrl, sub_coord, touch_id=id_sub)

            t1 = threading.Thread(target=thread_main)
            t2 = threading.Thread(target=thread_sub)

            t1.start()
            t2.start()

            t1.join()
            t2.join()

            return True

        except Exception:
            return False