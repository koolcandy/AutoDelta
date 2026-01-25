"""
AutoDelta 游戏机器人主程序
"""

from device import Device
from bot import Bot
from logger import logger
from config import RUN_ROUNDS


def main():
    """主函数"""
    logger.info("AutoDelta 机器人启动中...")

    # 初始化设备和机器人
    device = Device(block_frame=True)
    device.start()

    bot = Bot(device)

    try:
        for round_num in range(1, RUN_ROUNDS + 1):
            logger.info(f"开始第 {round_num}/{RUN_ROUNDS} 轮")
            bot.run()
    except KeyboardInterrupt:
        logger.info("用户手动停止")
    except Exception as e:
        logger.error(f"发生异常: {e}")
    finally:
        logger.info("正在清理资源...")
        device.stop()


if __name__ == "__main__":
    main()
