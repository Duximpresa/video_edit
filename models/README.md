# 本地模型目录

本目录用于保存项目运行时自动下载的本地 AI 模型。

当前目录约定：

- `asr/`：语音转文字模型，包括 Paraformer、标点模型和 faster-whisper 回退模型。

运行 `generate_subtitles_for_folder.py` 时，如果配置使用
`"backend": "local_paraformer"`，程序会在首次需要识别音频时自动下载缺少的
模型到 `models/asr/`。

Git 只提交本说明文件和空目录结构，不提交模型权重、缓存、锁文件或下载中的
临时文件。
