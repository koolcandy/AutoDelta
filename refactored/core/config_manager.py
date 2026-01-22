"""
配置管理器类，统一管理所有配置参数
"""
from typing import Tuple, Dict, Any


class ConfigManager:
    def __init__(self):
        # 加载坐标配置
        self.coords = self._load_coords_config()
        
        # 全局超时设置
        self.default_timeout = 10
        self.long_press_timeout = 30
        self.default_loop_interval = 0.05
        
        # 弹窗模板名称
        self.popup_template = "确认重连"
        
        # 常用坐标
        self.cancel_coord = self.coords.get('cancel', (1067, 824))
        self.syfa_coord = self.coords.get('syfa', (2270, 1100))
        self.qrfa_coord = self.coords.get('qrfa', (1350, 1000))

    def _load_coords_config(self) -> Dict[str, Tuple[int, int]]:
        """加载坐标配置"""
        # 这里可以从外部文件加载配置
        # 为演示目的，我们先返回一个默认字典
        try:
            # 尝试从原配置文件导入
            from config import cancel, syfa, qrfa
            return {
                'cancel': cancel,
                'syfa': syfa,
                'qrfa': qrfa
            }
        except ImportError:
            # 如果原配置文件不存在，则返回默认值
            return {
                'cancel': (1067, 824),
                'syfa': (2270, 1100),
                'qrfa': (1350, 1000)
            }

    def get_coord(self, name: str) -> Tuple[int, int]:
        """获取指定名称的坐标"""
        return self.coords.get(name, (0, 0))

    def update_coord(self, name: str, coord: Tuple[int, int]):
        """更新坐标配置"""
        self.coords[name] = coord