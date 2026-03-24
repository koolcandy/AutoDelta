import time
from utils.logger import logger
import utils.config as config
from core.agent import Agent


class GlitchHandler:
    def __init__(self, operator: Agent):
        self.operator = operator
        self.vision = operator.vision

    def handle_glitch(self, target):
        for _ in range(5):
            self.operator.popup_handler()
            coords = self.vision.get_template_coords(target)
            if coords is not None:
                self.operator.click(coords)
            time.sleep(0.2)

        time.sleep(10)
        self.operator.wifi_on()

        self.operator.long_press_until(config.syfa, "重连入局")
        time.sleep(4)
        self.operator.wait_and_click_target("取消重连")
        self.operator.wait_and_click_target("放弃对局")
