import cv2
import easyocr
import re
import time
import warnings
from typing import Tuple, Optional
from utils.logger import logger
from utils.device import Device
from modules.actions import ActionHandler

warnings.filterwarnings("ignore", category=UserWarning, module="torch")


class OcrUtils:
    def __init__(self, device: Device, actions: ActionHandler):
        self.device = device
        self.actions = actions
        self.coin_ui = (2230, 50)
        self.random_point = (2230, 400)
        self.count_roi = [1708, 564, 2025, 611]
        self.coin_roi = [2002, 133, 2295, 174]
        self.per_price_roi = [2029, 913, 2310, 984]
        self.shelves_slot_roi = [470, 112, 570, 154]
        self.reader = easyocr.Reader(["en"], gpu=True)

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

    def _do_ocr(self, roi: list, whitelist: str) -> str:
        frame = self.device.get_frame()
        if frame is None:
            return ""

        x1, y1, x2, y2 = roi
        crop = frame[y1:y2, x1:x2]
        processed_img = self._preprocess_image(crop)

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

    def get_inventory_count(self) -> Optional[Tuple[int, int]]:
        clean_res = self._do_ocr(self.count_roi, "0123456789/")
        if clean_res:
            pattern = re.compile(r"(\d+)\s*[\/|]\s*(\d+)")
            match = pattern.search(clean_res)
            if match:
                return (int(match.group(1)), int(match.group(2)))
        return None

    def get_current_money(self) -> int:
        self.device.click(self.coin_ui)
        time.sleep(0.2)
        clean_res = self._do_ocr(self.coin_roi, "0123456789")
        if clean_res:
            final_money = int(clean_res)
        else:
            final_money = 0

        self.device.click(self.random_point)
        return final_money

    def get_current_price(self) -> int:
        clean_res = self._do_ocr(self.per_price_roi, "0123456789")
        if clean_res:
            price = int(clean_res)
        else:
            price = 0
        logger.info(f"单价: {price}")
        return price

    def get_shelves_slot_count(self) -> Optional[int]:
        clean_res = self._do_ocr(self.shelves_slot_roi, "0123456789/")
        if clean_res:
            pattern = re.compile(r"(\d+)\s*[\/|]\s*(\d+)")
            match = pattern.search(clean_res)
            if match:
                return int(match.group(1))
        return None
