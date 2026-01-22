"""
基础动作类，提供通用的游戏操作方法
"""
import time
from typing import Optional
from ..core.controller import ScreenController
from ..utils.logger import logger


class BaseAction:
    """基础动作类，封装常用的游戏操作"""
    
    def __init__(self, controller: ScreenController):
        self.controller = controller
        self.default_timeout = 10
        self.long_press_timeout = 30
        self.default_loop_interval = 0.05
        self.popup_template = "确认重连"

    def resolve_popup_if_present(self) -> bool:
        """如果存在弹窗则处理它"""
        center = self.controller.fetch_template_coords(self.popup_template)
        if center:
            logger.info(
                f"检测到干扰弹窗: {self.popup_template} @ {center}，正在处理..."
            )
            self.controller.click(center)
            return True
        return False

    def click_template(
        self, 
        target: str, 
        timeout: Optional[float] = None, 
        check_ad: bool = False
    ) -> bool:
        """点击指定模板"""
        timeout = timeout if timeout is not None else self.default_timeout
        start_time = time.time()
        logger.info(f"寻找目标: [{target}]")

        while time.time() - start_time < timeout:
            ad_center = self.controller.fetch_template_coords("广告") if check_ad else None
            if ad_center is not None:
                self.controller.click(ad_center)
                logger.info(f"点击成功: [广告] @ {ad_center}")
                continue
                
            center = self.controller.fetch_template_coords(target)
            if center:
                self.controller.click(center)
                logger.info(f"点击成功: [{target}] @ {center}")
                return True
            else:
                # 检查是否出现弹窗
                self.resolve_popup_if_present()
            time.sleep(self.default_loop_interval)

        logger.warning(f"超时未找到目标: [{target}]")
        return False

    def long_press(self, target_coord, timeout: Optional[float] = None):
        """长按指定坐标"""
        timeout = timeout if timeout is not None else self.long_press_timeout
        logger.info(f"开始长按坐标: {target_coord}")
        start_time = time.time()

        self.controller.click_down(target_coord)

        try:
            while time.time() - start_time < timeout:
                if self.controller.has_template("重连入局"):
                    logger.info(f"检测到目标 [重连入局]，提前结束长按")
                    break

                # 检测弹窗
                if self.controller.has_template(self.popup_template):
                    logger.warning("长按被打断，处理弹窗...")
                    self.controller.click_up(target_coord)  # 抬起
                    self.resolve_popup_if_present()  # 处理弹窗
                    self.controller.click_down(target_coord)  # 恢复按下

                time.sleep(self.default_loop_interval)
        finally:
            self.controller.click_up(target_coord)
            logger.info("长按结束")