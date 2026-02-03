import time
from typing import Optional
import config
from logger import logger


class ActionHandler:
    def __init__(self, device):
        self.device = device

    def click_if_found(self, target: str) -> bool:
        center = self.device.fetch_coords(target)
        if center:
            popup = self.device.fetch_coords("确认重连")
            if popup:
                return False
            self.device.click(center)
            logger.info(f"点击动作: [{target}]")
            return True
        return False

    def resolve_popup_if_present(self, center=None) -> bool:
        if center is None:
            center = self.device.fetch_coords("确认重连")
        if center:
            logger.info(f"检测到干扰弹窗: [确认重连] @ {center}，正在处理...")
            self.device.click(center)
            return True
        return False

    def click_template(
        self, target: str, timeout: Optional[float] = None, check_ad: bool = False
    ) -> bool:
        timeout = timeout if timeout is not None else config.DEFAULT_TIMEOUT
        start_time = time.time()
        logger.info(f"寻找目标: [{target}]")

        while time.time() - start_time < float(timeout):
            if check_ad and self.click_if_found("广告"):
                time.sleep(config.LOOP_INTERVAL * 2)
                continue

            if self.click_if_found(target):
                return True

            self.resolve_popup_if_present()

            if self.click_if_found(target):
                return True

            time.sleep(config.LOOP_INTERVAL)

        logger.warning(f"超时未找到目标: [{target}]")
        return False

    def long_press(self, target_coord, timeout: Optional[float] = None):
        timeout = timeout if timeout is not None else config.LONG_PRESS_TIMEOUT
        logger.info(f"开始长按坐标: {target_coord}")
        start_time = time.time()
        self.device.click_down(target_coord)

        try:
            while time.time() - start_time < timeout:
                if self.device.has_template("重连入局"):
                    logger.info(f"检测到目标 [重连入局]，提前结束长按")
                    break

                popup_center = self.device.fetch_coords("确认重连")
                if popup_center:
                    logger.warning("长按被打断，处理弹窗...")
                    self.device.click_up(target_coord)
                    self.resolve_popup_if_present(center=popup_center)
                    self.device.click_down(target_coord)

                time.sleep(config.LOOP_INTERVAL)
        finally:
            self.device.click_up(target_coord)
            logger.info("长按结束")

    def click_step(
        self, current_target: str, next_target: str, timeout: float = 10.0
    ) -> bool:
        start_time = time.time()
        logger.info(f"流程执行: [{current_target}] -> 等待 [{next_target}]")

        while time.time() - start_time < timeout:
            if self.device.fetch_coords(next_target):
                logger.info(f"流转成功: 检测到 [{next_target}]")
                return True

            if self.resolve_popup_if_present():
                logger.info("处理了弹窗，准备重试点击...")
                time.sleep(config.LOOP_INTERVAL)
                continue

            if self.click_if_found(current_target):
                time.sleep(config.LOOP_INTERVAL)

            time.sleep(config.LOOP_INTERVAL)

        logger.warning(f"流程超时: 未能从 [{current_target}] 跳转到 [{next_target}]")
        return False
