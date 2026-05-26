# video_edit

自动混剪与配音视频生成工具（MoviePy + Azure TTS）。

## 1. 环境准备

1. 安装 Python 3.10+ 与 FFmpeg（并确保 `ffmpeg` 可在终端执行）。
2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置环境变量（可参考 `.env.example`）：

- `AZURE_SPEECH_KEY`
- `AZURE_SERVICE_REGION`

## 2. 目录说明

- `modules/`：核心混剪与语音逻辑
- `app/`：语音调用封装
- `config/`：项目配置文件
- `utils/`：通用工具函数
- `input/`：本地素材目录（已忽略，不提交）
- `output/`：生成结果目录（已忽略，不提交）
- `storage/Voices/`：配音缓存（已忽略，不提交）

## 3. 运行方式

### 批量混剪（BGM）

在 `modules/video_mixer.py` 中调用：

- `batch_multiple_video_bgm_generation(config_dir)`

### 批量混剪（配音 + BGM）

在 `modules/video_mixer.py` 中调用：

- `batch_multiple_video_voice_bgm_generation(config_dir)`

## 4. 配置文件建议字段

放在 `config/*.json`，典型字段包括：

- `project_name`
- `output_folder`
- `bgm_folder_path`
- `video_folder_path`
- `voice_folder_path`
- `number_of_video_list`
- `duration_of_video_list`
- `generated_quantity`
- `fps`

## 5. 常见问题

1. 报错素材数量不足：检查对应目录下视频/音频数量是否满足 `number_of_video_list`。
2. 报错配置长度不一致：`folder_path_list`、`number_of_video_list`、`duration_of_video_list` 必须一一对应。
3. Azure 鉴权失败：检查环境变量是否正确设置、区域是否匹配。
4. 视频导出失败：确认 FFmpeg 可用，且编码器（如 `h264_nvenc`）在本机可用。
