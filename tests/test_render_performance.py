import json
import tempfile
import unittest
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from modules.subtitle_tools import (
    _ass_color,
    _ass_timestamp,
    _escape_ffmpeg_filter_path,
    _write_split_cache,
    create_ass_subtitle_file,
)
from modules.video_mixer import (
    _failed_task_result,
    _generation_kwargs_from_config,
    _render_video_task,
    generate_datetime_string,
)


def _write_cache_worker(args):
    folder, audio_name, text = args
    item = {"text": text, "splits": {}}
    segments = [{"text": text, "start_ratio": 0.0, "end_ratio": 1.0}]
    _write_split_cache(folder, "subtitles.json", audio_name, item, "character_ratio", segments)


class RenderPerformanceTests(unittest.TestCase):
    def test_ass_timestamp_rounds_to_centiseconds(self):
        self.assertEqual(_ass_timestamp(0), "0:00:00.00")
        self.assertEqual(_ass_timestamp(65.678), "0:01:05.68")

    def test_ass_color_uses_abgr_and_reverse_alpha(self):
        self.assertEqual(_ass_color("#112233", 1.0), "&H00332211")
        self.assertEqual(_ass_color("#FFFFFF", 0.0), "&HFFFFFFFF")

    def test_filter_path_escapes_windows_drive_and_special_characters(self):
        escaped = _escape_ffmpeg_filter_path(r"C:\work dir\a,b'sub.ass")
        self.assertEqual(escaped, r"C\:/work dir/a\,b\'sub.ass")

    def test_ass_file_contains_style_position_spacing_and_wrapped_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "test.ass"
            create_ass_subtitle_file(
                [
                    {
                        "start": 0.25,
                        "end": 2.5,
                        "text": "这是一段用于测试自动换行的中文字幕",
                    }
                ],
                {
                    "font": "SourceHanSansSC-Bold.otf",
                    "font_size": 42,
                    "letter_spacing": 2,
                    "color": "#FFFFFF",
                    "opacity": 1.0,
                    "stroke_enabled": True,
                    "stroke_color": "#000000",
                    "stroke_opacity": 1.0,
                    "stroke_width": 4,
                    "vertical_percent": 30,
                    "max_width_percent": 35,
                },
                (1080, 1920),
                output,
            )
            content = output.read_text(encoding="utf-8-sig")

        self.assertIn("Source Han Sans SC", content)
        self.assertIn(r"\fsp2", content)
        self.assertIn(r"\pos(540,", content)
        self.assertIn(r"\N", content)
        self.assertIn("Dialogue: 0,0:00:00.25,0:00:02.50", content)

    def test_parallel_split_cache_writes_keep_all_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks = [
                (temp_dir, f"voice-{index}.mp3", f"字幕{index}")
                for index in range(4)
            ]
            with ProcessPoolExecutor(max_workers=2) as executor:
                list(executor.map(_write_cache_worker, tasks))

            saved = json.loads(
                (Path(temp_dir) / "subtitles.json").read_text(encoding="utf-8")
            )
            self.assertEqual(set(saved["items"]), {task[1] for task in tasks})

    def test_old_config_defaults_to_legacy_serial_behavior(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_root = root / "video"
            audio_root = root / "audio"
            (video_root / "01").mkdir(parents=True)
            (audio_root / "01").mkdir(parents=True)
            config = {
                "project_name": "test",
                "output_folder": str(root / "output"),
                "video_folder_path": str(video_root),
                "voice_folder_path": str(audio_root),
                "number_of_video_list": [1],
                "bgm_folder_path": str(root),
                "audio_volumex": 1,
                "bgm_volumex": 1,
                "clip_size": [320, 240],
                "fps": 24,
            }
            kwargs = _generation_kwargs_from_config(config)

        self.assertEqual(kwargs["subtitle_render_mode"], "legacy_opencv")
        self.assertTrue(kwargs["subtitle_enabled"])

    def test_parallel_output_names_include_milliseconds_and_task(self):
        name = generate_datetime_string(
            "project",
            include_milliseconds=True,
            task_index=1,
        )
        self.assertRegex(
            name,
            r"^project_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-\d{3}_task-002$",
        )

    def test_worker_returns_structured_failure(self):
        result = _render_video_task({
            "task_index": 3,
            "seed": 123,
            "parallel_mode": True,
            "generation_kwargs": {},
        })
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["task_index"], 3)
        self.assertEqual(result["seed"], 123)
        self.assertTrue(result["error"])

    def test_parent_can_summarize_crashed_worker(self):
        task = {
            "task_index": 2,
            "seed": 456,
            "generation_kwargs": {
                "subtitle_render_mode": "single_pass_ass",
            },
        }
        result = _failed_task_result(task, "worker exited")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["task_index"], 2)
        self.assertEqual(result["subtitle_render_mode"], "single_pass_ass")
        self.assertEqual(result["error"], "worker exited")


if __name__ == "__main__":
    unittest.main()
