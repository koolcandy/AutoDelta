from typing import Optional

import cv2
import easyocr
import warnings
import numpy as np
from utils.logger import logger

warnings.filterwarnings("ignore", category=UserWarning, module="torch")


class Ocr:
    def __init__(self):
        self.reader = easyocr.Reader(["en", "ch_sim"])

    def _preprocess_image(self, crop_img):
        """
        Scale=2, Threshold=120 (Manual), Morph=None
        """
        if len(crop_img.shape) == 3:
            gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop_img

        height, width = gray.shape
        scale_factor = 2
        resized = cv2.resize(
            gray,
            (width * scale_factor, height * scale_factor),
            interpolation=cv2.INTER_CUBIC,
        )

        _, binary = cv2.threshold(resized, 120, 255, cv2.THRESH_BINARY)

        return binary

    def do_ocr(
        self,
        frame: np.ndarray,
        roi: list[int],
        whitelist: str,
    ) -> str:
        """执行 OCR 识别"""
        if frame is None:
            return ""

        if roi is None or len(roi) != 4:
            logger.warning(f"OCR ROI 配置无效: {roi}")
            return ""

        x1, y1, x2, y2 = roi
        crop = frame[y1:y2, x1:x2]
        # cv2.imwrite("debug_ocr_crop.png", crop)
        processed_img = self._preprocess_image(crop)
        # cv2.imwrite("debug_ocr_processed.png", processed_img)

        try:
            results = self.reader.readtext(processed_img)
            clean_res = " ".join([text for _, text, _ in results]).strip()

            if whitelist:
                clean_res = "".join(c for c in clean_res if c in whitelist)

            logger.debug(f"EasyOCR识别结果: {clean_res}")
            return clean_res
        except Exception as e:
            logger.error(f"OCR识别出错: {e}")
            return ""

    def find_text_and_crop(
        self,
        frame: np.ndarray,
        target_text: str,
    ) -> Optional[np.ndarray]:
        """在整帧中查找目标文字，返回该文字对应区域的裁剪图。"""
        if frame is None or frame.size == 0:
            return None

        if not target_text or not target_text.strip():
            logger.warning("OCR目标文字为空")
            return None

        def _norm(text: str) -> str:
            text = text.strip()
            return text

        normalized_target = _norm(target_text)

        try:
            results = self.reader.readtext(frame)
        except Exception as e:
            logger.error(f"OCR定位出错: {e}")
            return None

        best_match = None
        best_confidence = -1.0

        for bbox, text, confidence in results:
            normalized_text = _norm(text)
            if not normalized_text:
                continue

            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                confidence_value = 0.0

            is_match = normalized_target in normalized_text
            if not is_match:
                continue

            if confidence_value > best_confidence:
                best_confidence = confidence_value
                best_match = bbox

        if best_match is None:
            logger.debug(f"未识别到目标文字: {target_text}")
            return None

        points = np.array(best_match, dtype=np.float32)
        x_coords = points[:, 0]
        y_coords = points[:, 1]

        x1 = max(int(np.floor(np.min(x_coords))), 0)
        y1 = max(int(np.floor(np.min(y_coords))), 0)
        x2 = min(int(np.ceil(np.max(x_coords))), frame.shape[1])
        y2 = min(int(np.ceil(np.max(y_coords))), frame.shape[0])

        if x2 <= x1 or y2 <= y1:
            logger.warning("OCR识别到无效文本区域")
            return None

        return frame[y1:y2, x1:x2].copy()
