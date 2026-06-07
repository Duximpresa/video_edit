# 更新日志

本项目采用 [语义化版本](https://semver.org/lang/zh-CN/) 记录正式版本。

## [1.0.0] - 2026-06-07

首个正式稳定版本。

### 新增

- 支持从多个素材目录随机选择视频、配音和 BGM，批量生成差异化成片。
- 支持从每个音频目录的 `subtitles.json` 读取与随机配音对应的字幕。
- 支持配置字幕字体、字号、字间距、颜色、透明度、描边、位置和最大行宽。
- 支持按中文或英文逗号拆分字幕，并使用字符比例或语音时间戳控制分段时间。
- 支持缓存字幕拆分比例，并兼容旧版字符串字幕映射。
- 提供递归字幕映射生成入口，可直接在 IDE 中运行。
- 支持 Paraformer 中文本地 GPU 识别、标点恢复和字符级时间戳。
- 支持 faster-whisper `small`、`base` INT8 GPU 回退。
- 本地模型可自动下载到项目内的 `models/asr`，模型权重不进入 Git。
- 提供 MoviePy 2、本地识别、字幕配置和模型目录的中文说明。

### 变更

- 全仓库视频主链路迁移至 MoviePy 2.x API。
- Azure Speech 密钥改为通过 `AZURE_SPEECH_KEY` 环境变量读取。
- 修复视频裁切边界、音频时长、BGM 循环和最终合成时的 MoviePy 2 兼容问题。
- 正式配置使用仓库内已跟踪的 `SourceHanSansSC-Bold.otf` 字体。

### 验证环境

- Windows 10/11。
- Python 3.12。
- MoviePy 2.x。
- RTX 3060 12GB。
- 本地识别最低目标配置为 GTX 1060 6GB；该型号仍需在实机上进一步验证。

### 已知限制

- 当前字幕默认通过 OpenCV/Pillow 逐帧烧录，会产生额外的视频编码过程。
- ASS/libass 单次字幕编码与批量并发生成尚未实现，设计记录见
  `docs/render-performance-development.md`。
- 本地语音识别需要兼容的 NVIDIA 驱动和 CUDA 版 PyTorch。
- 模型首次使用时需要联网下载，之后可复用项目内缓存离线运行。

[1.0.0]: https://github.com/Duximpresa/video_edit/releases/tag/v1.0.0
