# video_edit
视频批量混剪工具

当前稳定版本：`v1.0.0`。版本变化请查看 [CHANGELOG.md](CHANGELOG.md)。

## 字幕配置说明

字幕功能会根据每次随机选中的配音文件，在对应音频文件夹的 `subtitles.json` 中读取字幕文字，并在最终视频中内嵌显示。配置文件仍然使用标准 JSON，不支持 `//` 或 `/* */` 注释；下面的说明用于查看字段含义。

推荐复制 `config/索罗娜短袖_字幕.json` 作为带字幕项目配置。字幕相关配置放在 `subtitle_config` 中：

```json
"subtitle_config": {
  "enabled": true,
  "render_mode": "legacy_opencv",
  "filename": "subtitles.json",
  "split_on_comma": true,
  "split_timing_mode": "speech_timestamps",
  "font": "SourceHanSansSC-Bold.otf",
  "font_size": 67,
  "letter_spacing": 0,
  "color": "#FFDE00",
  "opacity": 1.0,
  "stroke_enabled": true,
  "stroke_color": "#000000",
  "stroke_opacity": 1.0,
  "stroke_width": 5,
  "vertical_percent": 12,
  "max_width_percent": 86
}
```

字段说明：

- `enabled`：是否启用字幕。`true` 表示导出后内嵌字幕，`false` 表示不处理字幕。
- `render_mode`：字幕渲染方式。`legacy_opencv` 保留原有 OpenCV/Pillow 二次烧录；`single_pass_ass` 使用 FFmpeg/libass 在最终输出时一次编码完成字幕。
- `filename`：每个音频片段文件夹中的字幕映射文件名，默认是 `subtitles.json`。
- `split_on_comma`：是否按中文/英文逗号 `，`、`,` 和句号 `。`、`.` 自动拆分字幕。字段名为兼容旧配置而保留；`true` 表示遇到这些标点时拆分，`false` 表示整句显示。
- `split_timing_mode`：标点拆分后的计时方式。`character_ratio` 按字数比例分配片段时长；`speech_timestamps` 优先使用语音时间戳，失败时自动退回字数比例。
- `font`：字幕字体文件名，只从项目根目录的 `font/` 文件夹中读取。
- `font_size`：字幕字号，数值越大字幕越大。
- `letter_spacing`：字间距，单位是像素。`0` 表示默认间距，数值越大每个字符之间越松。
- `color`：字幕颜色，推荐使用 `#RRGGBB` 格式，例如黄色 `#FFDE00`。
- `opacity`：字幕透明度，范围 `0.0` 到 `1.0`，`1.0` 表示完全不透明。
- `stroke_enabled`：是否启用描边。`true` 开启描边，`false` 关闭描边。
- `stroke_color`：描边颜色，推荐使用 `#RRGGBB` 格式，例如黑色 `#000000`。
- `stroke_opacity`：描边透明度，范围 `0.0` 到 `1.0`。
- `stroke_width`：描边粗细，`0` 表示无描边，数值越大描边越粗。
- `vertical_percent`：字幕垂直位置百分比。`0` 靠近底部，`50` 在画面中间，`100` 靠近顶部。
- `max_width_percent`：字幕最大行宽百分比，用于自动换行。`86` 表示字幕最大宽度为画面宽度的 86%。

当前 `font/` 文件夹中可用字体：

- `AlibabaPuHuiTi-2-105-Heavy.ttf`
- `SourceHanSansSC-Bold.otf`
- `SourceHanSansSC-Heavy.otf`

注意：启用 `split_on_comma` 时，中文句号 `。` 和英文句号 `.` 会作为字幕分段边界且不显示；关闭拆分时也会移除句号。程序不会修改 `subtitles.json` 中保存的原始转写文字。

### 视频渲染与批量并发

未配置以下字段时，程序仍使用原有“串行 + OpenCV/Pillow”流程：

```json
"batch_render": {
  "execution_mode": "serial",
  "max_workers": 2,
  "continue_on_error": true,
  "base_seed": 20260607
}
```

