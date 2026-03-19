import time
from core.agent import Agent
from utils.logger import logger


class MailHandler:
    def __init__(self, operator: Agent):
        self.operator = operator

    def handle_mail(self):
        logger.info("【状态】处理邮件与收尾")
        self.operator.wait_and_click_target("邮件")
        self.operator.wait_for("部分领取")
        time.sleep(0.5)
        frame = self.operator.get_frame()
        if frame is None:
            return
        allright = (
            self.operator.locate("胸挂", frame=frame) is not None
            and self.operator.locate("背包", frame=frame) is not None
        )
        if allright:
            self.operator.wait_and_click_target("部分领取")
            time.sleep(0.5)
            self.operator.wait_and_click_target("胸挂")
            self.operator.wait_and_click_target("背包")
        self.operator.wait_and_click_target("领取")
        time.sleep(1)
        self.operator.wait_and_click_target("返回", solve_popup=True)

        return True
    
    def recept_mail(self):
        logger.info("【状态】接取邮件")

        self.operator.wait_and_click_target("邮件")
        self.operator.wait_and_click_target("系统")
        time.sleep(2)
        self.operator.wait_and_click_target("领取")
        time.sleep(2)
        self.operator.popup_handler()
        if self.operator.if_visible("删除"):
            self.operator.wait_and_click_target("删除", solve_popup=True)
        self.operator.wait_and_click_target("返回")