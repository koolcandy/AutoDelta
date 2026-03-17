import time
import numpy as np
from typing import Optional, Literal
from drivers.adb_client import AdbClient
from drivers.android_device import AndroidDeviceDriver
from vision.engine import VisionEngine
from modules.expection import GameRebootException
from utils.logger import logger
from utils import config


class Agent:

    def __init__(self):
        self.android = AndroidDeviceDriver()
        self.adb = AdbClient()
        self.vision = VisionEngine()
        self.vision.register_ocr_target("count", config.count_roi, "0123456789/")
        self.vision.register_ocr_target("coin", config.coin_roi, "0123456789")
        self.vision.register_ocr_target("shelves", config.shelves_roi, "0123456789/")
        self.vision.register_ocr_target("price", config.per_price_roi, "0123456789")
        self.popup_targets = ["广告", "确认重连", "确认", "空白跳过", "领取跳过"]

    def start(self) -> None:
        self.android.start()

    def stop(self) -> None:
        self.android.stop()

    def get_frame(self) -> Optional[np.ndarray]:
        return self.android.get_frame()

    def click(self, coord: tuple[int, int]) -> bool:
        return self.android.click(coord)

    def touch_down(self, coord: tuple[int, int]) -> bool:
        return self.android.touch_down(coord)

    def touch_up(self, coord: tuple[int, int]) -> bool:
        return self.android.touch_up(coord)

    def swipe(self, start_coord: tuple[int, int], end_coord: tuple[int, int]) -> bool:
        return self.android.swipe(start_coord, end_coord)

    def restart_app(self) -> None:
        self.adb.restart_app()

    def wifi_on(self) -> None:
        self.adb.wifi_on()

    def wifi_off(self) -> None:
        self.adb.wifi_off()

    def read_text(
        self, target_type: str, frame: Optional[np.ndarray] = None
    ) -> Optional[str]:
        if frame is None:
            frame = self.get_frame()
            if frame is None:
                return None

        return self.vision.read_text(frame, target_type)

    def locate(
        self,
        target_name: str,
        frame: Optional[np.ndarray] = None,
        ocr: bool = False,
        template_type: Optional[Literal["warehouse", "marketplace"]] = None
    ) -> Optional[tuple[int, int]]:
        if frame is None:
            frame = self.get_frame()
            if frame is None:
                return None

        return self.vision.locate(frame, target_name, ocr, template_type)

    def if_visible(
        self,
        target: str,
        frame: Optional[np.ndarray] = None,
        do_click: bool = False,
    ) -> bool:
        if frame is None:
            frame = self.get_frame()
            if frame is None:
                return False

        if center := self.locate(target, frame=frame):
            if do_click:
                self.click(center)
            return True

        return False

    def wait_for(self, target: str, timeout: float = 10.0):
        start_time = time.time()
        deadline = start_time + float(timeout)
        logger.info(f"等待目标: [{target}]，超时时间: {timeout}s")

        while time.time() < deadline:
            if self.if_visible(target):
                logger.info(f"成功找到目标: [{target}]")
                return
            time.sleep(config.LOOP_INTERVAL)

        logger.warning(f"超时未找到目标: [{target}]")
        raise GameRebootException(f"超时未找到目标: {target}")
    
    def wait_and_click_target(
        self,
        target: str,
        timeout: float = 10.0,
        solve_popup: bool = False,
        next_tag: str = "",
    ) -> bool:
        start_time = time.time()
        deadline = start_time + float(timeout)
        clicked = False
        last_click_time = 0.0
        retry_click_count = 0
        logger.info(f"寻找目标: [{target}]")

        while time.time() < deadline:
            if solve_popup:
                self.popup_handler()

            if not clicked:
                if self.if_visible(target, do_click=True):
                    clicked = True
                    last_click_time = time.time()
                    if not next_tag:
                        return True
                    logger.info(f"已点击目标: [{target}]，开始验证后续状态: [{next_tag}]")
                    time.sleep(config.STEP_INTERVAL)
                    continue

            if clicked and next_tag and self.if_visible(next_tag):
                logger.info(f"成功找到目标: [{target}]，并验证了后续状态: [{next_tag}]")
                return True

            if (
                clicked
                and next_tag
                and time.time() - last_click_time >= config.STEP_INTERVAL*2
                and self.if_visible(target, do_click=True)
            ):
                retry_click_count += 1
                last_click_time = time.time()
                logger.info(
                    f"后续状态未出现，重试点击目标: [{target}]，第{retry_click_count}次补点"
                )
                time.sleep(config.STEP_INTERVAL)
                continue

            time.sleep(config.LOOP_INTERVAL)

        if clicked and next_tag:
            logger.warning(
                f"目标已点击但后续状态未出现: [{next_tag}]，目标: [{target}]，补点次数: {retry_click_count}"
            )
            raise GameRebootException(f"后续状态验证超时: {next_tag}")

        logger.warning(f"超时未找到目标: [{target}]")
        raise GameRebootException(f"超时未找到目标: {target}")

    def long_press_until(
        self,
        coords: tuple[int, int],
        until_target: str,
        timeout: float = 20.0,
    ) -> bool:
        logger.info(f"开始长按坐标: {coords}")
        start_time = time.time()

        self.touch_down(coords)

        try:
            while time.time() - start_time < timeout:

                if self.if_visible(until_target):
                    return True

                # TODO 这个逻辑有点硬编码，后续可以改成更通用的弹窗处理机制
                if coord := self.locate(self.popup_targets[1]):
                    self.touch_up(coords)
                    self.click(coord)
                    self.touch_down(coords)

                time.sleep(config.LOOP_INTERVAL)
        finally:
            self.touch_up(coords)

        logger.error(f"长按操作超时，超时时间: {timeout}s")
        raise GameRebootException(f"长按操作超时: {timeout}s")

    def popup_handler(
        self,
        frame: Optional[np.ndarray] = None,
    ) -> bool:
        """检测并处理弹窗，返回是否处理了弹窗。"""
        if frame is None:
            frame = self.get_frame()
        if frame is None:
            return False

        for target in self.popup_targets:
            if self.if_visible(target, frame=frame, do_click=True):
                logger.info(f"检测到弹窗: [{target}]，已自动处理")
                time.sleep(config.STEP_INTERVAL)
                return True

        return False
