import time
import subprocess
import threading
import scrcpy
from .logger import logger


class Device:
    def __init__(self, device_id=None, block_frame=True):
        self.latest_frame = None
        self.latest_frame_ts = 0
        self.frame_event = threading.Event()
        self.client = scrcpy.Client(device=device_id, block_frame=block_frame)
        self.client.add_listener(scrcpy.EVENT_FRAME, self._on_frame)
        self.pkg_name = "com.tencent.tmgp.dfm"

    def start(self):
        self.client.start(threaded=True)

    def stop(self):
        self.client.stop()

    def _on_frame(self, frame):
        if frame is not None:
            self.latest_frame = frame
            self.latest_frame_ts = time.time()
            self.frame_event.set()

    def get_frame(self, timeout=1.0):
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
        return self.client.control

    def _adb_command(self, cmd_list: list) -> bool:
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
        self._adb_command(["am", "force-stop", self.pkg_name])
        time.sleep(1)
        self._adb_command(
            ["am", "start", "-n", f"{self.pkg_name}/com.epicgames.ue4.SplashActivity"]
        )

    def wifi_on(self):
        return self._adb_command(["svc", "wifi", "enable"])

    def wifi_off(self):
        return self._adb_command(["svc", "wifi", "disable"])
