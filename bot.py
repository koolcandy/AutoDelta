"""
游戏自动化机器人模块
整合了基础操作和游戏流程逻辑
"""

import time
from utils.device import Device
from utils.logger import logger
from modules.actions import ActionHandler
from modules.market import MarketHandler


class Bot:
    """游戏自动化机器人，封装所有游戏操作逻辑"""

    def __init__(self, device: Device):
        """
        初始化机器人

        Args:
            device: Device 设备控制器实例
        """
        self.device = device
        self.actions = ActionHandler(device)
        self.market = MarketHandler(device)

        # 从 coords.json 获取静态坐标
        self.syfa = self.device.fetch_center("使用方案")
        self.qrfa = self.device.fetch_center("确认配装方案")
        self.cancel = self.device.fetch_center("取消重连")

    def run(self, target):
        self.actions.click_template("交易行")
        self.actions.click_template("12 buy")
        self.market.buy_items(target_price=288, total_purchase_count=1600)
        self.actions.click_template("返回")
        self.actions.click_template("返回")
        self.actions.click_template("行前备战")
        self.actions.click_template("开始行动")
        self.actions.click_template("确认配装")
        time.sleep(0.5)
        self.actions.click_template("确认配装2")
        self.actions.click_template("出发")
        logger.info("正在进入战局...")
        time.sleep(10)

        logger.info("重启应用...")
        self.device.restart_app()

        while self.device.fetch_coords("重连入局") is None:
            time.sleep(0.1)

        self.device.wifi_off()
        logger.info("关闭 WiFi")

        self.actions.click_template("重连入局", timeout=20)
        self.actions.click_template("开始游戏")
        self.actions.click_template("行前备战", check_ad=True)

        self.actions.click_step("零号大坝", "开始行动")

        self.actions.click_step("开始行动", "确认")

        self.actions.click_step("确认", "方案")

        self.actions.click_template("方案", target)
        time.sleep(1)

        self.actions.click_template(target)
        time.sleep(0.5)
        self.actions.click_template(target)
        time.sleep(0.5)
        self.actions.click_template(target)

        time.sleep(10)
        logger.info("恢复 WiFi")
        self.device.wifi_on()

        self.actions.long_press(self.syfa)
        time.sleep(5)
        self.actions.click_template("取消重连")
        self.actions.click_template("放弃对局")
        self.actions.click_step("通行证", "邮件")
        time.sleep(1)
        self.actions.click_template("邮件", check_ad=True)
        self.actions.click_template("部分领取")
        time.sleep(1)
        self.actions.click_template("胸挂")
        self.actions.click_template("背包")
        self.actions.click_template("领取")
        time.sleep(2)
        self.actions.click_template("跳过")
        time.sleep(1)
        self.actions.click_template("返回")


def main():
    """主函数"""
    logger.info("AutoDelta 启动中...")

    device = Device()
    device.start()

    bot = Bot(device)

    run_rounds = 5

    try:
        for round_num in range(1, run_rounds + 1):
            logger.info(f"开始第 {round_num}/{run_rounds} 轮")
            bot.run("12")
    except KeyboardInterrupt:
        logger.info("用户手动停止")
    finally:
        logger.info("正在清理资源...")
        device.stop()


if __name__ == "__main__":
    main()