- `execution_mode`：`serial` 顺序生成；`parallel` 使用独立进程同时生成多条视频。
- `max_workers`：并发进程数，仅 `parallel` 生效。RTX 3060 12GB 建议从 `2` 开始，GTX 1060 6GB 建议使用 `1`。
- `continue_on_error`：当前必须为 `true`，单条失败会记录错误并继续其他任务。
- `base_seed`：可选的批量随机种子。每条任务使用 `base_seed + task_index`，便于复现素材选择；不填写时每批自动生成。

`single_pass_ass` 会检查 FFmpeg 是否包含 `ass/libass` 滤镜。检查失败或字体无法加载时，该条任务直接失败，不自动回退旧字幕流程。并发模式会为输出增加毫秒和任务编号，避免同秒重名，并为每条任务使用独立临时目录。

Azure Speech 密钥不要写入 Git。配置中的 `speech_key` 可以写成 `${AZURE_SPEECH_KEY}`，运行前在系统环境变量中设置真实密钥即可。

### 一键生成字幕映射

如果不想手工填写每个音频文件夹里的 `subtitles.json`，可以运行根目录的
`generate_subtitles_for_folder.py`。先修改文件顶部的参数：

```python
AUDIO_ROOT = Path(r"input\赫学熊\索罗娜短袖\audio")
CONFIG_PATH = Path(r"config\索罗娜\索罗娜短袖.json")
OVERWRITE = False
LANGUAGE = "zh-CN"
SUBTITLE_FILENAME = "subtitles.json"
```

- `AUDIO_ROOT`：需要识别的音频根目录。程序会递归扫描全部子目录。
- `CONFIG_PATH`：提供 Azure Speech 区域和密钥配置的项目 JSON。
- `OVERWRITE`：默认 `False`，保留已有人工字幕，只补充缺失或空白项；设为 `True` 时重新识别。
- `LANGUAGE`：Azure Speech 识别语言，中文默认使用 `zh-CN`。
- `SUBTITLE_FILENAME`：每个含音频目录中生成的字幕映射文件名。

PowerShell 临时设置 Azure Speech 密钥后，可以直接在 IDE 中运行脚本：

```powershell
$env:AZURE_SPEECH_KEY="你的 Azure Speech 密钥"
```

程序支持 `.mp3`、`.aac`、`.acc`、`.m4a` 和 `.wav`。单个音频失败不会中断整批任务，
完成后会汇总扫描、成功、跳过和失败数量。覆盖新版对象格式字幕时会更新 `text` 并移除
已经失效的 `splits` 缓存，其他自定义字段会保留。

原有命令行入口仍可使用：

```powershell
python generate_subtitle_maps.py --config "config\索罗娜\索罗娜短袖.json"
python generate_subtitle_maps.py --voice-root "input\赫学熊\索罗娜短袖\audio" --overwrite
```

### 本地语音识别

字幕映射生成器支持完全本地运行。项目配置加入 `speech_recognition`：

```json
"speech_recognition": {
  "backend": "local_paraformer",
  "primary_model": "paraformer-zh",
  "punctuation_model": "ct-punc",
  "fallback_models": ["small", "base"],
  "minimum_cuda_memory_gb": 6,
  "model_cache_dir": "models\\asr",
  "download_progress": "auto",
  "convert_to_simplified": true,
  "fallback_hotwords": ["赫学熊", "索罗娜"],
  "hotwords": ["赫学熊", "索罗娜", "凉感", "吸湿排汗", "抗菌", "含棉量", "氨纶"]
}
```

- `backend`：`local_paraformer` 使用本地模型；`azure` 使用原有在线识别。
- `primary_model`：中文主模型，默认 `paraformer-zh`。
- `punctuation_model`：本地标点恢复模型，默认 `ct-punc`，用于自动生成逗号、问号等。
- `fallback_models`：主模型加载或推理失败后，按顺序尝试 faster-whisper INT8 模型。
- `minimum_cuda_memory_gb`：最低显存要求，默认 `6`，对应 GTX 1060 6GB。
- `model_cache_dir`：模型下载位置。相对路径从项目根目录计算，默认下载到
  `models/asr`。Git 只保留 `models` 目录结构和说明文件，实际模型权重不会提交。
