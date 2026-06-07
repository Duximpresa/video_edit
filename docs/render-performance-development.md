# 视频渲染性能开发文档

> 状态：功能已实施，并已完成当前 RTX 3060 环境真实素材验证
>
> 目标版本：MoviePy 2.x
>
> 主要目标：保留现有工作流，同时增加 ASS 单次字幕编码和批量并发生成两个可选功能

## 1. 背景

当前带字幕的视频生成会经历以下处理：

1. MoviePy 拼接视频、混合配音和 BGM。
2. FFmpeg 使用 `h264_nvenc` 输出完整视频。
3. OpenCV 再次读取已经生成的视频。
4. Pillow 逐帧绘制中文字幕。
5. OpenCV 使用 `mp4v` 输出无音频临时视频。
6. FFmpeg 再次编码字幕视频，并复制原视频音轨。

这套流程稳定且字幕样式可控，但存在重复解码和重复编码。增加
`write_videofile(threads=...)` 对当前 NVENC 编码帮助有限，因为本机 FFmpeg
报告 `h264_nvenc` 不支持普通 FFmpeg 帧线程。

本次优化采用两条独立路线：

- 使用 ASS/libass，在 MoviePy 最终输出时直接烧录字幕，只编码一次视频。
- 使用多个独立进程并行生成多条成片，提高批量任务吞吐量。

两项功能必须可以单独启用，也可以组合启用。

## 2. 兼容原则

- 未配置任何新字段时，继续使用现有串行 OpenCV/Pillow 工作流。
- 不删除或重写现有 `burn_subtitles_to_video()`。
- 不改变随机选材、片段时长、字幕分段、BGM、音量、输出目录和编码参数。
- ASS 工作流失败时直接终止当前任务，不自动回退旧工作流。
- 并发模式中单个任务失败不影响其他任务，最后统一汇总。
- GTX 1060 6GB 只提供推荐配置，不在没有实机时宣称通过验证。

## 3. 配置设计

```json
{
  "subtitle_config": {
    "enabled": true,
    "render_mode": "legacy_opencv"
  },
  "batch_render": {
    "execution_mode": "serial",
    "max_workers": 2,
    "continue_on_error": true
  }
}
```

### 3.1 字幕渲染模式

`subtitle_config.render_mode`：

| 值 | 行为 |
| --- | --- |
| `legacy_opencv` | 使用现有 OpenCV/Pillow 二次字幕烧录流程，默认值 |
| `single_pass_ass` | 使用 ASS/libass，在第一次 NVENC 输出时直接烧录字幕 |

字幕关闭时，`render_mode` 不参与处理。

### 3.2 批量执行模式

`batch_render.execution_mode`：

| 值 | 行为 |
| --- | --- |
| `serial` | 现有顺序生成方式，默认值 |
| `parallel` | 使用独立进程并行生成 |

`batch_render.max_workers`：

- 只在 `parallel` 模式中生效。
- 必须是大于等于 `1` 的整数。
- RTX 3060 12GB 推荐从 `2` 开始。
- GTX 1060 6GB 推荐使用 `1`，确认稳定后再测试 `2`。
- 不根据 CPU 或显存自动修改用户配置。

`batch_render.continue_on_error`：

- 当前版本固定支持 `true`。
- 单条失败时记录错误并继续其他任务。

## 4. ASS 单次字幕编码

### 4.1 数据流

```text
随机选材
  -> 构建 MoviePy Clip
  -> 生成字幕时间轴 subtitle_segments
  -> 生成临时 ASS 文件
  -> MoviePy 将原始帧传给 FFmpeg
  -> FFmpeg ass 滤镜烧录字幕
  -> h264_nvenc 编码
  -> 合并 MoviePy 临时 AAC
  -> 最终 MP4
```

新流程不会生成 OpenCV `mp4v` 临时视频，也不会执行第二次 NVENC 编码。

### 4.2 ASS 文件生成

