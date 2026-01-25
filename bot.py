"""
游戏自动化机器人模块
整合了基础操作和游戏流程逻辑
"""

import time
import config
from typing import Optional
from logger import logger


class Bot:
    """游戏自动化机器人，封装所有游戏操作逻辑"""

    def __init__(self, device):
        """
        初始化机器人
        
        Args:
            device: Device 设备控制器实例
        """
        self.device = device
        
        # 从 coords.json 获取静态坐标
        self.syfa = self.device.get_template_center("使用方案")

    def _click_if_found(self, target: str) -> bool:
        """
        尝试寻找并点击目标
        
        Args:
            target: 模板名称
            
        Returns:
            是否成功找到并点击
        """
        center = self.device.fetch_template_coords(target)
        if center:
            self.device.click(center)
            logger.info(f"点击成功: [{target}] @ {center}")
            return True
        return False

    def resolve_popup_if_present(self, center=None) -> bool:
        """
        如果存在弹窗则处理它
        
        Args:
           center: 已知的弹窗坐标，如果为None则尝试查找
        """
        if center is None:
            center = self.device.fetch_template_coords("确认重连")
            
        if center:
            logger.info(
                f"检测到干扰弹窗: [确认重连] @ {center}，正在处理..."
            )
            self.device.click(center)
            return True
        return False

    def click_template(
        self, target: str, timeout: Optional[float] = None, check_ad: bool = False
    ) -> bool:
        """
        点击指定模板
        
        Args:
            target: 模板名称
            timeout: 超时时间（秒）
            check_ad: 是否检查并点击广告
            
        Returns:
            是否成功找到并点击目标
        """
        timeout = timeout if timeout is not None else config.DEFAULT_TIMEOUT
        start_time = time.time()
        logger.info(f"寻找目标: [{target}]")

        while time.time() - start_time < timeout:
            if check_ad and self._click_if_found("广告"):
                time.sleep(config.LOOP_INTERVAL)
                continue

            if self._click_if_found(target):
                return True
            
            # 检查是否出现弹窗
            self.resolve_popup_if_present()
            time.sleep(config.LOOP_INTERVAL)

        logger.warning(f"超时未找到目标: [{target}]")
        return False

    def click_template_with_ad(self, target: str, timeout: Optional[float] = None) -> bool:
        """点击指定模板（自动检查广告）"""
        return self.click_template(target, timeout=timeout, check_ad=True)

    def long_press(self, target_coord, timeout: Optional[float] = None):
        """
        长按指定坐标
        
        Args:
            target_coord: 目标坐标 (x, y)
            timeout: 超时时间（秒）
        """
        timeout = timeout if timeout is not None else config.LONG_PRESS_TIMEOUT
        logger.info(f"开始长按坐标: {target_coord}")
        start_time = time.time()

        self.device.click_down(target_coord)

        try:
            while time.time() - start_time < timeout:
                if self.device.has_template("重连入局"):
                    logger.info(f"检测到目标 [重连入局]，提前结束长按")
                    break

                # 检测弹窗
                popup_center = self.device.fetch_template_coords("确认重连")
                if popup_center:
                    logger.warning("长按被打断，处理弹窗...")
                    self.device.click_up(target_coord)  # 抬起
                    self.resolve_popup_if_present(center=popup_center)  # 处理弹窗
                    self.device.click_down(target_coord)  # 恢复按下

                time.sleep(config.LOOP_INTERVAL)
        finally:
            self.device.click_up(target_coord)
            logger.info("长按结束")

    def run(self):
        """执行一次完整的游戏流程"""
        from config import QRFA_COORD, CANCEL_COORD
        
        self.click_template("行前备战")
        self.click_template("开始行动")
        self.click_template("确认配装")
        self.click_template("确认配装2")
        self.click_template("出发")
        logger.info("正在进入战局...")
        time.sleep(5)

        logger.info("重启应用...")
        self.device.restart_app()

        while (self.device.fetch_template_coords("重连入局") is None):
            time.sleep(0.1)
        self.device.wifi_off()
        logger.info("关闭 WiFi")
        self.click_template("重连入局")
        self.click_template("开始游戏")
        self.click_template_with_ad("行前备战")
        self.click_template("零号大坝")
        self.click_template("开始行动")
        self.click_template("确认")
        self.click_template("方案")
        self.click_template("9x39")
        time.sleep(10)
        logger.info("恢复 WiFi")
        self.device.wifi_on()
        
        self.long_press(self.syfa)
        time.sleep(2)
        logger.info("执行多点触控")
        
        self.device.multitouch(QRFA_COORD, CANCEL_COORD)
        time.sleep(2)
        self.click_template("放弃对局")
        self.click_template_with_ad("邮件")
        self.click_template("部分领取")
        time.sleep(1)
        self.click_template("胸挂")
        self.click_template("背包")
        self.click_template("领取")
        time.sleep(2)
        self.click_template("跳过")
        time.sleep(2)
        self.click_template("返回")