- `download_progress`：`auto` 在普通 IDE 控制台隐藏刷屏进度，在终端中单行刷新；也可设为 `show` 或 `quiet`。

运行 `generate_subtitles_for_folder.py` 时，如果存在需要识别的音频，程序会自动
检查并下载缺少的 Paraformer、标点或 faster-whisper 回退模型。模型下载一次后
会复用 `models/asr` 中的缓存；如果所有字幕都已存在且 `OVERWRITE = False`，
程序会直接跳过识别，因此不会加载或下载模型。
- `convert_to_simplified`：将 Whisper 的繁体中文输出转换为简体，默认开启。
- `fallback_hotwords`：仅给 Whisper 回退模型的少量品牌提示；不要放大量功能词，避免误插。
- `hotwords`：品牌、商品、材质等业务词。仅 Paraformer 使用热词。

`AUDIO_ROOT` 与 `CONFIG_PATH` 应指向同一个项目，否则可能把另一个商品的热词用于当前音频。

GTX 1060 使用单文件、`batch_size=1`，不会强制开启依赖 Tensor Core 的 FP16。
RTX 3060 等新显卡使用相同主模型，保证字幕结果一致。Paraformer 失败或 CUDA
显存不足时，程序依次尝试 faster-whisper `small`、`base` 的 INT8 GPU 推理。
回退模型只使用 `fallback_hotwords` 作为保守提示，不保证达到 Paraformer 的热词增强效果。
本方案不自动回退 CPU；未检测到 CUDA 或显存不足 6GB 时会明确报错。

首次运行需要联网下载模型，下载完成后可以断网识别。安装依赖：

```powershell
pip install -r requirements.txt
pip install -r requirements-local-asr.txt
```

本地识别依赖固定使用 PyTorch CUDA 12.6，这是为了继续支持 GTX 1060 所属的
Pascal 架构。不要只从普通 PyPI 安装 `torch`，否则 Windows 上可能得到 CPU 版本，
导致 Paraformer 无法使用显卡。

本地识别会在 `subtitles.json` 中记录实际模型、设备、耗时和时间戳。字幕逗号分段
会优先复用这些时间戳，不再重复调用 Azure；时间戳无法匹配时才使用原有回退逻辑。
Paraformer 输出中的中文字间空格会自动清理。为方便人工查看，`recognition` 不重复保存
字幕全文，时间戳使用紧凑格式 `["文字", 开始毫秒, 结束毫秒]`；程序仍兼容旧对象格式。

### 字幕分段缓存

`subtitles.json` 仍然兼容原来的简单写法：

```json
{
  "version": 1,
  "items": {
    "xxx.mp3": "夏天热到爆炸，贺学雄索罗娜两杆T恤来救场了"
  }
}
```

当 `split_on_comma` 为 `true` 时，程序会按中英文逗号和句号分段，在第一次使用某条音频字幕时自动计算分段，并把结果缓存回同一个 `subtitles.json`，后续相同模式会直接复用：

```json
{
  "version": 2,
  "items": {
    "xxx.mp3": {
      "text": "夏天热到爆炸，贺学雄索罗娜两杆T恤来救场了",
      "splits": {
        "character_ratio": [
          {"text": "夏天热到爆炸", "start_ratio": 0.0, "end_ratio": 0.42},
          {"text": "贺学雄索罗娜两杆T恤来救场了", "start_ratio": 0.42, "end_ratio": 1.0}
        ]
      }
    }
  }
}
```

缓存里保存的是比例，不是具体秒数，所以同一条配音在不同视频里仍然可以复用。不同 `split_timing_mode` 的缓存会分别保存；如果你手动修改了字幕文本，程序会自动重新计算对应分段。
