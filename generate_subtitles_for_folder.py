"""在 IDE 中直接运行，为指定音频目录生成 subtitles.json。"""

import json
import os
from pathlib import Path

from modules.subtitle_tools import generate_subtitle_maps


# 修改下面几项后，直接在 IDE 中运行本文件。
AUDIO_ROOT = Path(r"input/赫学熊/防寒服/2024-_11_02/audio")
CONFIG_PATH = Path(r"config\索罗娜\索罗娜短袖.json")
OVERWRITE = False
LANGUAGE = "zh-CN"
SUBTITLE_FILENAME = "subtitles.json"


def _resolve_config_value(value):
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.getenv(value[2:-1], "")
    return value


def run():
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    voice_config = config["voice_config"]
    report = generate_subtitle_maps(
        voice_root=AUDIO_ROOT,
        speech_key=_resolve_config_value(voice_config.get("speech_key")),
        service_region=voice_config.get("service_region"),
        subtitle_filename=SUBTITLE_FILENAME,
        overwrite=OVERWRITE,
        language=LANGUAGE,
        return_report=True,
    )

    print("\n本次处理结果")
    print(f"扫描音频文件夹：{report['audio_folder_count']}")
    print(f"扫描音频文件：{report['audio_file_count']}")
    print(f"识别成功：{report['recognized_count']}")
    print(f"保留已有字幕：{report['skipped_count']}")
    print(f"识别失败：{report['failed_count']}")
    return report


if __name__ == "__main__":
    run()
