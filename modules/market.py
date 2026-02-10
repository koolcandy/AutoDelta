import time
from typing import Tuple, Optional
from utils.logger import logger
from utils.device import Device
from utils.ocr import OcrUtils
from modules.actions import ActionHandler, GameRebootException


class MarketHandler:
    def __init__(self, device: Device, actions: ActionHandler, ocr_utils: OcrUtils):
        self.device = device
        self.actions = actions
        self.ocr_utils = ocr_utils
        self.current_wallet_balance = 0
        self.total_purchased = 0
        self.buy_31 = (2036, 810)
        self.buy_200 = (2350, 810)
        self.buy_confirm = (2196, 950)
        self.slider_end = [1685, 2150, 650]  # x1, x2, y
        self.consecutive_failures = 0

    def open_market(self):
        """打开交易行界面"""
        self.actions.click_template("交易行")
        time.sleep(0.5)

    def init_wallet(self):
        """读取初始金币"""
        logger.info("初始化：读取初始金币...")
        self.current_wallet_balance = self.ocr_utils.get_current_money()

    def get_unit_price(self, count, buy_btn_type):
        logger.info(f"尝试购买 {count} 个...")
        old_money = self.current_wallet_balance

        self.device.click(buy_btn_type)
        time.sleep(0.2)
        self.device.click(self.buy_confirm)
        time.sleep(0.5)

        new_money = self.ocr_utils.get_current_money()
        self.current_wallet_balance = new_money

        cost = old_money - new_money
        actual_unit_price = cost / count if count > 0 else 0
        if actual_unit_price != 0:
            self.total_purchased += count
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            if self.consecutive_failures >= 5:
                raise GameRebootException(self.device)
        return actual_unit_price

    def buy_items(
        self,
        item_name: str,
        target_price: int,
        max_acceptable_price: int,
        total_purchase_count: int,
    ):
        """交易行购买逻辑

        Args:
            item_name: 商品名称（例如 "12 buy"）
            target_price: 目标价格，低于此价格时购买200发
            max_acceptable_price: 最大可接受价格，高于此价格时刷新
            total_purchase_count: 总购买数量
        """
        self.total_purchased = 0
        self.current_wallet_balance = 0

        logger.info(f"开始购买商品: {item_name}")
        logger.info(
            f"目标价格: {target_price}, 最大可接受价格: {max_acceptable_price}, 目标数量: {total_purchase_count}"
        )

        self.total_purchased += self.get_inventory(item_name="12 Gauge")

        self.open_market()

        while self.total_purchased < total_purchase_count:
            # 点击进入商品详情页
            self.actions.click_template(item_name)
            time.sleep(0.5)

            # 预检价格
            preview_price = self.ocr_utils.get_current_price()
            if preview_price == 0:
                logger.info("预检价格识别失败，返回刷新")
                self.actions.click_template("返回")
                time.sleep(0.3)
                continue

            # 如果价格太高，返回刷新
            if preview_price > max_acceptable_price:
                logger.info(
                    f"预检价格 {preview_price} 高于最大可接受价格 {max_acceptable_price}，返回刷新"
                )
                self.actions.click_template("返回")
                time.sleep(0.3)
                continue

            # 价格可接受，初始化钱包
            if self.current_wallet_balance == 0:
                self.init_wallet()

            # 探测模式：买31发获取真实单价
            price_31 = self.get_unit_price(31, self.buy_31)
            logger.info(f"探测单价: {price_31}")

            # 如果真实价格低于目标价格，进入批量模式
            if price_31 <= target_price:
                logger.info("价格合适，进入批量模式")
                while self.total_purchased < total_purchase_count:
                    # 先买一次200个，然后判断是否已经达到或超过目标
                    price_200 = self.get_unit_price(200, self.buy_200)
                    logger.info(f"批量购买单价: {price_200}")
                    logger.info(
                        f"已购买数量: {self.total_purchased}/{total_purchase_count}"
                    )

                    # 检查是否已经达到或超过目标
                    if self.total_purchased >= total_purchase_count:
                        logger.info(
                            f"已达到目标数量: {self.total_purchased}/{total_purchase_count}"
                        )
                        break

                    if price_200 > target_price:
                        logger.info("价格上涨，跳回探测模式")
                        break
            else:
                logger.info(
                    f"探测价格 {price_31} 高于目标价格 {target_price}，继续探测"
                )

            # 返回到商品列表
            self.actions.click_template("返回")
            time.sleep(0.3)

        self.actions.click_template("返回")

    def search_in_category(
        self, category_index: int, item_name: str
    ) -> Optional[Tuple[int, int]]:
        y = 680 + 130 * category_index
        self.device.click((2460, y))
        time.sleep(0.5)

        if coord := self.device.search_template(item_name):
            return coord

        self.device.swipe(
            (1900, 950), (1900, 650), move_step_length=10, move_steps_delay=0.01
        )

        time.sleep(0.5)
        if coord := self.device.search_template(item_name):
            return coord

        return None

    def search_warehouse(self, item_name: str) -> Optional[Tuple[int, int]]:
        # 整理仓库
        self.actions.click_template("整理")
        time.sleep(0.5)
        self.actions.click_template("确认整理")
        time.sleep(0.5)

        # 向上滑动
        self.device.swipe(
            (2460, 950), (2460, 650), move_step_length=10, move_steps_delay=0.01
        )
        time.sleep(0.5)

        # 遍历所有列表
        for category_index in range(4):
            if coord := self.search_in_category(category_index, item_name):
                return coord

        logger.warning(f"在仓库中未找到物品: {item_name}")
        return None

    def sell_all(self, item_name: str = "12 Gauge"):
        """出售所有物品"""
        self.actions.click_template("出售")

        time.sleep(0.5)

        if coord := self.search_warehouse(item_name):
            self.device.click(coord)
            time.sleep(1)
            if res := self.ocr_utils.get_inventory_count():
                current_val, total_val = res
                logger.info(f"物品数量: {current_val}/{total_val}")
                x1, x2, y = self.slider_end
                x = int(x1 + (x2 - x1) * min((3000 / total_val), 1))
                logger.debug(f"滑动到位置: ({x}, {y})")
                self.device.click((x, y))

            time.sleep(0.5)

            # 精细调整数量到3000
            while True:
                if res := self.ocr_utils.get_inventory_count():
                    current_val, total_val = res

                    if total_val > 3000:
                        click_count = abs(current_val - 3000)
                        if current_val > 3000:
                            for _ in range(click_count):
                                self.device.click((self.slider_end[0] - 60, y))
                                time.sleep(0.01)
                        elif current_val < 3000:
                            for _ in range(click_count):
                                self.device.click((self.slider_end[1] + 60, y))
                                time.sleep(0.01)
                        else:
                            logger.info("数量调整完成")
                            break
                    else:
                        break
                else:
                    logger.warning("数量识别失败，重试中...")
                    time.sleep(1)

                time.sleep(0.5)

            self.actions.click_template("上架2")

        self.actions.click_template("返回")

    def get_inventory(self, item_name: str = "12 Gauge") -> int:
        total_val = 0
        self.open_market()

        self.actions.click_template("出售")

        time.sleep(1)

        if coord := self.search_warehouse(item_name):
            self.device.click(coord)
            time.sleep(1)

            if res := self.ocr_utils.get_inventory_count():
                _, total_val = res
                logger.info(f"总数量: {total_val}")

                time.sleep(0.5)
                self.actions.click_template("取消")
        time.sleep(0.5)
        self.actions.click_template("返回")
        return total_val
