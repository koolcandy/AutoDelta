import time
import subprocess
from dataclasses import dataclass
from utils.logger import logger
from core.agent import Agent
from modules.expection import GameRebootException
from modules.recovery import GameRecoveryHandler
from modules.market import MarketHandler
from modules.mail import MailHandler
from modules.glitch import GlitchHandler
from modules.map import MapHandler
from modules.lobby import LobbyHandler
from modules.state import GameState
from modules.prepare import PrepareHandler
from modules.reconnect import ReconnectHandler


@dataclass
class _BotServices:
    operator: Agent
    market: MarketHandler
    mail: MailHandler
    glitch: GlitchHandler
    map: MapHandler
    lobby: LobbyHandler
    prepare: PrepareHandler
    reconnect: ReconnectHandler

def _build_services() -> _BotServices:
    operator = Agent()

    return _BotServices(
        operator=operator,
        market=MarketHandler(operator),
        mail=MailHandler(operator),
        glitch=GlitchHandler(operator),
        map=MapHandler(operator),
        lobby=LobbyHandler(operator),
        prepare=PrepareHandler(operator),
        reconnect=ReconnectHandler(operator),
    )


class Bot:
    """游戏自动化机器人，封装所有游戏操作逻辑"""

    def __init__(self):
        """
        初始化机器人
        """
        self.services = _build_services()
        self.operator = self.services.operator
        self.market = self.services.market
        self.mail = self.services.mail
        self.glitch = self.services.glitch
        self.map = self.services.map
        self.lobby = self.services.lobby
        self.prepare = self.services.prepare
        self.reconnect = self.services.reconnect

    def detect_state(self) -> GameState:
        """根据屏幕特征判断当前处于哪个阶段"""
        self.operator.popup_handler()

        frame = self.operator.get_frame()
        if frame is None:
            return GameState.UNKNOWN

        if self.operator.locate("重连入局", frame=frame):
            logger.info("检测到重连提示")
            return GameState.RECONNECT

        if self.operator.locate("战略板", frame=frame):
            logger.info("检测到选图界面")
            return GameState.MAP_SELECT

        if self.operator.locate("装备配置", frame=frame):
            logger.info("检测到配装界面")
            return GameState.PREPARE
        
        if self.operator.locate("推荐配装", frame=frame):
            logger.info("检测到准备界面 ")
            return GameState.GLITCH
            
        if self.operator.locate("行前备战", frame=frame):
            return GameState.LOBBY
        
        if self.operator.locate("出发", frame=frame):
            return GameState.LOBBY_GO

        return GameState.UNKNOWN

    def run(
        self,
        target,
        item_name,
        target_price,
        max_acceptable_price,
        total_purchase_count,
    ):
        self.market.buy(
            item_name,
            target_price,
            max_acceptable_price,
            total_purchase_count,
        )

        self.round_finished = False
        self.glitch_state = False
        self.handle_mail = False
        unknown_timer = 0

        # 2. 启动状态机引擎
        while not self.round_finished:
            current_state = self.detect_state()

            if current_state != GameState.UNKNOWN:
                unknown_timer = 0

            if current_state == GameState.LOBBY:
                if self.handle_mail:
                    self.round_finished = self.mail.handle_mail()
                    self.handle_mail = False
                else:
                    self.lobby.handle_lobby_prepare()

            elif current_state == GameState.MAP_SELECT:
                self.map.handle_map()

            elif current_state == GameState.LOBBY_GO:
                self.lobby.handle_lobby_go()
                self.glitch_state = True

            elif current_state == GameState.GLITCH:
                self.glitch.handle_glitch(target)
                self.glitch_state = False
                self.handle_mail = True
            
            elif current_state == GameState.RECONNECT:
                self.reconnect.handle_reconnect()

            elif current_state == GameState.PREPARE:
                self.prepare.handle_prepare(self.glitch_state)

            elif current_state == GameState.UNKNOWN:
                unknown_timer += 1
                if unknown_timer > 100:
                    raise GameRebootException("状态机彻底迷失，触发全局恢复")

            time.sleep(1)

    def test(self):
        """测试函数"""
        logger.info("正在测试状态检测...")
        self.operator.popup_handler()

    def sell(self):
        for _ in range(15):
            self.mail.recept_mail()
            self.market.sell_all()
            time.sleep(5)


def main():
    """主函数"""
    logger.info("AutoDelta 启动中...")

    caffeinate_process = subprocess.Popen(["caffeinate", "-i"])

    bot = Bot()

    bot.operator.start()

    run_rounds = 125

    try:
        for round_num in range(1, run_rounds + 1):
            logger.info(f"开始第 {round_num}/{run_rounds} 轮")
            try:
                bot.run(
                    target="sheme4",
                    item_name="T46M",
                    target_price=402,
                    max_acceptable_price=402,
                    total_purchase_count=5000,
                )
            except GameRebootException as e:
                logger.info(f"捕获异常，执行恢复: {e}")
                recovery = GameRecoveryHandler(bot.operator)
                recovery.recover_from_failure()
                continue
        # bot.sell()
    except KeyboardInterrupt:
        logger.info("用户手动停止")
    finally:
        logger.info("正在清理资源...")
        caffeinate_process.terminate()
        caffeinate_process.wait()
        bot.operator.stop()


if __name__ == "__main__":
    main()
