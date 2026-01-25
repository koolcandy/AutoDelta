# AutoDelta 游戏自动化机器人

自动化游戏操作的 Python 项目。

## 📁 项目结构

```
AutoDelta/
├── main.py              # 主程序入口
├── bot.py               # 游戏机器人逻辑（操作流程）
├── device.py            # 设备控制和模板匹配
├── config.py            # 配置文件
├── logger.py            # 日志模块
├── template_picker.py   # 模板选择工具（开发用）
├── scrcpy/              # scrcpy 库
└── templates/           # 游戏元素模板
    ├── coords.json      # 模板坐标配置
    └── *.png            # 模板图片
```

## 🚀 使用说明

### 运行机器人

```bash
python main.py
```

### 创建新模板

```bash
python template_picker.py
```

- 按 `F` 键冻结/解冻画面
- 鼠标拖拽框选区域
- 输入模板名称保存
- 按 `Q` 键退出

## ⚙️ 配置

在 [config.py](config.py) 中修改：

- `RUN_ROUNDS`: 运行轮次
- `PACKAGE_NAME`: 应用包名
- `QRFA_COORD`, `CANCEL_COORD`: 游戏坐标
- 其他超时和阈值设置

## 📝 核心类

### `Bot` (bot.py)
- 封装游戏操作逻辑
- 方法：`click_template()`, `long_press()`, `run()`

### `Device` (device.py)
- 设备控制和屏幕捕获
- 模板匹配和触摸控制
- 方法：`click()`, `multitouch()`, `restart_app()`

### `TemplateMatcher` (device.py)
- 屏幕元素识别
- 基于 OpenCV 的模板匹配

## 🔧 依赖

- scrcpy-py
- opencv-python
- numpy
