import time
import json
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict
from utils.logger import logger


class Matcher:
    """模板匹配器，用于在屏幕上查找特定图像"""

    def __init__(self):
        logger.debug("正在初始化模板匹配引擎")
        self.template_dir = Path("templates")
        self.coords_file = self.template_dir / "coords.json"
        self.coords = {}
        self._load_coords()

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
        threshold = 0.8
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

            if max_val >= threshold:
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
                logger.debug(f"'{target}' 未找到 (匹配度 {max_val:.2f} < {threshold})")
                return None

        except Exception as e:
            logger.error(f"匹配模板 '{target}' 时出错: {e}")
            return None

    def find_template_anywhere(self, frame: np.ndarray, target: str) -> Optional[Dict]:
        """
        在整个帧中查找指定模板，不需要预定义坐标

        Args:
            frame: 屏幕帧图像
            target: 目标模板名称

        Returns:
            匹配结果字典，包含 text、center、score 等信息，未找到返回 None
        """
        threshold = 0.95
        template_path = self._get_template_path(target)
        if not template_path.exists():
            logger.error(f"未找到模板图片: {template_path}")
            return None

        template = cv2.imread(str(template_path))
        if template is None:
            logger.error(f"加载模板图片失败: {template_path}")
            return None

        try:
            frame_h, frame_w = frame.shape[:2]
            template_h, template_w = template.shape[:2]
            logger.debug(
                f"开始匹配 '{target}': 帧大小=({frame_w}x{frame_h}), 模板大小=({template_w}x{template_h})"
            )

            start_time = time.time()
            res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            duration = (time.time() - start_time) * 1000

            logger.debug(
                f"匹配结果: 最大匹配度={max_val:.4f}, 阈值={threshold}, 位置={max_loc}"
            )

            if max_val >= threshold:
                th, tw = template.shape[:2]
                center_x = max_loc[0] + tw // 2
                center_y = max_loc[1] + th // 2

                logger.debug(
                    f"在全屏找到 '{target}' 匹配度={max_val:.2f} 坐标=({center_x}, {center_y}), 耗时={duration:.2f}ms"
                )

                return {
                    "text": target,
                    "center": (center_x, center_y),
                    "score": float(max_val),
                    "box": None,
                }
            else:
                logger.debug(
                    f"'{target}' 在全屏未找到 (匹配度 {max_val:.4f} < {threshold}), 耗时={duration:.2f}ms"
                )
                return None

        except Exception as e:
            logger.error(f"在全屏匹配模板 '{target}' 时出错: {e}")
            return None