ASS 文件由现有 `subtitle_segments` 生成，每条事件包含：

- `start`：字幕开始时间。
- `end`：字幕结束时间。
- `text`：字幕文字。

时间转换为 ASS 的 `H:MM:SS.cc` 格式。空文字、结束时间不大于开始时间的
片段不写入 ASS。

ASS 文件使用：

- `PlayResX`：配置中的视频宽度。
- `PlayResY`：配置中的视频高度。
- UTF-8 编码。
- 独立任务临时目录。

### 4.3 字幕样式映射

| 当前配置 | ASS 表达 |
| --- | --- |
| `font` | 字体文件内部的字体家族名称 |
| `font_size` | `Fontsize` |
| `letter_spacing` | `Spacing` 或事件级 `\fsp` |
| `color` | `PrimaryColour` |
| `opacity` | ASS 反向 Alpha |
| `stroke_enabled` | 控制 `Outline` 是否为零 |
| `stroke_color` | `OutlineColour` |
| `stroke_opacity` | 描边颜色的反向 Alpha |
| `stroke_width` | `Outline` |
| `vertical_percent` | 事件级 `\pos` |
| `max_width_percent` | 生成 ASS 前使用现有 Pillow 测量逻辑换行 |

ASS 颜色使用 `&HAABBGGRR`。透明度需要从当前 `0.0-1.0` 正向透明度转换为
ASS 的反向 Alpha：

```text
ass_alpha = 255 - round(opacity * 255)
```

### 4.4 字体处理

- 字体仍从项目根目录 `font/` 读取。
- 使用 Pillow 加载字体文件并读取实际字体家族名称。
- FFmpeg `ass` 滤镜通过 `fontsdir` 指向项目字体目录。
- 字体不存在、无法读取字体名称或 FFmpeg 无法加载字体时，当前任务直接失败。

### 4.5 换行和位置

为尽量保持旧流程视觉一致：

- 继续使用现有 Pillow 字符宽度测量和自动换行逻辑。
- 生成 ASS 时将换行转换为 `\N`。
- 按当前视频宽度和 `max_width_percent` 计算最大文本宽度。
- 使用现有 `vertical_percent` 语义：`0` 靠近底部，`50` 居中，
  `100` 靠近顶部。
- 每条字幕根据实际换行后的文本高度计算中心点，再通过 ASS `\pos(x,y)`
  定位。

### 4.6 FFmpeg 滤镜

当前 FFmpeg 已确认包含：

- `ass`
- `subtitles`
- `libass`
- FreeType
- FriBidi
- HarfBuzz

启动 `single_pass_ass` 前仍需运行能力检查。滤镜链需要同时保留当前的
像素格式要求：

```text
ass=<临时ASS路径>:fontsdir=<项目字体目录>,format=yuv420p
```

Windows 路径必须转为正斜杠，并正确转义盘符冒号、单引号、逗号和滤镜特殊字符。

## 5. 批量并发生成

### 5.1 并发模型

使用 `ProcessPoolExecutor`，不使用线程池共享 MoviePy Clip。

原因：

- MoviePy、FFmpeg reader 和 OpenCV 对象不适合跨线程共享。
- Python 字幕绘制和帧处理可能受到 GIL 影响。
- 独立进程可以隔离随机状态、临时文件、FFmpeg 子进程和异常。

父进程负责：

- 读取配置。
- 创建任务参数。
- 分配任务编号和随机种子。
- 收集结果。
- 输出最终汇总。

子进程负责一条完整视频：

- 随机选择素材。
- 构建 MoviePy Clip。
- 混合音频。
- 生成字幕。
- 输出最终视频。
- 返回结构化结果。

### 5.2 随机种子

每个任务使用不同的确定性种子：

```text
seed = base_seed + task_index
```

如果配置没有提供 `base_seed`，父进程在本次批量任务开始时生成一个随机基础种子。
日志中记录基础种子，便于复现问题。

