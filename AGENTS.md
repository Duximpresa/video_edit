# 项目代理协作指南

本文件用于指导 AI 编码代理在本仓库中安全、稳定地工作。修改代码前应先阅读相关模块和配置，尽量保持现有业务行为不变。

## 项目概览

这是一个基于 MoviePy 2 的随机视频混剪工具。程序会从多个片段目录中随机选择视频和配音，拼接成最终视频，并支持 BGM、内嵌中文字幕、字幕分段缓存及本地语音识别。

主要文件：

- `modules/video_mixer.py`：视频选择、裁切、拼接、配音、BGM 和最终导出主流程。
- `modules/subtitle_tools.py`：字幕映射读取、字幕分段、缓存写入及字幕渲染。
- `modules/local_asr.py`：本地语音识别、GPU 检测、模型加载和回退逻辑。
- `test.py`：当前主要视频生成入口。
- `generate_subtitles_for_folder.py`：适合在 IDE 中直接运行的字幕批量生成入口。
- `generate_subtitle_maps.py`：字幕批量生成命令行入口。
- `config/`：项目配置文件。
- `font/`：内嵌字幕使用的本地字体。
- `tests/`：字幕映射等自动化测试。

## 环境安装

推荐使用项目当前 Conda 环境：

```powershell
D:\ProgramData\miniconda3\envs\main\python.exe -m pip install -r requirements.txt
```

需要本地语音识别时，再安装：

```powershell
D:\ProgramData\miniconda3\envs\main\python.exe -m pip install -r requirements-local-asr.txt
```

本地识别默认使用 Paraformer-zh，失败时依次回退到 faster-whisper `small` 和 `base`。6GB 是建议显存警告阈值，不是启动门槛；CUDA 不可用或 GPU 模型全部失败时，默认回退到 CPU faster-whisper `base`。

模型应缓存在项目外，例如：

```text
%LOCALAPPDATA%\video_edit\models\asr
```

不要把模型权重、下载缓存或临时转码文件提交到 Git。

## MoviePy 2 约定

本项目只支持 MoviePy 2，不要重新引入 MoviePy 1 API。

- 使用 `from moviepy import ...`，不要使用 `moviepy.editor`。
- 使用 `subclipped()`，不要使用 `subclip()`。
- 使用 `with_audio()`，不要使用 `set_audio()`。
- 使用 `with_duration()`，不要使用 `set_duration()`。
- 使用 `with_start()`，不要使用 `set_start()`。
- 使用 `resized()`，不要使用 `resize()`。
- MoviePy 2 的效果优先使用效果类及 `with_effects()`。
- 调用 `resized()` 时优先使用位置参数，避免不同 2.x 子版本的关键字名称差异。

除非任务明确要求，否则不要改变随机选材逻辑、片段时长算法、拼接顺序、输出目录、文件命名、编码器或 FFmpeg 参数。

## 字幕约定

每个实际包含音频的目录可放置一份 `subtitles.json`，音频 basename 作为 key。

代码必须兼容：

- v1 字符串字幕条目。
- v2 包含 `text` 和 `splits` 的对象条目。
- 已有的紧凑时间戳格式。

字幕修改规则：

- 默认只补充缺失或空白字幕，不覆盖人工校对内容。
- 只有明确启用覆盖模式时才能替换已有字幕。
- 字幕文本变化后，应清除该条目已经失效的分段缓存。
- 写入 JSON 时使用临时文件和原子替换，避免中途退出损坏文件。
- `split_timing_mode` 支持 `character_ratio` 和 `speech_timestamps`。
- 语音时间戳失败时可以回退到字符比例，但缓存必须标记实际使用的模式。
- `split_on_comma=false` 时应保持整句字幕。
- 缺少字幕文件或映射时只输出警告，不应中断视频生成。

字幕样式从项目 JSON 的 `subtitle_config` 读取。配置文件必须保持标准 JSON，不要加入 `//`、`/* */` 等注释；字段说明应写入 README。

字体必须优先使用根目录 `font/` 下的文件，不依赖系统字体。

## 本地语音识别

- 默认后端为 `local_paraformer`。
- Paraformer 使用 `ct-punc` 补充标点，并支持热词和字符级时间戳。
- GTX 1060 等低显存设备使用单文件、`batch_size=1`。
- `minimum_cuda_memory_gb` 只用于警告，不得因低于阈值而阻止识别器初始化。
- CUDA 不可用、模型加载失败或 OOM 时，先按配置尝试 GPU faster-whisper，再按 `allow_cpu_fallback` 回退到 CPU `cpu_fallback_model`。
- GPU 与 CPU 尝试必须分别记录失败状态，GPU 模型失败不得禁用同名 CPU 模型。
- `download_progress` 应保持终端单行刷新，避免模型下载刷出大量空行。
- `convert_to_simplified` 控制繁体转简体。
- 品牌名、商品名和材质词应通过配置中的热词维护，不要硬编码到识别模块。

Azure Speech 只作为可选备用。密钥必须通过环境变量读取：

```json
"speech_key": "${AZURE_SPEECH_KEY}"
```

严禁把 Azure 密钥、令牌、密码或其他凭据直接写入代码、配置示例、日志或提交记录。

## 配置与素材

- 修改配置前确认配置路径与当前素材目录匹配。
- `generate_subtitles_for_folder.py` 顶部的 `AUDIO_ROOT` 和 `CONFIG_PATH` 应指向同一个项目。
- `OVERWRITE = False` 是安全默认值，应优先保护人工字幕。
- 不要擅自删除或批量移动 `input/`、`output/`、`BGM/`、`font/` 中的文件。
- 视频、音频、生成成片和模型文件通常体积较大，只有用户明确要求时才加入 Git。
- 不要提交 MoviePy 临时音频、临时 MP4、缓存目录或未完成的下载文件。

## 验证要求

修改 Python 文件后至少执行语法检查：

```powershell
D:\ProgramData\miniconda3\envs\main\python.exe -m py_compile test.py modules\video_mixer.py modules\subtitle_tools.py modules\local_asr.py generate_subtitles_for_folder.py generate_subtitle_maps.py
```

字幕映射相关修改应运行：

```powershell
D:\ProgramData\miniconda3\envs\main\python.exe -m unittest tests.test_subtitle_map_generation -q
```

修改 JSON 配置后，应使用 `json.load` 验证配置合法。

完整视频生成耗时较长，并会使用真实素材、GPU 和输出目录。只有修改影响主链路或用户明确要求时才运行完整生成；完成后检查：

- 进程退出码为 0。
- 最终 MP4 存在且可播放。
- 视频包含音轨。
- 字幕中文显示正常且时间对齐。
- 没有残留 MoviePy 临时文件。

## Git 安全

- 默认在 `codex/` 前缀的新分支工作，不直接修改或推送 `main`。
- 工作区可能包含用户尚未提交的修改，不要撤销、覆盖或顺手格式化无关文件。
- 提交前使用 `git status --short` 和 `git diff` 核对范围。
- 使用明确的文件路径暂存，不要无条件执行 `git add .`。
- 不要提交密钥、个人环境配置、大型媒体、模型权重或无关生成文件。
- 未经用户明确要求，不要执行 destructive Git 命令、强制推送或改写历史。
