"""
多点触控动作类
"""
from typing import Tuple
from refactored.actions.base_action import BaseAction
from refactored.utils.logger import logger


class MultitouchAction(BaseAction):
    """多点触控动作类"""
    
    def __init__(self, controller, config_manager):
        super().__init__(controller, config_manager)

    def execute(
        self, 
        main_coord: Tuple[int, int], 
        sub_coord: Tuple[int, int], 
        device=None,
        duration: float = 1.0,
        sub_delay: float = 0.5
    ) -> bool:
        """
        执行多点触控动作
        
        Args:
            main_coord: 主要触控坐标
            sub_coord: 辅助触控坐标
            device: 设备对象
            duration: 持续时间
            sub_delay: 辅助触控延迟
            
        Returns:
            bool: 是否成功执行
        """
        logger.info(f"执行多点触控: 主坐标={main_coord}, 辅坐标={sub_coord}")
        
        control = device.get_control() if device else None
        if not control:
            logger.error("无法获取控制接口")
            return False
            
        return self.controller.multitouch(control, main_coord, sub_coord, duration, sub_delay)