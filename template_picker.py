"""
模板选择器工具
用于在屏幕上框选并保存游戏元素作为模板
"""

import cv2
import os
import time
import json
from device import Device


class TemplatePicker:
    """模板选择器，用于框选和保存屏幕区域作为识别模板"""

    def __init__(self, display_width=1920):
        """
        初始化模板选择器

        Args:
            display_width: 预览窗口的最大宽度
        """
        # 初始化设备
        self.device = Device(block_frame=True)
        self.device.start()

        # 状态变量
        self.drawing = False
        self.paused = False
        self.start_point = None  # 存储预览图上的坐标
        self.end_point = None  # 存储预览图上的坐标

        self.current_frame = None  # 原始高分辩率帧 (用于保存)
        self.preview = None  # 预览用的低分辻率帧 (缓存用于显示)
        self.scale_factor = 1.0  # 缩放比例 (原图/预览图)
        self.display_width = display_width
        # 创建输出目录
        if not os.path.exists("templates"):
            os.makedirs("templates")

    def get_real_coords(self, x, y):
        """将预览图坐标(x,y) 映射回 原图坐标"""
        if self.scale_factor == 0:
            return 0, 0
        return int(x * self.scale_factor), int(y * self.scale_factor)

    def mouse_callback(self, event, x, y, flags, param):
        """鼠标回调：记录的是预览窗口上的坐标"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_point = (x, y)
            self.end_point = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.end_point = (x, y)

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            self.end_point = (x, y)
            # 自动保存逻辑：如果有拖拽动作
            if self.start_point and self.end_point:
                # 计算拖拽距离，防止误触点击
                dist = (
                    (self.start_point[0] - self.end_point[0]) ** 2
                    + (self.start_point[1] - self.end_point[1]) ** 2
                ) ** 0.5
                if dist > 5:
                    self._save_template()

    def _save_template(self):
        """根据映射坐标从原图中裁剪"""
        if (
            self.current_frame is None
            or self.start_point is None
            or self.end_point is None
        ):
            return

        # 1. 获取显示坐标
        x1_disp, y1_disp = self.start_point
        x2_disp, y2_disp = self.end_point

        # 2. 映射回原图真实坐标
        rx1, ry1 = self.get_real_coords(x1_disp, y1_disp)
        rx2, ry2 = self.get_real_coords(x2_disp, y2_disp)

        # 3. 整理坐标 (min/max)
        x1, x2 = min(rx1, rx2), max(rx1, rx2)
        y1, y2 = min(ry1, ry2), max(ry1, ry2)

        # 4. 边界安全检查
        h, w = self.current_frame.shape[:2]
        x1, x2 = max(0, x1), min(w, x2)
        y1, y2 = max(0, y1), min(h, y2)

        # 5. 无效区域检查
        if x2 <= x1 or y2 <= y1:
            print("区域无效，未保存")
            return

        # 6. 从原图裁剪
        template = self.current_frame[y1:y2, x1:x2].copy()

        # 7. 询问模版名称
        print("\n" + "=" * 30)
        name = input("请输入模版名称 (直接回车取消): ").strip()
        if not name:
            print("已取消保存")
            return

        # 8. 保存图片
        filename = f"templates/{name}.png"
        cv2.imwrite(filename, template)

        # 9. 保存坐标
        coords_file = "templates/coords.json"
        coords_data = {}
        if os.path.exists(coords_file):
            try:
                with open(coords_file, "r", encoding="utf-8") as f:
                    coords_data = json.load(f)
            except Exception as e:
                print(f"读取坐标文件失败: {e}")

        coords_data[name] = [x1, y1, x2, y2]

        try:
            with open(coords_file, "w", encoding="utf-8") as f:
                json.dump(coords_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存坐标失败: {e}")
            return

        print(f"[保存成功] {filename}")
        print(f"  └─ 坐标: {x1}, {y1}, {x2}, {y2}")
        print("=" * 30 + "\n")

    def run(self):
        """启动模板选择器"""
        window_name = "Template Picker"
        cv2.namedWindow(window_name, cv2.WINDOW_GUI_NORMAL)
        cv2.setMouseCallback(window_name, self.mouse_callback)

        print(f"启动模版框选工具... 预览宽度限制: {self.display_width}px")
        print("操作:")
        print("  - [F] 键: 冻结/解冻画面 (推荐冻结后框选)")
        print("  - 鼠标拖拽: 直接保存选区")
        print("  - [Q] 键: 退出")

        try:
            while True:
                # 获取/更新帧
                if not self.paused:
                    frame = self.device.get_frame()
                    if frame is not None:
                        self.current_frame = frame

                        # 计算缩放比例并生成预览图
                        h, w = frame.shape[:2]
                        if w > self.display_width:
                            self.scale_factor = w / self.display_width
                            new_h = int(h / self.scale_factor)
                            self.preview = cv2.resize(
                                frame,
                                (self.display_width, new_h),
                                interpolation=cv2.INTER_NEAREST,
                            )
                        else:
                            self.scale_factor = 1.0
                            self.preview = frame.copy()

                if self.preview is None:
                    time.sleep(0.01)
                    continue

                # 在预览图副本上绘制 UI
                display_img = self.preview.copy()

                # 绘制鼠标选框
                if self.drawing and self.start_point and self.end_point:
                    cv2.rectangle(
                        display_img, self.start_point, self.end_point, (0, 255, 0), 2
                    )

                    # 显示当前选框对应的真实尺寸
                    cw, ch = abs(self.start_point[0] - self.end_point[0]), abs(
                        self.start_point[1] - self.end_point[1]
                    )
                    rw, rh = int(cw * self.scale_factor), int(ch * self.scale_factor)
                    cv2.putText(
                        display_img,
                        f"Real: {rw}x{rh}",
                        (self.start_point[0], self.start_point[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )

                cv2.imshow(window_name, display_img)

                # 按键处理
                key = cv2.waitKey(20) & 0xFF
                if key == ord("q") or key == ord("Q"):
                    break
                elif key == ord("f") or key == ord("F"):
                    self.paused = not self.paused

        except KeyboardInterrupt:
            pass
        finally:
            self.device.stop()
            cv2.destroyAllWindows()
            print("资源已释放")


if __name__ == "__main__":
    picker = TemplatePicker(display_width=1280)
    picker.run()
