import time
import json
import cv2
import numpy as np
from pathlib import Path
from typing import Optional
from utils.logger import logger


class Matcher:
    """模板匹配器，用于在屏幕上查找特定图像"""

    def __init__(self):
        logger.debug("正在初始化模板匹配引擎")
        self.template_dir = Path("templates")
        self.coords_file = self.template_dir / "coords.json"
        self.coords = {}
        self.template_cache = {}
        self._load_coords()
        self._preload_templates()

    def _preload_templates(self):
        """预加载所有模板"""
        if not self.template_dir.exists():
            return

        for ext in ["*.png"]:
            for path in self.template_dir.glob(ext):
                name = path.stem
                try:
                    img = cv2.imread(str(path))
                    if img is not None:
                        self.template_cache[name] = img
                except Exception as e:
                    logger.error(f"预加载模板 '{name}' 失败: {e}")
        logger.info(f"成功预加载 {len(self.template_cache)} 个模板到内存")

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

    def _get_template(self, name: str) -> np.ndarray:
        """加载模板图片"""
        if name in self.template_cache:
            return self.template_cache[name]
        raise FileNotFoundError(f"模板图片不存在: {name}")

    def find_template(
        self, frame: np.ndarray, target: str, template: Optional[np.ndarray] = None
    ) -> Optional[tuple[int, int]]:
        """
        在帧中查找指定模板

        Args:
            frame: 屏幕帧图像
            target: 目标模板名称
            template: 可选的模板图像

        Returns:
            匹配结果元组 (center_x, center_y)，未找到返回 None
        """
        threshold = 0.1
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

        template = self._get_template(target)

        try:
            start_time = time.time()
            res = cv2.matchTemplate(crop, template, cv2.TM_SQDIFF_NORMED)
            min_val, _, min_loc, _ = cv2.minMaxLoc(res)
            duration = (time.time() - start_time) * 1000

            if min_val <= threshold:
                th, tw = template.shape[:2]
                center_x_crop = min_loc[0] + tw // 2
                center_y_crop = min_loc[1] + th // 2

                center_x = x1 + center_x_crop
                center_y = y1 + center_y_crop

                logger.debug(
                    f"找到 '{target}' 匹配度={min_val:.2f} 坐标=({center_x}, {center_y}), 耗时={duration:.2f}ms"
                )

                return (center_x, center_y)
            else:
                logger.debug(f"'{target}' 未找到 (匹配度 {min_val:.2f} > {threshold})")
                return None

        except Exception as e:
            logger.error(f"匹配模板 '{target}' 时出错: {e}")
            return None

    def find_template_anywhere(
        self, frame: np.ndarray, target: str | np.ndarray
    ) -> Optional[tuple[int, int]]:
        threshold = 0.02
        if isinstance(target, str):
            traget_template = self._get_template(target)
        elif isinstance(target, np.ndarray):
            traget_template = target
        else:
            logger.error(f"无效的目标类型: {type(target)}")
            return None

        try:
            frame_h, frame_w = frame.shape[:2]
            template_h, template_w = traget_template.shape[:2]
            logger.debug(
                f"开始匹配 '{target}': 帧大小=({frame_w}x{frame_h}), 模板大小=({template_w}x{template_h})"
            )

            start_time = time.time()
            res = cv2.matchTemplate(frame, traget_template, cv2.TM_SQDIFF_NORMED)
            min_val, _, min_loc, _ = cv2.minMaxLoc(res)
            duration = (time.time() - start_time) * 1000

            logger.debug(
                f"匹配结果: 最小匹配度={min_val:.4f}, 阈值={threshold}, 位置={min_loc}"
            )

            if min_val <= threshold:
                th, tw = traget_template.shape[:2]
                center_x = min_loc[0] + tw // 2
                center_y = min_loc[1] + th // 2

                logger.debug(
                    f"在全屏找到 '{target}' 匹配度={min_val:.2f} 坐标=({center_x}, {center_y}), 耗时={duration:.2f}ms"
                )

                return (center_x, center_y)
            else:
                logger.debug(
                    f"'{target}' 在全屏未找到 (匹配度 {min_val:.4f} > {threshold}), 耗时={duration:.2f}ms"
                )
                return None

        except Exception as e:
            logger.error(f"在全屏匹配模板 '{target}' 时出错: {e}")
            return None
