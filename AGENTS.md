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

模型默认缓存在项目内但不进入 Git：

```text
models\asr
```

Git 只保留 `models/` 目录结构和说明文件。不要把模型权重、下载缓存或临时转码文件提交到 Git。

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
- `split_on_comma=true` 时应同时按中文/英文逗号 `，`、`,` 和句号 `。`、`.` 拆分。字段名为兼容旧配置而保留，不要仅按逗号处理。
- 分段前必须保留原始标点作为边界，不能先调用全文句号清理再拆分；正确顺序是“按标点切段 -> 清理每段标点 -> 计算时间比例”。
- 中文句号 `。` 和英文句号 `.` 不应出现在最终显示字幕中；`split_on_comma=false` 时保持整句时间轴，但仍清除显示文本中的句号。
- 分段缓存通过段落文本和段落数量校验。标点规则变化导致缓存与新分段不一致时，应重新计算并安全写回，不要复用失效缓存。
- 字幕规范化只用于显示、拆分和缓存校验，不得改写 `subtitles.json` 中人工维护的原始 `text`。
- 缺少字幕文件或映射时只输出警告，不应中断视频生成。

字幕样式从项目 JSON 的 `subtitle_config` 读取。配置文件必须保持标准 JSON，不要加入 `//`、`/* */` 等注释；字段说明应写入 README。

字体必须优先使用根目录 `font/` 下的文件，不依赖系统字体。

## 字幕分段实现思路

字幕分段入口位于 `modules/subtitle_tools.py` 的 `build_subtitle_segments()`：

1. 读取 `subtitles.json` 中当前随机配音文件对应的原始文字。
2. `split_on_comma=false` 时生成覆盖整个配音片段的一条字幕，只清理显示文本中的句号。
3. `split_on_comma=true` 时使用统一分隔正则识别中英文逗号和句号，再对每个非空片段执行显示文本规范化。
4. `character_ratio` 根据各段可见字符数占比分配当前配音片段时长。
5. `speech_timestamps` 优先匹配本地识别缓存中的字符级时间戳，必要时再调用配置的语音时间戳后端；失败后回退字符比例。
6. 缓存只保存 `start_ratio/end_ratio`，不保存绝对秒数，使同一音频在不同视频时长中仍可复用。
7. 写回缓存时使用字幕文件锁、临时文件和原子替换，避免批量并发任务互相覆盖或损坏 JSON。

新增或修改分段符时，必须同时补充覆盖中文标点、英文标点、混合标点、关闭拆分和旧缓存失效的测试。

## 视频渲染与批量并发

项目保留两套字幕渲染流程，由 `subtitle_config.render_mode` 选择：

- `legacy_opencv`：原有 MoviePy 输出后再用 OpenCV/Pillow 烧录字幕的兼容流程，也是缺省值。
- `single_pass_ass`：先把现有字幕时间轴和样式转换为临时 ASS，通过 FFmpeg `ass` 滤镜在 MoviePy 最终输出时一次完成视频编码。

ASS 实现规则：

- 使用现有 Pillow 字体测量和换行结果生成 ASS `\N`，避免两套流程换行差异过大。
- 从项目字体文件读取真实字体家族名称，并通过 FFmpeg `fontsdir` 指向根目录 `font/`。
- 字体颜色、透明度、描边、字间距、垂直百分比位置和最大行宽都应映射现有 `subtitle_config`，不要另建一套样式字段。
- Windows 路径传入 FFmpeg 滤镜前必须处理盘符、反斜杠、空格和特殊字符转义。
- `single_pass_ass` 缺少 libass/滤镜或字体加载失败时应明确报错，不自动静默回退旧流程。
- 临时 ASS、音频和中间文件必须使用任务独立临时目录并在结束后清理。

批量执行由 `batch_render.execution_mode` 选择：

- `serial`：保留原有顺序生成行为，也是缺省值。
- `parallel`：使用 `ProcessPoolExecutor` 进程级并发，每条任务拥有独立随机种子、临时目录和唯一输出名。

并发任务不得调用会终止其他任务 FFmpeg 进程的全局清理逻辑。单条失败应返回结构化错误并继续其他任务，最终汇总成功数、失败数、输出路径和分阶段耗时。字幕缓存写入必须继续使用跨进程文件锁。

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

ASS 单次编码或批量并发相关修改还应运行：

```powershell
D:\ProgramData\miniconda3\envs\main\python.exe -m unittest tests.test_render_performance -q
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
