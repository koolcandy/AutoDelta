import time
import subprocess
import threading
import scrcpy
from typing import Tuple, Optional, Dict
from scrcpy.control import ControlSender
from utils.logger import logger
from utils.match import Matcher


class Device:
    """设备控制器，负责与 Android 设备的所有交互操作"""

    def __init__(self, device_id=None, block_frame=True):
        """
        初始化设备控制器

        Args:
            device_id: 设备ID，None 表示自动选择
            block_frame: 是否阻塞等待帧更新
        """
        self.latest_frame = None
        self.latest_frame_ts = 0
        self.frame_event = threading.Event()
        self.client = scrcpy.Client(device=device_id, block_frame=block_frame)
        self.client.add_listener(scrcpy.EVENT_FRAME, self._on_frame)
        self.package_name = "com.tencent.tmgp.dfm"
        self.matcher = Matcher()

    def start(self):
        """启动 scrcpy 客户端"""
        self.client.start(threaded=True)

    def stop(self):
        """停止 scrcpy 客户端"""
        self.client.stop()

    def _on_frame(self, frame):
        """帧更新回调函数"""
        if frame is not None:
            self.latest_frame = frame
            self.latest_frame_ts = time.time()
            self.frame_event.set()

    def get_frame(self, timeout=1.0):
        """
        获取最新屏幕帧

        Args:
            timeout: 超时时间（秒）

        Returns:
            numpy 图像数组，或 None
        """
        # 如果当前帧已经很新（比如 20ms 内），直接返回，不强制等待下一帧
        if (
            self.latest_frame is not None
            and (time.time() - self.latest_frame_ts) < 0.02
        ):
            return self.latest_frame

        if self.frame_event.wait(timeout):
            self.frame_event.clear()
            delay = time.time() - self.latest_frame_ts
            logger.debug(f"获取帧成功。接收延迟: {delay*1000:.2f}ms")
            return self.latest_frame
        return None

    def get_control(self):
        """获取控制接口"""
        return self.client.control

    def _execute_adb_command(self, cmd_list: list) -> bool:
        """
        执行 ADB 命令

        Args:
            cmd_list: 命令参数列表

        Returns:
            命令是否执行成功
        """
        try:
            full_cmd = ["adb", "shell"] + cmd_list
            res = subprocess.run(
                full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15
            )
            return res.returncode == 0
        except Exception as e:
            logger.error(f"ADB 错误: {e}")
            return False

    def restart_app(self):
        """重启应用"""
        self._execute_adb_command(["am", "force-stop", self.package_name])
        time.sleep(1)
        self._execute_adb_command(
            [
                "am",
                "start",
                "-n",
                f"{self.package_name}/com.epicgames.ue4.SplashActivity",
            ]
        )

    def toggle_wifi(self, enable: bool):
        """
        开关 WiFi

        Args:
            enable: True 为开启，False 为关闭
        """
        if enable:
            return self._execute_adb_command(["svc", "wifi", "enable"])
        else:
            return self._execute_adb_command(["svc", "wifi", "disable"])

    def wifi_on(self):
        """开启 WiFi"""
        return self.toggle_wifi(True)

    def wifi_off(self):
        """关闭 WiFi"""
        return self.toggle_wifi(False)

    def _touch_at(
        self,
        control: ControlSender,
        coord: Tuple[int, int],
        action: Optional[int] = None,
    ) -> bool:
        """
        在指定坐标执行触摸操作

        Args:
            control: 控制发送器
            coord: 坐标 (x, y)
            action: 触摸动作类型，None 表示点击（按下+抬起）

        Returns:
            操作是否成功
        """
        try:
            x, y = coord
            if action is None:
                control.touch(x, y, action=0)
                time.sleep(0.1)
                control.touch(x, y, action=1)
            else:
                control.touch(x, y, action=action)
            return True
        except Exception:
            return False

    def click(self, coord: Tuple[int, int]) -> bool:
        """点击指定坐标"""
        return self._touch_at(self.get_control(), coord)

    def click_down(self, coord: Tuple[int, int]) -> bool:
        """按下指定坐标（长按开始）"""
        return self._touch_at(self.get_control(), coord, action=0)

    def click_up(self, coord: Tuple[int, int]) -> bool:
        """抬起指定坐标（长按结束）"""
        return self._touch_at(self.get_control(), coord, action=1)

    def swipe(
        self,
        start_coord: Tuple[int, int],
        end_coord: Tuple[int, int],
        move_step_length: int = 5,
        move_steps_delay: float = 0.005,
    ) -> bool:
        """
        在屏幕上进行滑动操作

        Args:
            start_coord: 起始坐标 (x, y)
            end_coord: 结束坐标 (x, y)
            move_step_length: 每步移动长度（像素）
            move_steps_delay: 每步之间的延迟（秒）

        Returns:
            操作是否成功
        """
        try:
            start_x, start_y = start_coord
            end_x, end_y = end_coord
            self.get_control().swipe(
                start_x, start_y, end_x, end_y, move_step_length, move_steps_delay
            )
            return True
        except Exception:
            return False

    def has_template(self, template_name: str) -> bool:
        """检查是否存在指定模板"""
        return self.fetch_coords(template_name) is not None

    def fetch_center(self, template_name: str) -> Tuple[int, int]:
        """
        从 coords.json 获取模板的静态中心坐标

        Args:
            template_name: 模板名称

        Returns:
            坐标元组 (x, y)
        """
        if template_name in self.matcher.coords:
            x1, y1, x2, y2 = self.matcher.coords[template_name]
            return (x1 + x2) // 2, (y1 + y2) // 2
        return (0, 0)

    def fetch_coords(
        self,
        template_name: str,
    ) -> Optional[Tuple[int, int]]:
        """
        获取模板在屏幕上的实际坐标

        Args:
            template_name: 模板名称

        Returns:
            坐标元组 (x, y)，未找到返回 None
        """
        frame = self.get_frame()
        if frame is None:
            return None

        try:
            match = self.matcher.find_template(frame, template_name)
            if match is None:
                return None

            coords = match.get("center")
            if not coords:
                return None
            return (int(coords[0]), int(coords[1]))
        except Exception:
            return None

    def search_template(self, template_name: str) -> Optional[Tuple[int, int]]:
        """
        在整个屏幕上搜索模板坐标

        Args:
            template_name: 模板名称

        Returns:
            坐标元组 (x, y)，未找到返回 None
        """
        frame = self.get_frame()
        if frame is None:
            return None

        try:
            match = self.matcher.find_template_anywhere(frame, template_name)
            if match is None:
                return None

            coords = match.get("center")
            if not coords:
                return None
            return (int(coords[0]), int(coords[1]))
        except Exception:
            return None
