"""
点击模板动作类
"""
import time
from typing import Optional, Tuple
from refactored.actions.base_action import BaseAction, PopupHandler
from refactored.utils.logger import logger


class ClickTemplateAction(BaseAction):
    """点击模板动作类"""
    
    def __init__(self, controller, config_manager):
        super().__init__(controller, config_manager)
        self.popup_handler = PopupHandler(controller, config_manager)

    def execute(
        self, 
        target: str, 
        frame=None, 
        timeout: Optional[float] = None, 
        check_ad=False,
        device=None
    ) -> bool:
        """
        执行点击模板动作
        
        Args:
            target: 目标模板名称
            frame: 当前帧，如果为None则从设备获取
            timeout: 超时时间
            check_ad: 是否检查广告
            device: 设备对象
            
        Returns:
            bool: 是否成功点击
        """
        timeout = timeout if timeout is not None else self.config.default_timeout
        start_time = time.time()
        logger.info(f"寻找目标: [{target}]")

        while time.time() - start_time < timeout:
            # 获取当前帧
            current_frame = frame
            if current_frame is None and device:
                current_frame = device.get_frame()
            
            if current_frame is None:
                logger.error("无法获取帧数据")
                return False

            # 检查广告
            if check_ad:
                ad_center = self.controller.fetch_template_coords(current_frame, "广告")
                if ad_center is not None:
                    control = device.get_control() if device else None
                    if control:
                        self.controller.click(control, ad_center)
                        logger.info(f"点击成功: [广告] @ {ad_center}")
                        continue

            # 查找目标
            center = self.controller.fetch_template_coords(current_frame, target)
            if center:
                control = device.get_control() if device else None
                if control:
                    self.controller.click(control, center)
                    logger.info(f"点击成功: [{target}] @ {center}")
                    return True
            else:
                # 检查是否出现弹窗
                self.popup_handler.resolve_popup_if_present(current_frame, self.config.popup_template)
            
            time.sleep(self.config.default_loop_interval)

        logger.warning(f"超时未找到目标: [{target}]")
        return False