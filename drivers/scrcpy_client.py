import os
import struct
import threading
import time
from typing import Optional, Tuple

import numpy as np
from adbutils import adb, AdbError, Network
from av.codec import CodecContext
from av.error import InvalidDataError

# --- 常量定义 ---
ACTION_DOWN = 0
ACTION_UP = 1
ACTION_MOVE = 2
TYPE_INJECT_TOUCH_EVENT = 2

# --- 控制模块 ---
class ControlSender:
    def __init__(self, parent):
        self.parent = parent

    def touch(self, x: int, y: int, action: int = ACTION_DOWN, touch_id: int = 0x1234567887654321):
        """发送触摸事件"""
        if not self.parent.resolution:
            return
            
        x, y = max(x, 0), max(y, 0)
        pressure = 0 if action == ACTION_UP else 0xFFFF
        
        # 组装数据包: 类型(1字节) + 动作(1字节) + ID(8字节) + X(4字节) + Y(4字节) + 宽(2字节) + 高(2字节) + 压力(2字节) + 其他(8字节)
        touch_data = struct.pack(
            ">BqiiHHHii",
            action, touch_id, int(x), int(y),
            int(self.parent.resolution[0]), int(self.parent.resolution[1]),
            pressure, 0, 0
        )
        package = struct.pack(">B", TYPE_INJECT_TOUCH_EVENT) + touch_data
        
        if self.parent.control_socket is not None:
            with self.parent.control_socket_lock:
                self.parent.control_socket.send(package)

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, move_step_length: int = 5, move_steps_delay: float = 0.005):
        """滑动屏幕"""
        self.touch(start_x, start_y, ACTION_DOWN)
        
        next_x, next_y = start_x, start_y
        max_x, max_y = self.parent.resolution[0], self.parent.resolution[1]
        end_x, end_y = min(end_x, max_x), min(end_y, max_y)

        decrease_x = start_x > end_x
        decrease_y = start_y > end_y
        
        while True:
            if decrease_x:
                next_x = max(next_x - move_step_length, end_x)
            else:
                next_x = min(next_x + move_step_length, end_x)
                
            if decrease_y:
                next_y = max(next_y - move_step_length, end_y)
            else:
                next_y = min(next_y + move_step_length, end_y)

            self.touch(next_x, next_y, ACTION_MOVE)

            if next_x == end_x and next_y == end_y:
                self.touch(next_x, next_y, ACTION_UP)
                break
            time.sleep(move_steps_delay)

class ScrcpyClient:
    def __init__(self, device_serial: Optional[str] = None, max_width: int = 0, bitrate: int = 8000000, max_fps: int = 0, flip: bool = False):
        self.flip = flip
        self.max_width = max_width
        self.bitrate = bitrate
        self.max_fps = max_fps
        
        self.device = adb.device(serial=device_serial) if device_serial else adb.device_list()[0]
        
        self.resolution: Optional[Tuple[int, int]] = None
        self.control = ControlSender(self)
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_index: int = 0
        
        self.alive = False
        self.__server_stream = None
        self.__video_socket = None
        self.control_socket = None
        self.control_socket_lock = threading.Lock()
        self._frame_condition = threading.Condition()

    def __deploy_server(self):
        jar_name = "scrcpy-server-v3.3.4"
        server_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), jar_name)
        self.device.sync.push(server_file_path, f"/data/local/tmp/{jar_name}")
        
        commands = [
            f"CLASSPATH=/data/local/tmp/{jar_name}", "app_process", "/", "com.genymobile.scrcpy.Server",
            "3.3.4", "log_level=info", f"max_size={self.max_width}", f"max_fps={self.max_fps}",
            f"video_bit_rate={self.bitrate}", "tunnel_forward=true", "send_frame_meta=false",
            "control=true", "audio=false", "show_touches=false", "stay_awake=false",
            "power_off_on_close=false", "clipboard_autosync=false"
        ]
        self.__server_stream = self.device.shell(commands, stream=True)
        self.__server_stream.read(10)

    def __init_server_connection(self):
        for _ in range(30):
            try:
                self.__video_socket = self.device.create_connection(Network.LOCAL_ABSTRACT, "scrcpy")
                break
            except AdbError:
                time.sleep(0.1)
        else:
            raise ConnectionError("连接 scrcpy-server 失败")

        dummy_byte = self.__video_socket.recv(1)
        if not dummy_byte or dummy_byte != b"\x00":
            raise ConnectionError("未收到 Dummy Byte")

        self.control_socket = self.device.create_connection(Network.LOCAL_ABSTRACT, "scrcpy")
        self.device_name = self.__video_socket.recv(64).decode("utf-8").rstrip("\x00")
        
        res = self.__video_socket.recv(4)
        self.resolution = struct.unpack(">HH", res)
        self.__video_socket.setblocking(False)

    def start(self):
        """以后台线程方式启动客户端"""
        if self.alive: return
        self.__deploy_server()
        self.__init_server_connection()
        self.alive = True
        
        threading.Thread(target=self.__stream_loop, daemon=True).start()

    def stop(self):
        """停止客户端并清理连接"""
        self.alive = False
        for sock in [self.__video_socket, self.control_socket, self.__server_stream]:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
        with self._frame_condition:
            self._frame_condition.notify_all()

    def get_latest_frame(self, last_seen_index: Optional[int] = None, timeout: float = 1.0) -> Tuple[Optional[np.ndarray], int]:
        """
        获取当前最新帧。
        传入 last_seen_index 可阻塞等待直到出现比它更新的帧。
        返回: (BGR numpy 数组, 当前帧序号)
        """
        deadline = time.monotonic() + timeout
        with self._frame_condition:
            while self.alive:
                has_new_frame = (last_seen_index is None or self.frame_index > last_seen_index)
                if self.latest_frame is not None and has_new_frame:
                    return self.latest_frame, self.frame_index

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._frame_condition.wait(remaining)

            return self.latest_frame, self.frame_index

    def __stream_loop(self):
        codec = CodecContext.create("h264", "r")
        
        assert self.__video_socket is not None
        while self.alive:
            try:
                raw_h264 = self.__video_socket.recv(0x10000)
                if not raw_h264:
                    break
                    
                for packet in codec.parse(raw_h264):
                    for frame in codec.decode(packet):
                        img_array = frame.to_ndarray(format="bgr24")
                        if self.flip:
                            img_array = np.ascontiguousarray(img_array[:, ::-1, :])
                            
                        self.resolution = (img_array.shape[1], img_array.shape[0])
                        with self._frame_condition:
                            self.latest_frame = img_array
                            self.frame_index += 1
                            self._frame_condition.notify_all()
                            
            except (BlockingIOError, InvalidDataError):
                time.sleep(0.005)
            except (ConnectionError, OSError):
                break
        self.stop()