import time
from typing import Optional
from utils.device import Device
from utils.controller import Controller
from utils.logger import logger
from config import *


class DeltaBot:
    def __init__(self, device: Device, automator: Controller):
        self.dev = device
        self.auto = automator
        self.DEFAULT_TIMEOUT = 10
        self.LONG_PRESS_TIMEOUT = 30
        self.DEFAULT_LOOP_INTERVAL = 0.05
        self.POPUP_TEMPLATE = "确认重连"

    def _resolve_popup_if_present(self) -> bool:
        center = self.auto.fetch_template_coords(self.POPUP_TEMPLATE)
        if center:
            logger.info(
                f"检测到干扰弹窗: {self.POPUP_TEMPLATE} @ {center}，正在处理..."
            )
            self.auto.click(center)
            return True
        return False

    def click_template(self, target: str, timeout: Optional[float] = None) -> bool:
        timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        start_time = time.time()
        logger.info(f"寻找目标: [{target}]")

        while time.time() - start_time < timeout:
            center = self.auto.fetch_template_coords(target)
            if center:
                self.auto.click(center)
                if self.auto.fetch_template_coords(target) is None:
                    # 点击失败，重试
                    continue
                logger.info(f"点击成功: [{target}] @ {center}")
                return True
            else:
                # 检查是否出现弹窗
                self._resolve_popup_if_present()
            time.sleep(self.DEFAULT_LOOP_INTERVAL)

        logger.warning(f"超时未找到目标: [{target}]")
        return False

    def long_press(self, target_coord, timeout: Optional[float] = None):
        timeout = timeout if timeout is not None else self.LONG_PRESS_TIMEOUT
        logger.info(f"开始长按坐标: {target_coord}")
        start_time = time.time()

        self.auto.click_down(target_coord)

        try:
            while time.time() - start_time < timeout:
                if self.auto.has_template(self.POPUP_TEMPLATE):
                    logger.info(f"检测到目标 [重连入局]，提前结束长按")
                    break

                # 检测弹窗
                if self.auto.has_template(self.POPUP_TEMPLATE):
                    logger.warning("长按被打断，处理弹窗...")
                    self.auto.click_up(target_coord)  # 抬起
                    self._resolve_popup_if_present()  # 处理弹窗
                    self.auto.click_down(target_coord)  # 恢复按下

                time.sleep(self.DEFAULT_LOOP_INTERVAL)
        finally:
            self.auto.click_up(target_coord)
            logger.info("长按结束")

    def run(self):
        self.click_template("行前备战")
        # self.click_template("零号大坝")
        self.click_template("开始行动")
        self.click_template("确认配装")
        self.click_template("确认配装2")
        self.click_template("出发")
        logger.info("正在进入战局...")
        self.auto.sleep(5)
        logger.info("重启应用...")
        self.dev.restart_app()

        # 等待关键节点
        if self.click_template("重连入局", timeout=60):
            logger.info("关闭 WiFi")
            self.dev.wifi_off()
            self.click_template("开始游戏")
            # self.click_template("广告")
            self.click_template("行前备战")
            self.click_template("零号大坝")
            self.click_template("开始行动")
            self.click_template("确认")
            self.click_template("方案")
            self.click_template("9x39")
            self.auto.sleep(10)
            logger.info("恢复 WiFi")
            self.dev.wifi_on()
        else:
            raise RuntimeError("未检测到重连入口，流程终止")

        logger.info("=== 阶段三：结算与领取 ===")

        # 复杂操作
        self.long_press(syfa)
        self.auto.sleep(2)
        logger.info("执行多点触控")
        self.auto.multitouch(qrfa, cancel)
        self.auto.sleep(2)
        self.click_template("放弃对局")
        self.click_template("邮件")
        self.click_template("部分领取")
        self.auto.sleep(1)
        self.click_template("胸挂")
        self.click_template("背包")
        self.click_template("领取")
        self.auto.sleep(2)
        self.click_template("跳过")
        self.auto.sleep(2)
        self.click_template("返回")


def main():
    logger.info("AutoDelta 机器人启动中...")
    dev = Device(block_frame=True)
    dev.start()

    auto = Controller(dev)
    bot = DeltaBot(dev, auto)

    try:
        for _ in range(3):
            bot.run()
    except KeyboardInterrupt:
        logger.info("用户手动停止")
    except Exception as e:
        logger.error(f"发生异常: {e}")
    finally:
        logger.info("正在清理资源...")
        # 安全保障：确保长按被释放
        try:
            bot.auto.click_up(syfa)
        except:
            pass
        dev.stop()


if __name__ == "__main__":
    main()
