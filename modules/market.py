import time
import cv2
import re
import ddddocr
from logger import logger


class MarketHandler:
    # 交易行相关坐标定义
    BUY_31 = (2036, 810)
    BUY_200 = (2350, 810)
    COIN = (2230, 50)
    BUY_CONFIRM = (2196, 950)
    RANDOM_CLICK = (2230, 400)
    ROI = [2002, 133, 2295, 174]

    def __init__(self, device):
        self.device = device
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.current_wallet_balance = 0
        self.total_purchased = 0

    def get_current_money(self) -> int:
        self.device.click(self.COIN)
        time.sleep(0.3)
        frame = self.device.get_frame()

        clean_res = "0"
        if frame is not None:
            x1, y1, x2, y2 = self.ROI
            crop = frame[y1:y2, x1:x2]
            if len(crop.shape) == 3:
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            else:
                gray = crop
            _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
            height, width = binary.shape
            scale_factor = 3
            processed_img = cv2.resize(
                binary,
                (width * scale_factor, height * scale_factor),
                interpolation=cv2.INTER_LINEAR,
            )
            success, encoded_image = cv2.imencode(".png", processed_img)
            if success:
                img_bytes = encoded_image.tobytes()
                res = self.ocr.classification(img_bytes)
                clean_res = re.sub(r"[^\d]", "", str(res))

        final_money = int(clean_res) if clean_res else 0
        self.device.click(self.RANDOM_CLICK)
        return final_money

    def init_wallet(self):
        """读取初始金币"""
        logger.info("初始化：读取初始金币...")
        self.current_wallet_balance = self.get_current_money()

    def get_unit_price(self, count, buy_btn_type):
        logger.info(f"尝试购买 {count} 个...")
        old_money = self.current_wallet_balance

        self.device.click(buy_btn_type)
        time.sleep(0.2)
        self.device.click(self.BUY_CONFIRM)
        time.sleep(0.5)

        new_money = self.get_current_money()
        self.current_wallet_balance = new_money
        self.total_purchased += count

        cost = old_money - new_money
        actual_unit_price = cost / count if count > 0 else 0
        return actual_unit_price

    def buy_items(self, target_price=450, total_purchase_count=float("inf")):
        """交易行购买逻辑"""
        self.total_purchased = 0
        self.current_wallet_balance = 0

        time.sleep(2)
        while self.total_purchased < total_purchase_count:
            self.init_wallet()
            price_31 = self.get_unit_price(31, self.BUY_31)
            logger.info(f"探测单价: {price_31}")

            if price_31 <= target_price:
                logger.info("价格合适，进入批量模式")
                while self.total_purchased < total_purchase_count:
                    price_200 = self.get_unit_price(200, self.BUY_200)
                    logger.info(f"批量购买单价: {price_200}")
                    logger.info(
                        f"已购买数量: {self.total_purchased}/{int(total_purchase_count)}"
                    )

                    if price_200 > target_price:
                        logger.info("价格上涨，跳回探测模式")
                        break
            else:
                logger.info("价格太贵，等待中...")
                time.sleep(0.2)

        logger.info(f"购买完成！总购买数量: {self.total_purchased}")
