import time
from core.agent import Agent
from utils.logger import logger


class LobbyHandler:
    def __init__(self, operator: Agent):
        self.operator = operator

    def handle_lobby_prepare(self):
        logger.info("【状态】大厅 -> 选图")
        self.operator.wait_and_click_target("行前备战")

    def handle_lobby_go(self):
        logger.info("【状态】大厅 -> 出发")
        self.operator.wait_and_click_target("出发")
        time.sleep(6)
        self.operator.restart_app()
