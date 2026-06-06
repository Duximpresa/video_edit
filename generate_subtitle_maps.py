import argparse
import json
import os
from pathlib import Path

from modules.subtitle_tools import generate_subtitle_maps


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_config_value(value):
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.getenv(value[2:-1], "")
    return value


def main():
    parser = argparse.ArgumentParser(description="Generate subtitles.json files for voice folders.")
    parser.add_argument(
        "--config",
        default="config/索罗娜/索罗娜短袖.json",
        help="Project config JSON path.",
    )
    parser.add_argument(
        "--voice-root",
        default=None,
        help="Audio root folder. Defaults to voice_folder_path in the config.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate existing non-empty subtitle entries.",
    )
    parser.add_argument(
        "--language",
        default="zh-CN",
        help="Speech recognition language, default zh-CN.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    voice_config = config["voice_config"]
    recognition_config = config.get("speech_recognition", {"backend": "azure"})
    voice_root = Path(args.voice_root or config["voice_folder_path"])

    written_files = generate_subtitle_maps(
        voice_root=voice_root,
        speech_key=resolve_config_value(voice_config["speech_key"]),
        service_region=voice_config["service_region"],
        overwrite=args.overwrite,
        language=args.language,
        recognition_config=recognition_config,
    )

    print("字幕映射生成完成")
    for file_path in written_files:
        print(file_path)


if __name__ == "__main__":
    main()
