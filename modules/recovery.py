import time
from utils.config import LOOP_INTERVAL
from utils.logger import logger
from core.agent import Agent


class GameRecoveryHandler:
    """游戏恢复处理器 - 处理重启和恢复逻辑"""

    def __init__(self, operator: "Agent"):
        self.operator = operator
        self.vision = operator.vision

    def recover_from_failure(self):
        """执行完整的恢复流程"""
        logger.info("开始游戏恢复...")
        self._restart_game()
        self._handle_ad()
        logger.info("游戏恢复完成")

    # TODO 这个函数过于冗长，后续可以拆分成更小的函数

    def _restart_game(self):
        """重启游戏应用"""
        logger.info("重启游戏应用...")
        self.operator.wifi_on()
        self.operator.restart_app()
        time.sleep(1)

        # 处理重连和放弃对局
        while True:
            frame = self.operator.get_frame()
            if frame is None:
                time.sleep(LOOP_INTERVAL)
                continue

            if center := self.operator.locate("取消重连", frame=frame):
                logger.debug("点击取消重连")
                self.operator.click(center)
                time.sleep(1)
                continue
            if center := self.operator.locate("放弃对局", frame=frame):
                logger.debug("点击放弃对局")
                self.operator.click(center)
                time.sleep(1)
                continue
            if center := self.operator.locate("空白跳过", frame=frame):
                logger.debug("点击空白跳过")
                self.operator.click(center)
                time.sleep(1)
                continue
            if center := self.operator.locate("开始游戏", frame=frame):
                logger.debug("点击开始游戏")
                self.operator.click(center)
                time.sleep(1)
                break

            time.sleep(LOOP_INTERVAL)

    def _handle_ad(self):
        """处理重连逻辑"""
        while True:
            frame = self.operator.get_frame()
            if frame is None:
                time.sleep(LOOP_INTERVAL)
                continue

            if center := self.operator.locate("广告", frame=frame):
                self.operator.click(center)
                time.sleep(1)

            if center := self.operator.locate("确认重连", frame=frame):
                self.operator.click(center)
                time.sleep(1)

            if center := self.operator.locate("确认", frame=frame):
                self.operator.click(center)
                time.sleep(1)

            if center := self.operator.locate("空白跳过", frame=frame):
                self.operator.click(center)
                time.sleep(1)
            if self.operator.locate("交易行", frame=frame):
                break
            time.sleep(LOOP_INTERVAL)
