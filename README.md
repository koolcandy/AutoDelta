
# AutoDelta

基于 `scrcpy` + 模板匹配的手游自动化脚本。通过抓取游戏画面帧、模板匹配定位按钮，再结合坐标点击、长按等操作实现流程自动化；交易行部分通过 OCR 识别金币变化来判断价格。

> 使用前请先去游戏里截取对应的模版（详见“模板采集”）。

## 实现逻辑概览

- **画面获取与控制**：
	- `utils/device.py` 封装 `scrcpy.Client` 获取帧与触控控制。
	- 通过 ADB 执行应用重启、Wi‑Fi 开关等系统级操作。
- **模板匹配**：
	- `utils/device.py` 中的 `Matcher` 读取 `templates/coords.json`，在指定 ROI 内进行模板匹配。
- **动作封装**：
	- `modules/actions.py` 提供 `click_template()`、`long_press()`、`click_step()` 等通用流程方法，自动处理弹窗与重试。
- **交易行逻辑**：
	- `modules/market.py` 基于 OCR 识别金币变化，计算单价并进行批量购买。
- **主流程**：
	- `bot.py` 组织完整游戏流程（进图、配装、重连、领取等）。

## 依赖与环境

### Python 依赖

建议使用 Python 3.10+。

必需依赖（来自代码引用）：
- `opencv-python`
- `numpy`
- `ddddocr`
- `adbutils`
- `av`（PyAV）

### 外部环境

- 已安装并可用的 **ADB**（`adb` 命令可执行）
- Android 设备开启 **USB 调试**
- 设备已安装并登录游戏

## 安装

1. 安装 Python 依赖：

	 ```bash
	 pip install opencv-python numpy ddddocr adbutils av
	 ```

2. 确认 ADB 可用：

	 ```bash
	 adb devices
	 ```

## 模板采集（必须）

运行模板选择器，**在游戏界面中截取按钮/文字区域**：

```bash
python utils/template_picker.py
```

操作提示：

- 按 **F** 冻结/解冻画面（建议先冻结再框选）
- 鼠标拖拽框选区域，松开后输入模板名称并保存
- 按 **Q** 退出

模板将保存到：

- 图片：`templates/<模板名>.png`
- 坐标：`templates/coords.json`

> 需要保证模板名与脚本中使用的名称一致（如 `交易行`、`开始行动`、`确认配装` 等）。

## 使用方法

1. 连接设备并进入游戏主界面。
2. 启动脚本：

	 ```bash
	 python bot.py
	 ```

3. 脚本默认执行 `run_rounds=5` 轮，可在 [bot.py](bot.py) 中调整。

## 常见问题

- **找不到模板**：
	- 确认已在当前分辨率/缩放下重新截取模板。
	- 确保 `templates/coords.json` 中存在对应条目。

- **ADB 无法控制设备**：
	- 检查 USB 调试授权是否允许。
	- 重新连接数据线或重启 ADB（`adb kill-server && adb start-server`）。

## 免责声明

本项目仅用于学习与技术研究，请遵守游戏与平台规则。使用者自行承担风险。

