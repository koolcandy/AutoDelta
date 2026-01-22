"""
主程序入口
"""
import time
from .core.device import DeviceController
from .core.controller import ScreenController
from .actions.deltabot import DeltaBot
from .utils.logger import logger


def main():
    """主函数"""
    logger.info("AutoDelta 机器人启动中...")
    
    # 初始化设备和控制器
    device = DeviceController(block_frame=True)
    device.start()

    controller = ScreenController(device)
    bot = DeltaBot(device, controller)

    try:
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