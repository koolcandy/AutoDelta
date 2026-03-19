"""
模板选择器工具
用于在屏幕上框选并保存游戏元素作为模板
"""

import cv2
import os
import time
import json
import re
from typing import Any
import numpy as np
from rapidocr import RapidOCR
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from core.agent import Agent


class TemplatePicker:

    def __init__(self):
        # 初始化设备
        self.operator = Agent()
        self.operator.start()

        # 状态变量
        self.drawing = False
        self.paused = False
        self.start_point = None  # 存储原图坐标
        self.end_point = None  # 存储原图坐标

        self.current_frame = None  # 原始高分辩率帧 (用于保存)
        self.preview = None  # 预览用的低分辻率帧 (缓存用于显示)
        self.scale_factor_x = 1.0  # X 轴缩放比例 (原图/预览图)
        self.scale_factor_y = 1.0  # Y 轴缩放比例 (原图/预览图)
        self.preview_offset_x = 0  # 预览图在 QLabel 内的 X 偏移
        self.preview_offset_y = 0  # 预览图在 QLabel 内的 Y 偏移
        self.preview_draw_w = 1
        self.preview_draw_h = 1
        self.ocr_reader = None
        self.qt_app: Any = None
        self.status_panel: Any = None
        self.status_label: Any = None
        self.last_ocr_quad = None  # 最近一次 OCR 命中的四点坐标(原图)
        self.last_ocr_text = ""
        # 创建输出目录
        if not os.path.exists("templates"):
            os.makedirs("templates")

    def _ensure_ocr_reader(self):
        """懒加载 RapidOCR，避免启动时初始化过慢"""
        if self.ocr_reader is None:
            self._set_status("正在初始化 RapidOCR（首次会稍慢）")
            self.ocr_reader = RapidOCR()

    @staticmethod
    def _rapidocr_entries(result):
        """将 RapidOCR 返回值转换为 (quad, text, score) 列表。"""
        if result is None:
            return []

        boxes = getattr(result, "boxes", None)
        txts = getattr(result, "txts", None)
        scores = getattr(result, "scores", None)
        if boxes is None or txts is None or scores is None:
            return []

        entries = []
        for quad, text, score in zip(boxes, txts, scores):
            if text is None:
                continue

            try:
                score_value = float(score)
            except (TypeError, ValueError):
                score_value = 0.0

            entries.append((np.array(quad, dtype=np.float32), str(text), score_value))

        return entries

    def _set_status(self, message):
        """在 Qt 页面内输出状态信息"""
        if not message:
            return
        if self.status_panel is not None:
            self.status_panel.appendPlainText(message)
        if self.status_label is not None:
            self.status_label.setText(message)

    @staticmethod
    def _normalize_text(text):
        """统一文本用于匹配：小写并移除空白"""
        if not text:
            return ""
        return re.sub(r"\s+", "", text).lower()

    def _ensure_qt_app(self):
        """确保存在 Qt 应用实例"""
        if self.qt_app is None:
            self.qt_app = QApplication.instance()
            if self.qt_app is None:
                self.qt_app = QApplication([])
                self.qt_app.setQuitOnLastWindowClosed(False)
        return True

    def _read_input(self, prompt, default_text=""):
        """使用 Qt 输入框获取输入"""
        if self._ensure_qt_app():
            try:
                text, ok = QInputDialog.getText(
                    None,
                    "模板选择器",
                    prompt,
                    QLineEdit.EchoMode.Normal,
                    default_text,
                )
                return text.strip() if ok else ""
            except Exception:
                return ""
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
        prompt = "请输入模板名称 (直接回车取消): "
        if default_name:
            prompt = "请输入模板名称 (可直接确认使用默认值): "

        name = self._read_input(prompt, default_text=default_name)
        if not name and default_name:
            name = default_name

        if not name:
            self._set_status("已取消保存")
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
                self._set_status(f"读取坐标文件失败: {e}")

        coords_data[name] = [int(x1), int(y1), int(x2), int(y2)]

        try:
            with open(coords_file, "w", encoding="utf-8") as f:
                json.dump(coords_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._set_status(f"保存坐标失败: {e}")
            return

        self._set_status(f"保存成功: {filename} | 坐标: {x1}, {y1}, {x2}, {y2}")

    def _save_template_by_target_text(self):
        """输入目标文字，使用 RapidOCR 自动定位后裁剪保存"""
        if self.current_frame is None:
            self._set_status("当前没有可用画面")
            return

        target_text = self._read_input("请输入要查找的目标文字 (直接回车取消): ")
        if not target_text:
            self._set_status("已取消 OCR 查找")
            return

        self._ensure_ocr_reader()
        reader = self.ocr_reader
        if reader is None:
            self._set_status("RapidOCR 初始化失败")
            return

        try:
            result = reader(self.current_frame)
            results = self._rapidocr_entries(result)
        except Exception as e:
            self._set_status(f"OCR 执行失败: {e}")
            return

        if not results:
            self._set_status("未识别到任何文字")
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
            self._set_status(f"未找到目标文字: {target_text}")
            return

        best_quad, best_text, best_conf = max(candidates, key=lambda x: x[2])
        template = self._extract_quad_patch(self.current_frame, best_quad)
        if template is None or template.size == 0:
            self._set_status("目标文字裁剪失败")
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
        self._set_status(f"命中 OCR 文本: '{best_text}' (置信度: {best_conf:.3f})")
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
        if self.scale_factor_x == 0 or self.scale_factor_y == 0:
            return 0, 0
        return int(x * self.scale_factor_x), int(y * self.scale_factor_y)

    @staticmethod
    def _get_qt_mouse_pos(event):
        """兼容不同 Qt 事件对象的坐标读取"""
        if hasattr(event, "position"):
            point = event.position()
            return int(point.x()), int(point.y())
        point = event.pos()
        return int(point.x()), int(point.y())

    def _map_label_to_real_coords(self, x, y):
        """将 QLabel 坐标映射到原图坐标，自动处理居中偏移与等比例缩放"""
        if self.current_frame is None:
            return None

        px = x - self.preview_offset_x
        py = y - self.preview_offset_y
        if self.preview_draw_w <= 0 or self.preview_draw_h <= 0:
            return None

        px = min(max(px, 0), self.preview_draw_w - 1)
        py = min(max(py, 0), self.preview_draw_h - 1)

        rx, ry = self.get_real_coords(px, py)
        h, w = self.current_frame.shape[:2]
        rx = min(max(rx, 0), w - 1)
        ry = min(max(ry, 0), h - 1)
        return rx, ry

    def _on_mouse_press(self, x, y):
        mapped = self._map_label_to_real_coords(x, y)
        if mapped is None:
            return
        x, y = mapped
        self.drawing = True
        self.start_point = (x, y)
        self.end_point = (x, y)

    def _on_mouse_move(self, x, y):
        mapped = self._map_label_to_real_coords(x, y)
        if mapped is None:
            return
        x, y = mapped
        if self.drawing:
            self.end_point = (x, y)

    def _on_mouse_release(self, x, y):
        mapped = self._map_label_to_real_coords(x, y)
        if mapped is None:
            self.drawing = False
            return
        x, y = mapped
        self.drawing = False
        self.end_point = (x, y)
        if self.start_point and self.end_point:
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

        # 1. 起止点已是原图坐标，直接整理
        x1, x2 = min(self.start_point[0], self.end_point[0]), max(self.start_point[0], self.end_point[0])
        y1, y2 = min(self.start_point[1], self.end_point[1]), max(self.start_point[1], self.end_point[1])

        # 2. 边界安全检查
        h, w = self.current_frame.shape[:2]
        x1, x2 = max(0, x1), min(w, x2)
        y1, y2 = max(0, y1), min(h, y2)

        # 3. 无效区域检查
        if x2 <= x1 or y2 <= y1:
            self._set_status("区域无效，未保存")
            return

        # 4. 从原图裁剪
        template = self.current_frame[y1:y2, x1:x2].copy()

        self._save_template_image_and_coords(template, x1, y1, x2, y2)

    def run(self):
        """启动模板选择器"""
        if not self._ensure_qt_app():
            return
        picker = self

        class PreviewLabel(QLabel):
            def __init__(self):
                super().__init__()
                self.setMouseTracking(True)
                self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

            def mousePressEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    x, y = picker._get_qt_mouse_pos(event)
                    picker._on_mouse_press(x, y)
                event.accept()

            def mouseMoveEvent(self, event):
                x, y = picker._get_qt_mouse_pos(event)
                picker._on_mouse_move(x, y)
                event.accept()

            def mouseReleaseEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    x, y = picker._get_qt_mouse_pos(event)
                    picker._on_mouse_release(x, y)
                event.accept()

        window = QWidget()
        window.setWindowTitle("Template Picker")

        preview_window = PreviewLabel()
        preview_window.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_window.setMinimumSize(320, 180)

        status_label = QLabel("就绪")
        status_panel = QPlainTextEdit()
        status_panel.setReadOnly(True)
        status_panel.setMaximumHeight(120)
        self.status_label = status_label
        self.status_panel = status_panel

        btn_pause = QPushButton("冻结/解冻")
        btn_ocr = QPushButton("OCR 自动保存")

        def toggle_pause():
            self.paused = not self.paused
            self._set_status("已冻结画面" if self.paused else "已恢复实时画面")

        def trigger_ocr():
            self._save_template_by_target_text()

        btn_pause.clicked.connect(toggle_pause)
        btn_ocr.clicked.connect(trigger_ocr)

        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_pause)
        btn_row.addWidget(btn_ocr)

        layout = QVBoxLayout(window)
        layout.addLayout(btn_row)
        layout.addWidget(preview_window)
        layout.addWidget(status_label)
        layout.addWidget(status_panel)

        window.show()
        window.resize(900, 650)
        self._set_status("启动成功：鼠标拖拽即可保存选区")

        try:
            while window.isVisible():
                # 获取/更新帧
                if not self.paused:
                    frame = self.operator.get_frame()
                    if frame is not None:
                        self.current_frame = frame
                        self.preview = frame.copy()

                if self.preview is None:
                    if self.qt_app is not None:
                        self.qt_app.processEvents()
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
                    cv2.putText(
                        display_img,
                        f"Real: {cw}x{ch}",
                        (self.start_point[0], self.start_point[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )

                # 显示最近一次 OCR 命中框
                if self.last_ocr_quad is not None and len(self.last_ocr_quad) == 4:
                    pts = np.array(
                        [[int(p[0]), int(p[1])] for p in self.last_ocr_quad],
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

                rgb_img = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
                h, w = rgb_img.shape[:2]
                bytes_per_line = rgb_img.strides[0]
                q_image = QImage(
                    rgb_img.data,
                    w,
                    h,
                    bytes_per_line,
                    QImage.Format.Format_RGB888,
                ).copy()

                disp_w = max(1, preview_window.width())
                disp_h = max(1, preview_window.height())

                scale = min(disp_w / w, disp_h / h)
                draw_w = max(1, int(w * scale))
                draw_h = max(1, int(h * scale))

                self.preview_offset_x = (disp_w - draw_w) // 2
                self.preview_offset_y = (disp_h - draw_h) // 2
                self.preview_draw_w = draw_w
                self.preview_draw_h = draw_h
                self.scale_factor_x = w / draw_w
                self.scale_factor_y = h / draw_h

                scaled_image = q_image.scaled(
                    draw_w,
                    draw_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
                canvas = QPixmap(disp_w, disp_h)
                canvas.fill(Qt.GlobalColor.black)
                painter = QPainter(canvas)
                painter.drawImage(self.preview_offset_x, self.preview_offset_y, scaled_image)
                painter.end()
                preview_window.setPixmap(canvas)

                if self.qt_app is not None:
                    self.qt_app.processEvents()
                time.sleep(0.02)

        except KeyboardInterrupt:
            pass
        finally:
            self.operator.stop()
            window.close()


if __name__ == "__main__":
    picker = TemplatePicker()
    picker.run()
