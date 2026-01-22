"""
长按动作类
"""
import time
from typing import Optional, Tuple
from refactored.actions.base_action import BaseAction, PopupHandler
from refactored.utils.logger import logger


class LongPressAction(BaseAction):
    """长按动作类"""
    
    def __init__(self, controller, config_manager):
        super().__init__(controller, config_manager)
        self.popup_handler = PopupHandler(controller, config_manager)

    def execute(
        self, 
        target_coord: Tuple[int, int], 
        frame=None, 
        timeout: Optional[float] = None,
        device=None
    ):
        """
        执行长按动作
        
        Args:
            target_coord: 目标坐标
            frame: 当前帧
            timeout: 长按持续时间
            device: 设备对象
        """
        timeout = timeout if timeout is not None else self.config.long_press_timeout
        logger.info(f"开始长按坐标: {target_coord}")
        start_time = time.time()

        control = device.get_control() if device else None
        if not control:
            logger.error("无法获取控制接口")
            return

        self.controller.click_down(control, target_coord)

        try:
            while time.time() - start_time < timeout:
                # 获取当前帧
                current_frame = frame
                if current_frame is None and device:
                    current_frame = device.get_frame()
                
                if current_frame is not None:
                    # 检查是否出现"重连入局"
                    if self.controller.has_template(current_frame, "重连入局"):
                        logger.info(f"检测到目标 [重连入局]，提前结束长按")
                        break

                    # 检测弹窗
                    if self.controller.has_template(current_frame, self.config.popup_template):
                        logger.warning("长按被打断，处理弹窗...")
                        self.controller.click_up(control, target_coord)  # 抬起
                        self.popup_handler.resolve_popup_if_present(current_frame, self.config.popup_template)  # 处理弹窗
                        self.controller.click_down(control, target_coord)  # 恢复按下

                time.sleep(self.config.default_loop_interval)
        finally:
            self.controller.click_up(control, target_coord)
            logger.info("长按结束")