### 5.3 输出命名

旧串行模式继续使用现有名称。

并发模式必须增加任务编号和更细时间精度，例如：

```text
赫学熊混剪_索罗娜短袖_2026-06-07_12-30-45-123_task-001.mp4
```

这样可以避免多个进程在同一秒创建相同文件。

### 5.4 临时文件隔离

每个任务创建独立临时目录，存放：

- MoviePy 临时音频。
- ASS 文件。
- 旧字幕模式产生的临时视频。
- FFmpeg 日志。

任务成功或失败后清理自己的临时目录，不处理其他任务的文件。

### 5.5 FFmpeg 进程安全

现有 `kill_ffmpeg_processes()` 会终止系统中所有名称包含 `ffmpeg` 的进程，
不能在并发子任务中调用。

- 旧串行路径保留当前行为，避免改变原工作流。
- 并发路径禁止调用全局清理函数。
- 子任务只等待和清理自己启动的 FFmpeg 进程。

### 5.6 字幕缓存并发写入

多个任务可能同时为同一个音频补充 `subtitles.json` 分段缓存。

写入步骤必须使用跨进程锁：

1. 获取与字幕文件对应的锁文件。
2. 重新读取最新 JSON。
3. 只合并当前音频、当前模式的缓存。
4. 使用现有临时文件和 `os.replace()` 原子写入。
5. 释放锁。

等待锁超时应使当前任务失败并记录明确错误，不能写入不完整 JSON。

## 6. 公共结果和计时

每条视频生成返回：

```python
{
    "task_index": 0,
    "status": "success",
    "output_file": "output/xxx.mp4",
    "seed": 12345,
    "subtitle_render_mode": "single_pass_ass",
    "timings": {
        "material_prepare": 0.0,
        "audio_mix": 0.0,
        "video_render": 0.0,
        "subtitle_render": 0.0,
        "total": 0.0
    },
    "error": null
}
```

失败任务使用 `status: "failed"` 并填写 `error`。旧调用方可以继续忽略返回值。

对于 ASS 单次编码，字幕与视频在同一 FFmpeg 过程完成：

- `video_render` 记录整个单次编码耗时。
- `subtitle_render` 记录 ASS 文件准备耗时。

## 7. 分阶段开发顺序

### 阶段一：基准与公共接口

- 增加分阶段计时和结构化结果。
- 固定随机种子建立旧流程基准。
- 验证未配置新字段时行为不变。

### 阶段二：ASS 生成器

- 实现时间、颜色、透明度和路径转换。
- 实现字体名称读取、换行和定位。
- 实现临时 ASS 文件生成。
- 完成纯函数单元测试。

### 阶段三：单次编码接入

- 增加 `single_pass_ass` 分支。
- 检查 FFmpeg/libass 能力。
- 将 ASS 和现有像素格式合并进滤镜链。
- 验证音视频和字幕。

### 阶段四：批量并发

- 抽取顶层可序列化 worker。
- 增加任务种子、唯一命名和临时目录。
- 增加字幕缓存跨进程锁。
- 增加失败隔离和批量汇总。

### 阶段五：完整回归和性能测试

- 旧串行 + OpenCV。
- 新串行 + ASS。
- 新并发 + ASS。
- 新并发 + OpenCV。

每个阶段通过验证后再进入下一阶段，出现回归时不继续叠加修改。

## 8. 测试和验收

### 8.1 自动化测试

- ASS 时间格式。
- RGB 到 ASS ABGR 转换。
- 透明度到反向 Alpha 转换。
- 字号、字间距和描边映射。
- 字体家族名称读取。
- 中文、空格和特殊字符路径转义。
- 自动换行和百分比位置。
- 旧配置默认值。
- 并发输出名称唯一性。
- 任务失败隔离和汇总。
- 字幕 JSON 并发写入。
- 现有字幕映射测试。
- Python `py_compile`。

### 8.2 短视频烟测

