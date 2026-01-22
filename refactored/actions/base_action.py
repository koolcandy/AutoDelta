"""
基础动作类，定义动作的基本接口
"""
import time
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from refactored.core.base_controller import BaseController


class BaseAction(ABC):
    def __init__(self, controller: BaseController, config_manager):
        self.controller = controller
        self.config = config_manager

    @abstractmethod
    def execute(self, *args, **kwargs):
        """执行动作的抽象方法"""
        pass


class PopupHandler:
    """弹窗处理器，专门处理各种弹窗"""
    
    def __init__(self, controller: BaseController, config_manager):
        self.controller = controller
        self.config = config_manager

    def resolve_popup_if_present(self, frame, popup_template: str = "确认重连") -> bool:
        """如果存在弹窗则处理它"""
        center = self.controller.fetch_template_coords(frame, popup_template)
        if center:
            control = self.controller.device.get_control() if hasattr(self.controller, 'device') else None
            if control:
                self.controller.click(control, center)
                return True
        return False