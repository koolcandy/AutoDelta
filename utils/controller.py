import time
import threading
from typing import Tuple, Optional
from scrcpy import const
from scrcpy.control import ControlSender
from utils.matcher import TemplateMatcher
from utils.device import Device


class Controller:
    def __init__(self, device: Device):
        self.device = device
        self.ocr_engine = TemplateMatcher()
        self._scrcpy_lock = threading.Lock()
        self.pkg_name = "com.tencent.tmgp.dfm"

    def _touch_at(
        self, control, coord: Tuple[int, int], action: Optional[int] = None
    ) -> bool:
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
        return self._touch_at(self.device.get_control(), coord)

    def click_down(self, coord: Tuple[int, int]) -> bool:
        return self._touch_at(self.device.get_control(), coord, action=0)

    def click_up(self, coord: Tuple[int, int]) -> bool:
        return self._touch_at(self.device.get_control(), coord, action=1)

    def has_template(self, template_name: str) -> bool:
        return self.fetch_template_coords(template_name) is not None

    def fetch_template_coords(
        self,
        template_name: str,
    ) -> Optional[Tuple[int, int]]:
        frame = self.device.get_frame()
        if frame is None:
            return None

        try:
            match = self.ocr_engine.find_template(frame, template_name)
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
        with self._scrcpy_lock:
            control.touch(coord[0], coord[1], action, touch_id=touch_id)

    def _spam_tap(
        self,
        control: ControlSender,
        coord: Tuple[int, int],
        touch_id: int,
        duration: float,
    ) -> int:
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
