from typing import Optional

import cv2
import numpy as np
from rapidocr import RapidOCR
from thefuzz import fuzz
from utils.logger import logger


class Ocr:
    def __init__(self):
        self.reader = RapidOCR()
        self.fuzzy_match_threshold = 80
        self.rec_only_reader = RapidOCR(
            params={
                "Global.use_det": False,
                "Global.use_cls": False,
                "Global.use_rec": True,
            }
        )

    def _fuzzy_score(self, text: str, target_text: str) -> int:
        """计算 OCR 结果与目标文本的近似匹配分数(0-100)。"""
        candidate = text.strip()
        target = target_text.strip()
        if not candidate or not target:
            return 0

        # 对 OCR 常见错字/漏字更稳健: 同时考虑完整匹配与部分匹配。
        return max(fuzz.partial_ratio(candidate, target), fuzz.ratio(candidate, target))

    def _run_ocr(
        self,
        image: np.ndarray,
        reader: Optional[RapidOCR] = None,
        **kwargs,
    ) -> list[tuple[np.ndarray, str, float]]:
        """标准化 RapidOCR 输出为 [(bbox, text, score), ...]"""
        ocr_reader = reader or self.reader
        result = ocr_reader(image, **kwargs)

        if result is None or (isinstance(result, (list, tuple)) and len(result) == 0):
            return []

        boxes = getattr(result, "boxes", None)
        txts = getattr(result, "txts", None)
        scores = getattr(result, "scores", None)

        if txts is None or scores is None:
            return []

        if boxes is None or len(boxes) == 0:
            h, w = image.shape[:2]
            boxes = [
                np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
            ] * len(txts)

        normalized = []
        for box, text, score in zip(boxes, txts, scores):
            if not text:
                continue
            try:
                confidence = float(score)
            except (TypeError, ValueError):
                confidence = 0.0

            normalized.append((np.array(box, dtype=np.float32), str(text), confidence))

        return normalized

    def _preprocess_image(self, crop_img: np.ndarray) -> np.ndarray:
        """缩放 x2, 阈值 120 (手动), 形态学操作=None"""
        gray = (
            cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
            if len(crop_img.shape) == 3
            else crop_img
        )
        resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, binary = cv2.threshold(resized, 120, 255, cv2.THRESH_BINARY)
        return binary

    def do_ocr(
        self,
        frame: np.ndarray,
        roi: list[int],
        whitelist: str = "",
        cropped: bool = False,
    ) -> str:
        """执行 OCR 识别"""
        if frame is None or roi is None or len(roi) != 4:
            logger.warning(f"帧为空或 OCR ROI 配置无效: {roi}")
            return ""

        x1, y1, x2, y2 = roi
        crop = frame[y1:y2, x1:x2]
        processed_img = self._preprocess_image(crop)

        try:
            reader = self.rec_only_reader if cropped else self.reader
            results = self._run_ocr(processed_img, reader=reader)

            clean_res = " ".join([text for _, text, _ in results]).strip()

            if whitelist:
                whitelist_set = set(whitelist)
                clean_res = "".join(c for c in clean_res if c in whitelist_set)

            logger.debug(f"RapidOCR 识别结果: {clean_res}")
            return clean_res

        except Exception as e:
            logger.error(f"OCR 识别出错: {e}")
            return ""

    def find_text_and_crop(
        self,
        frame: np.ndarray,
        target_text: str,
    ) -> Optional[np.ndarray]:
        """在整帧中查找目标文字，返回该文字对应区域的裁剪图。"""
        if frame is None or frame.size == 0 or not target_text.strip():
            logger.warning("OCR 目标文字为空或帧无效")
            return None

        target_text = target_text.strip()

        try:
            results = self._run_ocr(frame)
        except Exception as e:
            logger.error(f"OCR 定位出错: {e}")
            return None

        matches: list[tuple[np.ndarray, float]] = []
        for bbox, text, conf in results:
            if not text:
                continue

            candidate = text.strip()
            if target_text in candidate:
                # 精确子串命中优先，使用极高权重避免被近似结果抢占。
                rank_score = conf + 1000.0
                matches.append((bbox, rank_score))
                continue

            fuzzy_score = self._fuzzy_score(candidate, target_text)
            if fuzzy_score >= self.fuzzy_match_threshold:
                # 近似命中时兼顾 OCR 置信度，减少误匹配。
                rank_score = float(fuzzy_score) + conf
                matches.append((bbox, rank_score))

        if not matches:
            logger.debug(f"未识别到目标文字: {target_text}")
            return None

        best_match_bbox, _ = max(matches, key=lambda x: x[1])

        x, y, w, h = cv2.boundingRect(np.array(best_match_bbox, dtype=np.float32))

        x1 = max(x, 0)
        y1 = max(y, 0)
        x2 = min(x + w, frame.shape[1])
        y2 = min(y + h, frame.shape[0])

        if x2 <= x1 or y2 <= y1:
            logger.warning("OCR 识别到无效文本区域")
            return None

        return frame[y1:y2, x1:x2].copy()
