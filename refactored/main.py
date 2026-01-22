"""
重构后的主程序
"""
import time
from refactored.core.device_manager import DeviceManager
from refactored.core.bot_controller import BotController
from refactored.utils.logger import logger


def main():
    """主函数"""
    logger.info("AutoDelta 机器人启动中...")
    
    # 初始化设备
    device = DeviceManager(block_frame=True)
    device.start()

    # 初始化机器人控制器
    bot = BotController(device)

    try:
        # 执行任务
        bot.run_mission()
    except KeyboardInterrupt:
        logger.info("用户手动停止")
    except Exception as e:
        logger.error(f"发生异常: {e}")
    finally:
        logger.info("正在清理资源...")
        device.stop()


if __name__ == "__main__":
    main()