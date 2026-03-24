from core.agent import Agent
from utils.logger import logger
import time


class PrepareHandler:
    def __init__(self, operator: Agent):
        self.operator = operator

    def handle_prepare(self, glitch_state):
        logger.info("【状态】选图 -> 进入配装")
        if glitch_state:
            self.operator.wait_and_click_target(
                "方案", next_tag="推荐配装", solve_popup=True
            )
        else:
            self.operator.wait_and_click_target("确认配装", next_tag="再次确认配装")
            time.sleep(0.2)
            self.operator.wait_and_click_target("再次确认配装", next_tag="出发")
