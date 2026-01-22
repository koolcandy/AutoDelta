import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime


class Logger:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, name="AutoDelta", log_dir="logs", level=logging.INFO):
        if self._initialized:
            return

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False  # Prevent double logging if attached to root

        # 格式化器
        # detailed_fmt = logging.Formatter(
        #     '[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s',
        #     datefmt='%Y-%m-%d %H:%M:%S'
        # )
        detailed_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
        )

        # 如果日志目录不存在则创建
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 文件处理器 (轮转)
        current_time = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_dir, f"autodelta_{current_time}.log")
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(detailed_fmt)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(detailed_fmt)

        # 添加处理器
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

        self._initialized = True

    def get_logger(self):
        return self.logger

    # 便捷方法，允许像 Logger().info(...) 这样使用
    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)


# 为了方便导入的全局实例
logger = Logger().get_logger()
