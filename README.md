# AutoDelta - 三角洲行动自动化脚本

这是一个用于《三角洲行动》游戏的自动化脚本，通过scrcpy实现对Android设备的控制。

## 重构说明

本项目经过重构，采用了更清晰的架构：

### 项目结构

```
/workspace/
├── run_bot.py              # 主程序入口
├── setup.py               # 项目配置
├── README.md              # 说明文档
├── src/                   # 源代码目录
│   ├── __init__.py
│   ├── actions/           # 游戏动作相关
│   │   ├── __init__.py
│   │   ├── base.py        # 基础动作类
│   │   └── deltabot.py    # DeltaBot主类
│   ├── config/            # 配置文件
│   │   ├── __init__.py
│   │   └── coords.py      # 坐标配置
│   ├── core/              # 核心功能
│   │   ├── __init__.py
│   │   ├── device.py      # 设备控制
│   │   └── controller.py  # 屏幕控制器
│   ├── utils/             # 工具函数
│   │   ├── __init__.py
│   │   ├── logger.py      # 日志系统
│   │   └── matcher.py     # 模板匹配器
│   └── main.py            # 程序入口
├── templates/             # 模板图片目录
└── scrcpy/               # scrcpy库文件
```

### 主要改进

1. **模块化设计**：将功能拆分为不同的模块，提高代码可维护性
2. **清晰的分层**：
   - `core`: 核心设备和控制器功能
   - `actions`: 游戏特定动作逻辑
   - `utils`: 通用工具函数
   - `config`: 配置参数
3. **继承结构**：`DeltaBot` 继承自 `BaseAction`，便于扩展
4. **错误处理**：增强错误处理和日志记录

### 依赖项

```bash
pip install adbutils opencv-python numpy av scrcpy
```

### 运行

```bash
# 确保设备已通过USB调试连接
python run_bot.py
```

### 注意事项

- 需要Android设备启用USB调试模式
- 需要安装adb工具
- 模板匹配依赖于`templates`目录下的图片文件