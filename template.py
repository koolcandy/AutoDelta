"""
模板选择器工具
用于在屏幕上框选并保存游戏元素作为模板
"""

import cv2
import os
import time
import json
import re
import numpy as np
import easyocr
from core.agent import Agent
import subprocess


class TemplatePicker:
    """模板选择器，用于框选和保存屏幕区域作为识别模板"""

    def __init__(self, display_width=1920):
        """
        初始化模板选择器

        Args:
            display_width: 预览窗口的最大宽度
        """
        # 初始化设备
        self.operator = Agent()
        self.operator.start()

        # 状态变量
        self.drawing = False
        self.paused = False
        self.start_point = None  # 存储预览图上的坐标
        self.end_point = None  # 存储预览图上的坐标

        self.current_frame = None  # 原始高分辩率帧 (用于保存)
        self.preview = None  # 预览用的低分辻率帧 (缓存用于显示)
        self.scale_factor = 1.0  # 缩放比例 (原图/预览图)
        self.display_width = display_width
        self.ocr_reader = None
        self.last_ocr_quad = None  # 最近一次 OCR 命中的四点坐标(原图)
        self.last_ocr_text = ""
        # 创建输出目录
        if not os.path.exists("templates"):
            os.makedirs("templates")

    def _ensure_ocr_reader(self):
        """懒加载 EasyOCR，避免启动时初始化过慢"""
        if self.ocr_reader is None:
            print("正在初始化 EasyOCR (首次会稍慢)...")
            self.ocr_reader = easyocr.Reader(["ch_sim", "en"])

    @staticmethod
    def _normalize_text(text):
        """统一文本用于匹配：小写并移除空白"""
        if not text:
            return ""
        return re.sub(r"\s+", "", text).lower()

    @staticmethod
    def _sanitize_terminal_input(value):
        """兼容部分终端将回车编码为 CSI-u 序列（如 ^[[13u）"""
        if value is None:
            return ""

        cleaned = value
        # 1) 去掉实际 ANSI/CSI 控制序列（覆盖 CSI-u 如 \x1b[13u / \x1b[13;1u）
        cleaned = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", cleaned)
        # 2) 去掉字面量形式 \x1b[13u（部分终端/日志会把 ESC 展示为文本）
        cleaned = re.sub(r"\\x1b\[[0-9;:]*[A-Za-z~]", "", cleaned, flags=re.IGNORECASE)
        # 3) 去掉 caret 可见形式 ^[[13u / ^[[13;1u
        cleaned = re.sub(r"\^\[\[[0-9;:]*[A-Za-z~]", "", cleaned)
        # 3.1) 去掉无 ESC 的残片形式，如 [[13u / [13u / ^[[13u 的变体
        cleaned = re.sub(r"(?:\^\[\[|\[\[|\[)[0-9;:]*[A-Za-z~]", "", cleaned)
        # 4) 兜底：若控制序列仍以尾巴形式存在，截掉尾巴
        cleaned = re.sub(r"(?:\x1b\[[0-9;:]*[A-Za-z~]|\^\[\[[0-9;:]*[A-Za-z~])+$", "", cleaned)
        # 5) 清理可能残留的裸 ^[ 和多余空白
        cleaned = cleaned.replace("^[", "")
        return cleaned.strip()

    def _read_input(self, prompt):
        """使用 macOS 原生弹窗获取输入，完美避开终端和 Tkinter 冲突"""
        # 清理 prompt 中可能导致 AppleScript 语法错误的引号
        safe_prompt = prompt.replace('"', "'")
        
        # 编写 AppleScript 调用系统原生输入框
        apple_script = f'''
        tell application "System Events"
            activate
            set dialog_result to display dialog "{safe_prompt}" default answer "" buttons {{"取消", "确定"}} default button "确定" with title "模板选择器"
            if button returned of dialog_result is "确定" then
                return text returned of dialog_result
            else
                return ""
            end if
        end tell
        '''
        
        try:
            # 执行脚本并捕获输出
            result = subprocess.run(
                ['osascript', '-e', apple_script],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            # 用户点击了"取消"或按了 ESC 键，osascript 会抛出异常
            return ""
    @staticmethod
    def _order_quad_points(pts):
        """将四点排序为 tl, tr, br, bl，便于透视裁剪"""
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def _extract_quad_patch(self, frame, quad):
        """根据 OCR 四点框进行透视变换，得到紧贴文字区域的裁剪图"""
        pts = np.array(quad, dtype=np.float32)
        if pts.shape != (4, 2):
            return None

        rect = self._order_quad_points(pts)
        (tl, tr, br, bl) = rect

        width_a = np.linalg.norm(br - bl)
        width_b = np.linalg.norm(tr - tl)
        height_a = np.linalg.norm(tr - br)
        height_b = np.linalg.norm(tl - bl)

        max_width = int(max(width_a, width_b))
        max_height = int(max(height_a, height_b))

        if max_width <= 0 or max_height <= 0:
            return None

        dst = np.array(
            [
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1],
            ],
            dtype=np.float32,
        )

        matrix = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(frame, matrix, (max_width, max_height))
        return warped

    def _save_template_image_and_coords(self, template, x1, y1, x2, y2, default_name=""):
        """保存模板图片和坐标配置"""
        print("\n" + "=" * 30)
        prompt = "请输入模版名称 (直接回车取消): "
        if default_name:
            prompt = f"请输入模版名称 (默认: {default_name}, 直接回车使用默认): "

        name = self._read_input(prompt)
        if not name and default_name:
            name = default_name

        if not name:
            print("已取消保存")
            return

        filename = f"templates/{name}.png"
        cv2.imwrite(filename, template)

        coords_file = "templates/coords.json"
        coords_data = {}
        if os.path.exists(coords_file):
            try:
                with open(coords_file, "r", encoding="utf-8") as f:
                    coords_data = json.load(f)
            except Exception as e:
                print(f"读取坐标文件失败: {e}")

        coords_data[name] = [int(x1), int(y1), int(x2), int(y2)]

        try:
            with open(coords_file, "w", encoding="utf-8") as f:
                json.dump(coords_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存坐标失败: {e}")
            return

        print(f"[保存成功] {filename}")
        print(f"  └─ 坐标: {x1}, {y1}, {x2}, {y2}")
        print("=" * 30 + "\n")

    def _save_template_by_target_text(self):
        """输入目标文字，使用 EasyOCR 自动定位后裁剪保存"""
        if self.current_frame is None:
            print("当前没有可用画面")
            return

        target_text = self._read_input("请输入要查找的目标文字 (直接回车取消): ")
        if not target_text:
            print("已取消 OCR 查找")
            return

        self._ensure_ocr_reader()
        reader = self.ocr_reader
        if reader is None:
            print("EasyOCR 初始化失败")
            return

        try:
            results = reader.readtext(self.current_frame, detail=1)
        except Exception as e:
            print(f"OCR 执行失败: {e}")
            return

        if not results:
            print("未识别到任何文字")
            return

        target_norm = self._normalize_text(target_text)
        exact_matches = []
        contains_matches = []

        for quad, text, conf in results:
            text_norm = self._normalize_text(text)
            if not text_norm:
                continue

            if text_norm == target_norm:
                exact_matches.append((quad, text, conf))
            elif target_norm in text_norm or text_norm in target_norm:
                contains_matches.append((quad, text, conf))

        candidates = exact_matches if exact_matches else contains_matches
        if not candidates:
            print(f"未找到目标文字: {target_text}")
            return

        best_quad, best_text, best_conf = max(candidates, key=lambda x: x[2])
        template = self._extract_quad_patch(self.current_frame, best_quad)
        if template is None or template.size == 0:
            print("目标文字裁剪失败")
            return

        pts = np.array(best_quad, dtype=np.float32)
        h, w = self.current_frame.shape[:2]
        x1 = max(0, int(np.floor(np.min(pts[:, 0]))))
        y1 = max(0, int(np.floor(np.min(pts[:, 1]))))
        x2 = min(w, int(np.ceil(np.max(pts[:, 0]))))
        y2 = min(h, int(np.ceil(np.max(pts[:, 1]))))

        self.last_ocr_quad = self._order_quad_points(pts)
        self.last_ocr_text = best_text

        safe_default = re.sub(r"[^0-9a-zA-Z_\u4e00-\u9fff-]+", "_", target_text).strip("_")
        print(f"命中 OCR 文本: '{best_text}' (置信度: {best_conf:.3f})")
        self._save_template_image_and_coords(
            template,
            x1,
            y1,
            x2,
            y2,
            default_name=safe_default,
        )

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

        self._save_template_image_and_coords(template, x1, y1, x2, y2)

    def run(self):
        """启动模板选择器"""
        window_name = "Template Picker"
        cv2.namedWindow(window_name, cv2.WINDOW_GUI_NORMAL)
        cv2.setMouseCallback(window_name, self.mouse_callback)

        print(f"启动模版框选工具... 预览宽度限制: {self.display_width}px")
        print("操作:")
        print("  - [F] 键: 冻结/解冻画面 (推荐冻结后框选)")
        print("  - 鼠标拖拽: 直接保存选区")
        print("  - [T] 键: 输入目标文字，OCR 自动定位并裁剪保存")
        print("  - [Q] 键: 退出")

        try:
            while True:
                # 获取/更新帧
                if not self.paused:
                    frame = self.operator.get_frame()
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

                # 显示最近一次 OCR 命中框
                if self.last_ocr_quad is not None and len(self.last_ocr_quad) == 4:
                    pts = np.array(
                        [
                            [int(p[0] / self.scale_factor), int(p[1] / self.scale_factor)]
                            for p in self.last_ocr_quad
                        ],
                        dtype=np.int32,
                    )
                    cv2.polylines(display_img, [pts], True, (0, 200, 255), 2)
                    if self.last_ocr_text:
                        tx = max(0, pts[0][0])
                        ty = max(20, pts[0][1] - 8)
                        cv2.putText(
                            display_img,
                            f"OCR: {self.last_ocr_text}",
                            (tx, ty),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 200, 255),
                            2,
                        )

                cv2.imshow(window_name, display_img)

                # 按键处理
                key = cv2.waitKey(20) & 0xFF
                if key == ord("q") or key == ord("Q"):
                    break
                elif key == ord("f") or key == ord("F"):
                    self.paused = not self.paused
                elif key == ord("t") or key == ord("T"):
                    self._save_template_by_target_text()

        except KeyboardInterrupt:
            pass
        finally:
            self.operator.stop()
            cv2.destroyAllWindows()
            print("资源已释放")


if __name__ == "__main__":
    picker = TemplatePicker(display_width=1280)
    picker.run()
