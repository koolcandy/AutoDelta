from utils.logger import logger
from core.agent import Agent

class ReconnectHandler:
    def __init__(self, operator: Agent):
        self.operator = operator
        self.vision = operator.vision

    def handle_reconnect(self, wifi_off=True):
        logger.info("【状态】重连提示 -> 断网并切入方案") 
        if wifi_off:
            self.operator.wifi_off()

        self.operator.wait_and_click_target("重连入局", next_tag="开始游戏", solve_popup=True)
        self.operator.wait_and_click_target("开始游戏", next_tag="行前备战", solve_popup=True)