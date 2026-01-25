"""
设备控制模块
整合了设备交互、触摸控制和模板匹配功能
"""

import time
import subprocess
import threading
import json
import cv2
import numpy as np
import scrcpy
from pathlib import Path
from typing import Tuple, Optional, Dict
from scrcpy.control import ControlSender
from logger import logger


class Matcher:
    """模板匹配器，用于在屏幕上查找特定图像"""

    def __init__(self):
        logger.debug("正在初始化模板匹配引擎")
        self.template_dir = Path("templates")
        self.coords_file = self.template_dir / "coords.json"
        self.coords = {}
        self._load_coords()
        self.threshold = 0.8

    def _load_coords(self):
        """加载坐标配置文件"""
        if self.coords_file.exists():
            try:
                with open(self.coords_file, "r", encoding="utf-8") as f:
                    self.coords = json.load(f)
                logger.debug(f"已加载 {len(self.coords)} 个模板的坐标")
            except Exception as e:
                logger.error(f"加载 coords.json 失败: {e}")
        else:
            logger.warning(
                "在 templates 目录中未找到 coords.json。请使用 template_picker.py 创建模板。"
            )

    def _get_template_path(self, name: str) -> Path:
        """获取模板图片路径"""
        return self.template_dir / f"{name}.png"

    def find_template(self, frame: np.ndarray, target: str) -> Optional[Dict]:
        """
        在帧中查找指定模板
        
        Args:
            frame: 屏幕帧图像
            target: 目标模板名称
            
        Returns:
            匹配结果字典，包含 text、center、score 等信息，未找到返回 None
        """
        if target not in self.coords:
            self._load_coords()
            if target not in self.coords:
                logger.warning(f"目标 '{target}' 未在 coords.json 中定义")
                return None

        coords = self.coords[target]
        if len(coords) != 4:
            return None

        x1, y1, x2, y2 = coords

        h, w = frame.shape[:2]

        x1 = max(0, min(x1, w))
        y1 = max(0, min(y1, h))
        x2 = max(0, min(x2, w))
        y2 = max(0, min(y2, h))

        if x2 <= x1 or y2 <= y1:
            return None

        crop = frame[y1:y2, x1:x2]

        template_path = self._get_template_path(target)
        if not template_path.exists():
            logger.error(f"未找到模板图片: {template_path}")
            return None

        template = cv2.imread(str(template_path))
        if template is None:
            logger.error(f"加载模板图片失败: {template_path}")
            return None

        try:
            start_time = time.time()
            res = cv2.matchTemplate(crop, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            duration = (time.time() - start_time) * 1000

            if max_val >= self.threshold:
                th, tw = template.shape[:2]
                center_x_crop = max_loc[0] + tw // 2
                center_y_crop = max_loc[1] + th // 2

                center_x = x1 + center_x_crop
                center_y = y1 + center_y_crop

                logger.debug(
                    f"找到 '{target}' 匹配度={max_val:.2f} 坐标=({center_x}, {center_y}), 耗时={duration:.2f}ms"
                )

                return {
                    "text": target,
                    "center": (center_x, center_y),
                    "score": float(max_val),
                    "box": None,
                }
            else:
                logger.debug(
                    f"'{target}' 未找到 (匹配度 {max_val:.2f} < {self.threshold})"
                )
                return None

        except Exception as e:
            logger.error(f"匹配模板 '{target}' 时出错: {e}")
            return None


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
        self._scrcpy_lock = threading.Lock()

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

    def has_template(self, template_name: str) -> bool:
        """检查是否存在指定模板"""
        return self.fetch_template_coords(template_name) is not None

    def get_template_center(self, template_name: str) -> Optional[Tuple[int, int]]:
        """
        从 coords.json 获取模板的静态中心坐标
        
        Args:
            template_name: 模板名称
            
        Returns:
            坐标元组 (x, y)，未找到返回 None
        """
        if template_name in self.matcher.coords:
            x1, y1, x2, y2 = self.matcher.coords[template_name]
            return (x1 + x2) // 2, (y1 + y2) // 2
        return None

    def fetch_template_coords(
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

    def _safe_touch(
        self, control: ControlSender, coord: Tuple[int, int], action: int, touch_id: int
    ):
        """线程安全的触摸操作"""
        with self._scrcpy_lock:
            control.touch(coord[0], coord[1], action, touch_id=touch_id)

    def _spam_tap(
        self,
        control: ControlSender,
        coord: Tuple[int, int],
        touch_id: int,
        duration: float,
    ) -> int:
        """快速连续点击"""
        start = time.time()
        count = 0
        while time.time() - start < duration:
            self._safe_touch(control, coord, scrcpy.const.ACTION_DOWN, touch_id)
            time.sleep(0.05)
            self._safe_touch(control, coord, scrcpy.const.ACTION_UP, touch_id)
            count += 1
        return count

    def _single_tap(
        self, control: ControlSender, coord: Tuple[int, int], touch_id: int
    ):
        """单次点击"""
        self._safe_touch(control, coord, scrcpy.const.ACTION_DOWN, touch_id)
        time.sleep(0.05)
        self._safe_touch(control, coord, scrcpy.const.ACTION_UP, touch_id)

    def multitouch(
        self,
        main_coord: Tuple[int, int],
        sub_coord: Tuple[int, int],
        duration: float = 1.0,
        sub_delay: float = 0.5,
    ) -> bool:
        """
        多点触控操作
        
        Args:
            main_coord: 主触点坐标，会连续点击
            sub_coord: 副触点坐标，延迟后单次点击
            duration: 主触点持续时间（秒）
            sub_delay: 副触点延迟时间（秒）
            
        Returns:
            操作是否成功
        """
        try:
            ctrl = self.get_control()

            id_main = 1
            id_sub = 2

            def thread_main():
                self._spam_tap(ctrl, main_coord, touch_id=id_main, duration=duration)

            def thread_sub():
                time.sleep(sub_delay)
                self._single_tap(ctrl, sub_coord, touch_id=id_sub)

            t1 = threading.Thread(target=thread_main)
            t2 = threading.Thread(target=thread_sub)

            t1.start()
            t2.start()

            t1.join()
            t2.join()

            return True

        except Exception:
            return False
