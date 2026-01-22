import cv2
import numpy as np
import json
import time
from pathlib import Path
from typing import Optional, Dict
from .logger import logger


class TemplateMatcher:
    def __init__(self):
        logger.debug("正在初始化模板匹配引擎")
        self.template_dir = Path("templates")
        self.coords_file = self.template_dir / "coords.json"
        self.coords = {}
        self._load_coords()
        self.threshold = 0.8

    def _load_coords(self):
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
        return self.template_dir / f"{name}.png"

    def find_template(self, frame: np.ndarray, target: str) -> Optional[Dict]:
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
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
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
