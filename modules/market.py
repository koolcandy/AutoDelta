from math import e
import time
from utils import config
import re
from typing import Tuple, Optional
from utils.logger import logger
from core.agent import Agent


class MarketHandler:
    def __init__(self, operator: Agent):
        self.operator = operator
        self.total_purchased = 0
        self.total_purchase_count = 0
        self.current_money = 0
        self.target_coord = None

    def get_shelves_slot_count(self) -> Optional[int]:
        clean_res = self.operator.read_text("shelves")
        if clean_res:
            pattern = re.compile(r"(\d+)\s*[\/|]\s*(\d+)")
            match = pattern.search(clean_res)
            if match:
                return int(match.group(1))
        return None

    def get_current_price(self) -> int:
        clean_res = self.operator.read_text("price")
        if clean_res:
            price = int(clean_res)
        else:
            price = 0
        logger.info(f"单价: {price}")
        return price

    def get_inventory_count(self) -> Optional[Tuple[int, int]]:
        clean_res = self.operator.read_text("count")
        if clean_res:
            pattern = re.compile(r"(\d+)\s*[\/|]\s*(\d+)")
            match = pattern.search(clean_res)
            if match:
                return (int(match.group(1)), int(match.group(2)))
        return None

    def get_current_money(self) -> int:
        self.operator.click(config.coin_ui)
        time.sleep(0.2)
        clean_res = self.operator.read_text("coin")
        if clean_res:
            final_money = int(clean_res)
        else:
            final_money = 0

        self.operator.click(config.random_point)
        return final_money

    def get_unit_price(self, count):
        logger.info(f"尝试购买 {count} 个...")

        if count == 31:
            buy_btn = config.buy_31
        elif count == 200:
            buy_btn = config.buy_200
        else:
            logger.error(f"不支持的购买数量: {count}")
            return 0

        if self.current_money == 0:
            self.current_money = self.get_current_money()

        for _ in range(3):
            self.operator.click(buy_btn)
            time.sleep(0.2)
            self.operator.click(config.buy_confirm)
            time.sleep(0.2)

            new_money = self.get_current_money()

            cost = self.current_money - new_money
            self.current_money = new_money
            actual_unit_price = cost / count

            if actual_unit_price != 0:
                self.total_purchased += count
                logger.info(
                    f"购买数量: {self.total_purchased} / {self.total_purchase_count}"
                )
                return actual_unit_price

        return 0

    def buy(
        self,
        item_name: str,
        target_price: int,
        max_acceptable_price: int,
        total_purchase_count: int,
    ):
        self.total_purchased = 0
        self.total_purchase_count = total_purchase_count

        logger.info(f"开始购买商品: {item_name}")
        logger.info(
            f"目标价格: {target_price}, 最大可接受价格: {max_acceptable_price}, 目标数量: {self.total_purchase_count}"
        )

        self.total_purchased += self.get_inventory(item_name)

        self.operator.wait_and_click_target("交易行")

        while self.total_purchased < self.total_purchase_count:
            self.operator.wait_for("交易行页面")
            if self.target_coord is None:
                if coord := self.operator.locate(
                    item_name, ocr=True, template_type="marketplace"
                ):
                    self.target_coord = coord
                    self.operator.click(self.target_coord)
            else:
                self.operator.click(self.target_coord)

            self.operator.wait_for("待售列表")
            preview_price = self.get_current_price()

            if preview_price > max_acceptable_price or preview_price == 0:
                logger.info(
                    f"预检价格 {preview_price} 高于可接受价格 {max_acceptable_price}，返回刷新"
                )
                self.operator.wait_and_click_target("返回")
                self.operator.wait_for("交易行页面")
                continue

            price_31 = self.get_unit_price(31)
            logger.info(f"单价: {price_31}")

            if price_31 <= target_price and price_31 > 0:
                logger.info("进入批量模式")
                while self.total_purchased < self.total_purchase_count:
                    price_200 = self.get_unit_price(200)
                    logger.info(f"批量购买单价: {price_200}")

                    if self.total_purchased >= self.total_purchase_count:
                        logger.info(
                            f"已达到目标数量: {self.total_purchased}/{self.total_purchase_count}"
                        )
                        break

                    if price_200 > target_price:
                        logger.info("价格上涨，跳回探测模式")
                        break
            else:
                logger.info(
                    f"探测价格 {price_31} 高于目标价格 {target_price}，继续探测"
                )

            self.operator.wait_and_click_target("返回")
            self.operator.wait_for("交易行页面")

        self.operator.wait_and_click_target("返回")

    def search_category(
        self, category_index: int, item_name: str
    ) -> Optional[Tuple[int, int]]:
        y = 1070 - 130 * category_index
        self.operator.click((2460, y))
        time.sleep(0.5)

        if coord := self.operator.locate(
            item_name, ocr=True, template_type="warehouse"
        ):
            return coord

        self.operator.swipe((1900, 800), (1900, 600))

        if coord := self.operator.locate(
            item_name, ocr=True, template_type="warehouse"
        ):
            return coord

        return None

    def search_warehouse(self, item_name: str) -> Optional[Tuple[int, int]]:
        self.operator.wait_and_click_target("整理")
        self.operator.wait_and_click_target("确认整理")

        self.operator.swipe((2460, 950), (2460, 650))
        time.sleep(0.5)

        for category_index in range(4):
            if coord := self.search_category(category_index, item_name):
                return coord

        logger.warning(f"在仓库中未找到物品: {item_name}")
        return None

    def get_inventory(self, item_name) -> int:
        self.operator.wait_and_click_target("交易行")
        total_val = 0
        self.operator.wait_and_click_target("出售")
        if coord := self.search_warehouse(item_name):
            self.operator.click(coord)
            self.operator.wait_for("上架2")

            if res := self.get_inventory_count():
                _, total_val = res
                logger.info(f"总数量: {total_val}")

                time.sleep(0.2)
                self.operator.wait_and_click_target("取消")
        time.sleep(0.2)
        self.operator.wait_and_click_target("返回")
        return total_val

    def sell_all(self, item_name: str = "9x19 rip"):
        """出售所有物品"""
        self.operator.wait_and_click_target("交易行")

        self.operator.wait_and_click_target("出售")
        time.sleep(0.2)

        if coord := self.search_warehouse(item_name):
            self.operator.click(coord)
            self.operator.wait_for("上架2")
            x1, x2, y = config.slider_end

            if res := self.get_inventory_count():
                current_val, total_val = res
                logger.info(f"物品数量: {current_val}/{total_val}")
                if total_val == 0:
                    return
                x = int(x1 + (x2 - x1) * min((3000 / total_val), 1))
                logger.debug(f"滑动到位置: ({x}, {y})")
                self.operator.click((x, y))

            time.sleep(0.2)

            if res := self.get_inventory_count():
                current_val, total_val = res

                if total_val > 3000:
                    click_count = abs(current_val - 3000)
                    if current_val > 3000:
                        for _ in range(click_count):
                            self.operator.click((config.slider_end[0] - 60, y))
                            time.sleep(0.01)
                    elif current_val < 3000:
                        for _ in range(click_count):
                            self.operator.click((config.slider_end[1] + 60, y))
                            time.sleep(0.01)

                time.sleep(0.2)

            self.operator.wait_and_click_target("上架2")

        self.operator.wait_and_click_target("返回")
