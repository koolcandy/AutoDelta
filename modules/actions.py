import time
import utils.config as config
from utils.logger import logger
from utils.device import Device


class GameRebootException(Exception):
    """游戏重启异常，用于跳过当前循环"""

    def __init__(self, device: Device, message: str = "游戏已重启，跳过当前循环"):
        super().__init__(message)
        self.device = device
        self._execute_reboot()

    def _execute_reboot(self):
        """执行游戏重启逻辑"""
        logger.info("失败重启...")
        self.device.wifi_on()
        self.device.restart_app()
        time.sleep(5)
        while True:
            if self.device.fetch_coords("取消重连"):
                center = self.device.fetch_coords("取消重连")
                if center:
                    self.device.click(center)
                center = self.device.fetch_coords("放弃对局")
                if center:
                    self.device.click(center)
                center = self.device.fetch_coords("开始游戏")
                if center:
                    self.device.click(center)
                break
            if self.device.fetch_coords("开始游戏"):
                center = self.device.fetch_coords("开始游戏")
                if center:
                    self.device.click(center)
                break
            time.sleep(config.LOOP_INTERVAL)

        time.sleep(1)

        while True:
            if self.device.fetch_coords("广告"):
                center = self.device.fetch_coords("广告")
                if center:
                    self.device.click(center)
                break
            if self.device.fetch_coords("行前备战"):
                break
            time.sleep(config.LOOP_INTERVAL)

        time.sleep(1)

        if self.device.fetch_coords("通行证"):
            center = self.device.fetch_coords("通行证")
            if center:
                self.device.click(center)

        time.sleep(5)


class ActionHandler:
    def __init__(self, device: Device):
        self.device = device

    def click_if_found(self, target: str) -> bool:
        if center := self.device.fetch_coords(target):
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
        self, target: str, timeout: float = 10.0, check_ad: bool = False
    ) -> bool:
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
        raise GameRebootException(self.device)

    def click_template_no_coords(self, target: str, timeout: float = 10.0) -> bool:
        start_time = time.time()
        logger.info(f"寻找目标: [{target}]")

        while time.time() - start_time < float(timeout):
            if coord := self.device.search_template("出售"):
                self.device.click(coord)
                return True

            time.sleep(config.LOOP_INTERVAL)

        logger.warning(f"超时未找到目标: [{target}]")
        raise GameRebootException(self.device)

    def long_press(self, target_coord, timeout: float = 20.0):
        logger.info(f"开始长按坐标: {target_coord}")
        start_time = time.time()
        self.device.click_down(target_coord)
        should_reboot = False

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
            else:
                logger.error(f"长按操作超时，超时时间: {timeout}s")
                should_reboot = True
        finally:
            self.device.click_up(target_coord)
            logger.info("长按结束")
        
        if should_reboot:
            raise GameRebootException(self.device)

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
                logger.info("处理弹窗，准备重试点击...")
                time.sleep(config.LOOP_INTERVAL)
                continue

            if self.click_if_found(current_target):
                time.sleep(config.LOOP_INTERVAL)

            time.sleep(config.LOOP_INTERVAL)

        logger.warning(f"流程超时: 未能从 [{current_target}] 跳转到 [{next_target}]")
        raise GameRebootException(self.device)
