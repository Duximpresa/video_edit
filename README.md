# video_edit
视频批量混剪工具

## 字幕配置说明

字幕功能会根据每次随机选中的配音文件，在对应音频文件夹的 `subtitles.json` 中读取字幕文字，并在最终视频中内嵌显示。配置文件仍然使用标准 JSON，不支持 `//` 或 `/* */` 注释；下面的说明用于查看字段含义。

推荐复制 `config/索罗娜短袖_字幕.json` 作为带字幕项目配置。字幕相关配置放在 `subtitle_config` 中：

```json
"subtitle_config": {
  "enabled": true,
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
- `filename`：每个音频片段文件夹中的字幕映射文件名，默认是 `subtitles.json`。
- `split_on_comma`：是否按中文逗号 `，` 和英文逗号 `,` 自动拆分字幕。`true` 表示拆分，`false` 表示整句显示。
- `split_timing_mode`：逗号拆分后的计时方式。`character_ratio` 按字数比例分配片段时长；`speech_timestamps` 优先使用 Azure Speech 语音时间戳，失败时自动退回字数比例。
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

注意：字幕显示时会自动去掉末尾的中文句号 `。` 和英文句号 `.`，但不会修改 `subtitles.json` 中保存的原始转写文字。

Azure Speech 密钥不要写入 Git。配置中的 `speech_key` 可以写成 `${AZURE_SPEECH_KEY}`，运行前在系统环境变量中设置真实密钥即可。

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

当 `split_on_comma` 为 `true` 时，程序会在第一次使用某条音频字幕时自动计算分段，并把结果缓存回同一个 `subtitles.json`，后续相同模式会直接复用：

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
