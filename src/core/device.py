"""
设备控制模块，封装与Android设备的交互
"""
import time
import subprocess
import threading
import scrcpy
from ..utils.logger import logger


class DeviceController:
    """设备控制器，负责与Android设备的基本交互"""
    
    def __init__(self, device_id=None, block_frame=True):
        self.latest_frame = None
        self.latest_frame_ts = 0
        self.frame_event = threading.Event()
        self.client = scrcpy.Client(device=device_id, block_frame=block_frame)
        self.client.add_listener(scrcpy.EVENT_FRAME, self._on_frame)
        self.package_name = "com.tencent.tmgp.dfm"

    def start(self):
        """启动scrcpy客户端"""
        self.client.start(threaded=True)

    def stop(self):
        """停止scrcpy客户端"""
        self.client.stop()

    def _on_frame(self, frame):
        """帧更新回调函数"""
        if frame is not None:
            self.latest_frame = frame
            self.latest_frame_ts = time.time()
            self.frame_event.set()

    def get_frame(self, timeout=1.0):
        """获取最新帧"""
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
        """执行ADB命令"""
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
            ["am", "start", "-n", f"{self.package_name}/com.epicgames.ue4.SplashActivity"]
        )

    def toggle_wifi(self, enable: bool):
        """开关WiFi"""
        if enable:
            return self._execute_adb_command(["svc", "wifi", "enable"])
        else:
            return self._execute_adb_command(["svc", "wifi", "disable"])

    def wifi_on(self):
        """开启WiFi"""
        return self.toggle_wifi(True)

    def wifi_off(self):
        """关闭WiFi"""
        return self.toggle_wifi(False)