import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.subtitle_tools import generate_subtitle_maps


class SubtitleMapGenerationTests(unittest.TestCase):
    def _audio_file(self, folder, name):
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_bytes(b"test")
        return path

    def test_recursively_generates_maps_and_continues_after_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = self._audio_file(root / "part-1", "first.mp3")
            failed = self._audio_file(root / "nested" / "part-2", "failed.wav")

            def transcribe(path, *_args, **_kwargs):
                if path == failed:
                    raise RuntimeError("recognition failed")
                return "第一句。"

            with patch("modules.subtitle_tools.transcribe_audio_file", side_effect=transcribe):
                report = generate_subtitle_maps(
                    root,
                    "test-key",
                    "test-region",
                    return_report=True,
                )

            self.assertEqual(report["audio_folder_count"], 2)
            self.assertEqual(report["recognized_count"], 1)
            self.assertEqual(report["failed_count"], 1)
            self.assertIn(str(failed), report["failed_files"])
            self.assertEqual(
                json.loads((first.parent / "subtitles.json").read_text(encoding="utf-8"))["items"]["first.mp3"],
                "第一句。",
            )
            self.assertEqual(
                json.loads((failed.parent / "subtitles.json").read_text(encoding="utf-8"))["items"]["failed.wav"],
                "",
            )

    def test_preserves_manual_text_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio = self._audio_file(root / "part", "voice.m4a")
            subtitle_file = audio.parent / "subtitles.json"
            subtitle_file.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "items": {
                            "voice.m4a": {
                                "text": "人工校对文本",
                                "splits": {"character_ratio": [{"text": "人工校对文本"}]},
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch("modules.subtitle_tools.transcribe_audio_file") as transcribe:
                report = generate_subtitle_maps(
                    root,
                    "test-key",
                    "test-region",
                    return_report=True,
                )

            transcribe.assert_not_called()
            self.assertEqual(report["skipped_count"], 1)
            saved = json.loads(subtitle_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["items"]["voice.m4a"]["text"], "人工校对文本")
            self.assertIn("splits", saved["items"]["voice.m4a"])

    def test_overwrite_updates_object_text_and_removes_stale_splits(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio = self._audio_file(root, "voice.aac")
            subtitle_file = root / "subtitles.json"
            subtitle_file.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "items": {
                            "voice.aac": {
                                "text": "旧文字",
                                "splits": {"character_ratio": [{"text": "旧文字"}]},
                                "note": "保留字段",
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch("modules.subtitle_tools.transcribe_audio_file", return_value="新文字"):
                generate_subtitle_maps(
                    root,
                    "test-key",
                    "test-region",
                    overwrite=True,
                )

            saved_item = json.loads(subtitle_file.read_text(encoding="utf-8"))["items"]["voice.aac"]
            self.assertEqual(saved_item["text"], "新文字")
            self.assertNotIn("splits", saved_item)
            self.assertEqual(saved_item["note"], "保留字段")


if __name__ == "__main__":
    unittest.main()
