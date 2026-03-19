import numpy as np
from vision.match import Matcher
from vision.ocr import Ocr
from typing import Literal, Optional, Tuple, TypedDict


class OcrTarget(TypedDict):
    roi: list[int]
    whitelist: str

class TemplateCache(TypedDict, total=False):
    warehouse: np.ndarray
    marketplace: np.ndarray

class VisionEngine:
    """视觉引擎"""

    def __init__(self):
        self.matcher = Matcher()
        self.ocr = Ocr()
        self._ocr_targets: dict[str, OcrTarget] = {}
        self._template_cache: dict[str, TemplateCache] = {}

    def register_ocr_target(
        self,
        target_name: str,
        roi: list[int],
        whitelist: str = "",
    ) -> None:
        """注册 OCR 目标。"""
        self._ocr_targets[target_name] = {"roi": roi, "whitelist": whitelist}

    def locate(
        self,
        frame: np.ndarray,
        target: str,
        ocr: bool,
        template_type: Optional[Literal["warehouse", "marketplace"]] = None,
    ) -> Optional[Tuple[int, int]]:
        """输入 frame + target_name，输出坐标。"""
        if ocr and template_type is not None:
            target_cache = self._template_cache.setdefault(target, {})
            template = target_cache.get(template_type)
            if template is None:
                crop = self.ocr.find_text_and_crop(frame, target)
                if crop is None:
                    return None
                target_cache[template_type] = crop
                template = crop
            if coords := self.matcher.find_template_anywhere(frame, template):
                return coords

        else:
            if coords := self.matcher.find_template(frame, target):
                return coords

        return None

    def get_template_coords(self, target_name: str) -> Tuple[int, int]:
        """返回 coords.json 里的静态中心坐标。"""
        if target_name in self.matcher.coords:
            x1, y1, x2, y2 = self.matcher.coords[target_name]
            return (x1 + x2) // 2, (y1 + y2) // 2
        return (0, 0)

    def read_text(self, frame: np.ndarray, target_name: str, cropped: bool) -> str:
        """输入 frame + target_name，输出 OCR 文本。"""
        target = self._ocr_targets.get(target_name)
        if target is None:
            raise KeyError(f"未注册 OCR 目标: {target_name}")

        roi = target["roi"]
        whitelist = target["whitelist"]
        return self.ocr.do_ocr(frame=frame, roi=roi, whitelist=whitelist, cropped=cropped)
