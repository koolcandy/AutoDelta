"""
日志模块
"""

import logging

log_level = logging.INFO

# 创建logger实例
logger = logging.getLogger("AutoDelta")
logger.setLevel(log_level)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
# 创建格式化器
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

# 添加处理器到logger
if not logger.handlers:
    logger.addHandler(console_handler)
