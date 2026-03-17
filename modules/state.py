from enum import Enum, auto


class GameState(Enum):
    UNKNOWN = auto()  # 识别不到特征图（加载中、黑屏）
    LOBBY = auto()  # 正常大厅（行前备战）
    MAP_SELECT = auto()  # 地图选择（零号大坝/开始行动）
    PREPARE = auto()  # 配装界面（确认配装/出发）
    RECONNECT = auto()  # 重启后（重连入局）
    LOBBY_GO = auto()  # 大厅界面（出发）
    GLITCH = auto()  # 故障界面（方案）
