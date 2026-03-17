import subprocess
import time
from typing import List, Optional


class AdbClient:

    def __init__(
        self,
        package_name: str = "com.tencent.tmgp.dfm",
        launch_activity: str = "com.epicgames.ue4.SplashActivity",
        serial: Optional[str] = None,
        adb_path: str = "adb",
    ):
        self.package_name = package_name
        self.launch_activity = launch_activity
        self.serial = serial
        self.adb_path = adb_path

    def _build_adb_shell_cmd(self, cmd_list: List[str]) -> List[str]:
        full_cmd = [self.adb_path]
        if self.serial:
            full_cmd.extend(["-s", self.serial])
        full_cmd.extend(["shell", *cmd_list])
        return full_cmd

    def execute_shell(self, cmd_list: List[str], timeout: int = 15) -> None:
        """执行 adb shell 命令；失败时抛出 RuntimeError。"""
        full_cmd = self._build_adb_shell_cmd(cmd_list)
        try:
            result = subprocess.run(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
        except Exception as e:
            raise RuntimeError(f"ADB 执行异常: {e}") from e

        if result.returncode != 0:
            error_msg = (
                result.stderr.strip() or result.stdout.strip() or "unknown error"
            )
            raise RuntimeError(f"ADB 命令失败: {' '.join(full_cmd)} | {error_msg}")

    def restart_app(self, wait_seconds: float = 1.0) -> None:
        """重启应用。"""
        self.execute_shell(["am", "force-stop", self.package_name])
        time.sleep(wait_seconds)
        self.execute_shell(
            [
                "am",
                "start",
                "-n",
                f"{self.package_name}/{self.launch_activity}",
            ]
        )

    def toggle_wifi(self, enable: bool) -> None:
        """开关 WiFi。"""
        if enable:
            self.execute_shell(["svc", "wifi", "enable"])
        else:
            self.execute_shell(["svc", "wifi", "disable"])

    def wifi_on(self) -> None:
        """开启 WiFi。"""
        self.toggle_wifi(True)

    def wifi_off(self) -> None:
        """关闭 WiFi。"""
        self.toggle_wifi(False)
