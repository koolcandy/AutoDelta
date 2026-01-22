"""
DeltaBot 游戏自动化类
"""
import time
from .base import BaseAction
from ..core.device import DeviceController
from ..core.controller import ScreenController
from ..utils.logger import logger


class DeltaBot(BaseAction):
    """DeltaBot游戏自动化主类"""
    
    def __init__(self, device: DeviceController, controller: ScreenController):
        super().__init__(controller)
        self.device = device
        
        # 从 coords.json 获取静态坐标
        self.syfa = self.controller.get_template_center("使用方案")
        if self.syfa is None:
            logger.error("无法获取模板 '使用方案' 的中心坐标，请检查模板配置或 coords.json。")
            raise RuntimeError("模板 '使用方案' 的坐标未配置，无法继续执行 DeltaBot 流程")

    def run_phase_one(self):
        """第一阶段：初始设置和进入战斗"""
        logger.info("=== 阶段一：初始设置和进入战斗 ===")
        
        self.click_template("行前备战")
        self.click_template("开始行动")
        self.click_template("确认配装")
        self.click_template("确认配装2")
        self.click_template("出发")
        logger.info("正在进入战局...")
        time.sleep(5)
        
        logger.info("重启应用...")
        self.device.restart_app()

    def run_phase_two(self):
        """第二阶段：重连和任务执行"""
        logger.info("=== 阶段二：重连和任务执行 ===")
        
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
            time.sleep(10)
            logger.info("恢复 WiFi")
            self.device.wifi_on()
        else:
            raise RuntimeError("未检测到重连入口，流程终止")

    def run_phase_three(self):
        """第三阶段：结算与领取奖励"""
        logger.info("=== 阶段三：结算与领取 ===")
        
        # 复杂操作
        self.long_press(self.syfa)
        time.sleep(2)
        logger.info("执行多点触控")
        
        # 需要从配置中获取这些坐标
        from ..config.coords import qrfa, cancel
        self.controller.multitouch(qrfa, cancel)
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

    def run(self):
        """运行完整的游戏循环"""
        self.run_phase_one()
        self.run_phase_two()
        self.run_phase_three()