使用程序生成的短视频验证：

- ASS 字幕肉眼可见。
- 视频存在 H.264 视频流。
- 视频存在 AAC 音频流。
- 字幕开始和结束时间正确。
- 输出没有遗留临时文件。

### 8.3 真实项目性能测试

使用同一随机种子和同一批素材，对比：

| 场景 | 数量 | 目标 |
| --- | ---: | --- |
| 串行 + OpenCV | 1 | 建立基准 |
| 串行 + ASS | 1 | 总耗时至少降低 20% |
| 串行 + ASS | 2 | 建立两条顺序基准 |
| 并发 + ASS，2 workers | 2 | 总吞吐至少提高 15% |
| 并发 + OpenCV，2 workers | 2 | 验证功能组合 |

同时记录：

- 分阶段耗时。
- CPU 使用率。
- GPU 使用率。
- NVENC 会话数。
- 峰值内存和显存。
- 文件大小和码率。
- 音视频时长。

目标值用于判断优化是否有意义，未达到目标时如实记录，不为了通过测试改变画质。

## 9. 硬件建议

### RTX 3060 12GB

```json
"batch_render": {
  "execution_mode": "parallel",
  "max_workers": 2,
  "continue_on_error": true
}
```

### GTX 1060 6GB

```json
"batch_render": {
  "execution_mode": "parallel",
  "max_workers": 1,
  "continue_on_error": true
}
```

GTX 1060 是否适合 `max_workers=2` 必须实机测试后决定。

## 10. 已确认的决策

- 原有流程必须保留。
- 新功能全部由 JSON 配置显式启用。
- ASS 失败时当前任务立即失败，不自动回退。
- 并发数量由配置明确指定。
- 并发任务失败后继续其他任务。
- 不使用 `threads=64` 作为本次主要优化手段。
- 不删除 OpenCV/Pillow 字幕实现。
- 开发前先审阅本文件，确认后才开始修改功能代码。

## 11. 实施结果

实现日期：2026-06-07。

已完成：

- 保留 `legacy_opencv` 默认流程。
- 新增 `single_pass_ass` 单次字幕编码。
- 新增结构化任务结果和分阶段计时。
- 新增 `serial` / `parallel` 批量执行模式。
- 并发任务使用独立种子、毫秒级任务名和临时目录。
- 并发任务不调用全局 `kill_ffmpeg_processes()`。
- `subtitles.json` 分段缓存写入增加跨进程锁和原子替换。
- 新增 ASS 转换、配置兼容、唯一命名、失败隔离和并发缓存测试。

### 11.1 当前机器实测

测试环境：

- Windows。
- Python 3.12。
- MoviePy 2.1.2。
- RTX 3060 12GB。
- 真实索罗娜短袖素材。
- 1080×1920、60fps、H.264 NVENC、AAC。
- 固定 `base_seed=20260607`。

| 场景 | 数量 | 墙钟耗时 | 结果 |
| --- | ---: | ---: | --- |
| 串行 + OpenCV | 1 | 157.83s | 成功 |
| 串行 + ASS | 1 | 68.99s | 成功 |
| 串行 + ASS | 2 | 133.58s | 两条成功 |
| 并发 + ASS，2 workers | 2 | 91.13s | 两条成功 |
| 并发 + OpenCV，2 workers | 2 | 198.28s | 两条成功 |

测得：

- 单条 ASS 相比旧 OpenCV 流程降低约 56.3% 总耗时。
- 两条 ASS 并发相比两条 ASS 串行降低约 31.8% 墙钟耗时。
- 两项性能目标均达到。
- 并发旧字幕流程功能可用，但 CPU 逐帧绘制竞争明显，不建议将其作为首选性能模式。

本次未自动采集 CPU、GPU、显存和峰值内存曲线，因此不对这些指标作定量结论。
GTX 1060 6GB 仍未进行实机测试，继续建议 `max_workers=1`。
