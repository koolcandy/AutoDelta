"""
设备管理器类，负责设备连接和基本操作
"""
import time
import subprocess
import threading
import scrcpy
from ..utils.logger import logger


class DeviceManager:
    def __init__(self, device_id=None, block_frame=True):
        self.latest_frame = None
        self.latest_frame_ts = 0
        self.frame_event = threading.Event()
        self.client = scrcpy.Client(device=device_id, block_frame=block_frame)
        self.client.add_listener(scrcpy.EVENT_FRAME, self._on_frame)
        self.pkg_name = "com.tencent.tmgp.dfm"

    def start(self):
        """启动设备连接"""
        self.client.start(threaded=True)

    def stop(self):
        """停止设备连接"""
        self.client.stop()

    def _on_frame(self, frame):
        """帧更新回调"""
        if frame is not None:
            self.latest_frame = frame
            self.latest_frame_ts = time.time()
            self.frame_event.set()

    def get_frame(self, timeout=1.0):
        """获取当前帧"""
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

    def _adb_command(self, cmd_list: list) -> bool:
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
        logger.info("正在重启应用...")
        self._adb_command(["am", "force-stop", self.pkg_name])
        time.sleep(1)
        self._adb_command(
            ["am", "start", "-n", f"{self.pkg_name}/com.epicgames.ue4.SplashActivity"]
        )

    def wifi_on(self):
        """开启WiFi"""
        logger.info("开启WiFi")
        return self._adb_command(["svc", "wifi", "enable"])

    def wifi_off(self):
        """关闭WiFi"""
        logger.info("关闭WiFi")
        return self._adb_command(["svc", "wifi", "disable"])