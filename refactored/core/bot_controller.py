"""
机器人控制器类，整合所有功能并提供高级操作接口
"""
from refactored.core.base_controller import BaseController
from refactored.core.config_manager import ConfigManager
from refactored.actions.click_template_action import ClickTemplateAction
from refactored.actions.long_press_action import LongPressAction
from refactored.actions.multitouch_action import MultitouchAction
from refactored.utils.logger import logger


class BotController:
    """机器人控制器，协调各个组件完成复杂任务"""
    
    def __init__(self, device):
        self.device = device
        self.config = ConfigManager()
        self.controller = BaseController()
        # 设置控制器的设备引用
        self.controller.device = device
        
        # 初始化各种动作
        self.click_template_action = ClickTemplateAction(self.controller, self.config)
        self.long_press_action = LongPressAction(self.controller, self.config)
        self.multitouch_action = MultitouchAction(self.controller, self.config)

    def click_template(self, target: str, timeout=None, check_ad=False) -> bool:
        """点击模板"""
        return self.click_template_action.execute(
            target=target,
            timeout=timeout,
            check_ad=check_ad,
            device=self.device
        )

    def long_press(self, target_coord, timeout=None):
        """长按操作"""
        self.long_press_action.execute(
            target_coord=target_coord,
            timeout=timeout,
            device=self.device
        )

    def multitouch(self, main_coord, sub_coord, duration=1.0, sub_delay=0.5):
        """多点触控操作"""
        return self.multitouch_action.execute(
            main_coord=main_coord,
            sub_coord=sub_coord,
            device=self.device,
            duration=duration,
            sub_delay=sub_delay
        )

    def run_mission(self):
        """执行完整任务流程"""
        logger.info("开始执行任务流程...")
        
        # 阶段一：准备阶段
        logger.info("=== 阶段一：准备阶段 ===")
        self.click_template("行前备战")
        # self.click_template("零号大坝")
        self.click_template("开始行动")
        self.click_template("确认配装")
        self.click_template("确认配装2")
        self.click_template("出发")
        logger.info("正在进入战局...")
        
        # 重启应用
        logger.info("重启应用...")
        self.device.restart_app()

        # 阶段二：游戏中期
        logger.info("=== 阶段二：游戏中期 ===")
        if self.click_template("重连入局", timeout=60):
            logger.info("关闭 WiFi")
            self.device.wifi_off()
            self.click_template("开始游戏")
            self.click_template("行前备战", check_ad=True)
            self.click_template("零号大坝")
            self.click_template("开始行动")
            self.click_template("确认")
            self.click_template("方案")
            self.click_template("9x39")
            logger.info("等待10秒...")
            import time
            time.sleep(10)
            logger.info("恢复 WiFi")
            self.device.wifi_on()
        else:
            raise RuntimeError("未检测到重连入口，流程终止")

        logger.info("=== 阶段三：结算与领取 ===")

        # 复杂操作
        self.long_press(self.config.syfa_coord)
        import time
        time.sleep(2)
        logger.info("执行多点触控")
        self.multitouch(self.config.qrfa_coord, self.config.cancel_coord)
        time.sleep(2)
        self.click_template("放弃对局")
        self.click_template("邮件", check_ad=True)
        self.click_template("部分领取")
        time.sleep(1)
        self.click_template("胸挂")
        self.click_template("背包")
        self.click_template("领取")
        time.sleep(2)
        self.click_template("跳过")
        time.sleep(2)
        self.click_template("返回")
        
        logger.info("任务流程执行完毕")