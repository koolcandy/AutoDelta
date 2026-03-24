import time
from core.agent import Agent
from utils.logger import logger


class MapHandler:
    def __init__(self, operator: Agent):
        self.operator = operator

    def handle_map(self):
        logger.info("【状态】选图 -> 进入配装")
        time.sleep(1)
        if self.operator.if_visible("开始行动", do_click=True):
            return
        self.operator.wait_and_click_target(
            "零号大坝", next_tag="开始行动", solve_popup=True
        )
        self.operator.wait_and_click_target(
            "开始行动", next_tag="装备配置", solve_popup=True
        )
