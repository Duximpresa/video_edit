import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.subtitle_tools import (
    _serialize_subtitle_payload,
    build_subtitle_segments,
    generate_subtitle_maps,
    normalize_subtitle_text,
)
from modules.local_asr import (
    LocalSpeechRecognizer,
    PROJECT_ROOT,
    TranscriptionResult,
    _compact_chinese_spacing,
    _configure_download_progress,
    _expand_path,
    detect_cuda_device,
)


class SubtitleMapGenerationTests(unittest.TestCase):
    def _audio_file(self, folder, name):
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_bytes(b"test")
        return path

    def test_removes_chinese_and_english_periods_everywhere(self):
        self.assertEqual(
            normalize_subtitle_text("前半句。后半句.结尾。"),
            "前半句后半句结尾",
        )

    def test_split_uses_chinese_and_english_periods_as_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio = self._audio_file(root, "voice.mp3")
            (root / "subtitles.json").write_text(
                json.dumps(
                    {
                        "version": 2,
                        "items": {
                            "voice.mp3": {
                                "text": "第一句。第二句.第三句，第四句,第五句。",
                                "splits": {},
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            segments = build_subtitle_segments(
                root,
                audio,
                0,
                10,
                split_timing_mode="character_ratio",
            )

            self.assertEqual(
                [segment["text"] for segment in segments],
                ["第一句", "第二句", "第三句", "第四句", "第五句"],
            )
            self.assertEqual(segments[0]["start"], 0)
            self.assertEqual(segments[-1]["end"], 10)

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

    def test_local_backend_writes_recognition_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._audio_file(root, "voice.mp3")
            result = TranscriptionResult(
                text="本地识别结果",
                backend="paraformer",
                model="paraformer-zh",
                device="cuda:0",
                elapsed_seconds=0.1,
                timestamps=[
                    {"text": "本", "start_ms": 0, "end_ms": 100}
                ],
            )

            with patch(
                "modules.local_asr.LocalSpeechRecognizer.__init__",
                return_value=None,
            ), patch(
                "modules.local_asr.LocalSpeechRecognizer.transcribe",
                return_value=result,
            ):
                generate_subtitle_maps(
                    root,
                    recognition_config={"backend": "local_paraformer"},
                )

            saved = json.loads((root / "subtitles.json").read_text(encoding="utf-8"))
            item = saved["items"]["voice.mp3"]
            self.assertEqual(item["text"], "本地识别结果")
            self.assertEqual(item["recognition"]["model"], "paraformer-zh")
            self.assertNotIn("text", item["recognition"])

    def test_compacts_paraformer_chinese_spacing(self):
        self.assertEqual(
            _compact_chinese_spacing("冬 天 就 要 来 临 了"),
            "冬天就要来临了",
        )
        self.assertEqual(
            _compact_chinese_spacing("hello world"),
            "hello world",
        )

    def test_quiet_download_progress_disables_tqdm(self):
        with patch("sys.stdout.isatty", return_value=False), patch(
            "sys.stderr.isatty",
            return_value=False,
        ), patch.dict("os.environ", {}, clear=False):
            _configure_download_progress("auto")
            self.assertEqual(os.environ["TQDM_DISABLE"], "1")

    def test_relative_model_cache_is_resolved_from_project_root(self):
        self.assertEqual(
            _expand_path(r"models\asr"),
            (PROJECT_ROOT / "models" / "asr").resolve(),
        )

    def test_recognition_metadata_uses_compact_timestamps(self):
        result = TranscriptionResult(
            text="冬天",
            backend="paraformer",
            model="paraformer-zh",
            device="cuda:0",
            elapsed_seconds=0.2,
            timestamps=[
                {"text": "冬", "start_ms": 100, "end_ms": 200},
                {"text": "天", "start_ms": 200, "end_ms": 400},
            ],
        )
        payload = result.to_dict()
        self.assertNotIn("text", payload)
        self.assertEqual(
            payload["timestamps"],
            [["冬", 100, 200], ["天", 200, 400]],
        )

    def test_subtitle_json_keeps_timestamps_on_one_line(self):
        content = _serialize_subtitle_payload({
            "version": 2,
            "items": {
                "voice.mp3": {
                    "text": "冬天",
                    "recognition": {
                        "timestamps": [["冬", 100, 200], ["天", 200, 400]]
                    },
                }
            },
        })
        self.assertIn(
            '"timestamps": [["冬",100,200],["天",200,400]]',
            content,
        )
        self.assertEqual(json.loads(content)["items"]["voice.mp3"]["text"], "冬天")

    def test_local_recognizer_falls_back_from_paraformer_to_whisper(self):
        recognizer = object.__new__(LocalSpeechRecognizer)
        recognizer.primary_model = "paraformer-zh"
        recognizer.fallback_models = ["small", "base"]
        recognizer.cpu_fallback_model = "base"
        recognizer.allow_cpu_fallback = True
        recognizer.device_info = {"name": "GPU"}
        recognizer.device = "cuda:0"
        recognizer._paraformer = None
        recognizer._whisper_models = {}
        recognizer._disabled_attempts = set()
        recognizer.last_backend = None
        recognizer.last_model = None

        with patch.object(
            recognizer,
            "_transcribe_paraformer",
            side_effect=RuntimeError("CUDA out of memory"),
        ), patch.object(
            recognizer,
            "_transcribe_whisper",
            return_value=("回退识别成功", []),
        ) as whisper:
            result = recognizer.transcribe("voice.mp3")

        self.assertEqual(result.backend, "faster-whisper")
        self.assertEqual(result.model, "small")
        self.assertEqual(result.device, "cuda:0")
        whisper.assert_called_once_with("voice.mp3", "small", "zh-CN", "cuda:0")

    def test_local_recognizer_falls_back_from_small_to_base(self):
        recognizer = object.__new__(LocalSpeechRecognizer)
        recognizer.primary_model = "paraformer-zh"
        recognizer.fallback_models = ["small", "base"]
        recognizer.cpu_fallback_model = "base"
        recognizer.allow_cpu_fallback = True
        recognizer.device_info = {"name": "GPU"}
        recognizer.device = "cuda:0"
        recognizer._paraformer = None
        recognizer._whisper_models = {}
        recognizer._disabled_attempts = {
            ("paraformer", "paraformer-zh", "cuda:0")
        }
        recognizer.last_backend = None
        recognizer.last_model = None

        def whisper(_audio, model_name, _language, device):
            if device == "cpu":
                return "CPU base识别成功", []
            if model_name == "small":
                raise RuntimeError("CUDA out of memory")
            return "base识别成功", []

        with patch.object(
            recognizer,
            "_transcribe_whisper",
            side_effect=whisper,
        ):
            result = recognizer.transcribe("voice.mp3")

        self.assertEqual(result.model, "base")
        self.assertEqual(result.device, "cuda:0")
        self.assertIn(
            ("faster-whisper", "small", "cuda:0"),
            recognizer._disabled_attempts,
        )

    def test_memory_threshold_only_warns_and_never_blocks_gpu(self):
        for memory_gb in (3.0, 4.0, 6.0):
            with self.subTest(memory_gb=memory_gb):
                gpu = {
                    "name": f"NVIDIA GPU {memory_gb:.0f}GB",
                    "memory_gb": memory_gb,
                    "compute_capability": "6.1",
                }
                with patch(
                    "modules.local_asr._cuda_info_from_torch",
                    return_value=gpu,
                ):
                    self.assertEqual(detect_cuda_device(6.0), gpu)

    def test_falls_back_to_cpu_after_all_gpu_models_fail(self):
        recognizer = object.__new__(LocalSpeechRecognizer)
        recognizer.primary_model = "paraformer-zh"
        recognizer.fallback_models = ["small", "base"]
        recognizer.cpu_fallback_model = "base"
        recognizer.allow_cpu_fallback = True
        recognizer.device_info = {"name": "GPU"}
        recognizer.device = "cuda:0"
        recognizer._paraformer = None
        recognizer._whisper_models = {}
        recognizer._disabled_attempts = set()
        recognizer.last_backend = None
        recognizer.last_model = None

        def whisper(_audio, model_name, _language, device):
            if device == "cuda:0":
                raise RuntimeError("CUDA out of memory")
            return "CPU识别成功", []

        with patch.object(
            recognizer,
            "_transcribe_paraformer",
            side_effect=RuntimeError("CUDA out of memory"),
        ), patch.object(
            recognizer,
            "_transcribe_whisper",
            side_effect=whisper,
        ):
            result = recognizer.transcribe("voice.mp3")

        self.assertEqual(result.model, "base")
        self.assertEqual(result.device, "cpu")
        self.assertNotIn(
            ("faster-whisper", "base", "cpu"),
            recognizer._disabled_attempts,
        )

    def test_uses_cpu_directly_when_cuda_is_unavailable(self):
        recognizer = object.__new__(LocalSpeechRecognizer)
        recognizer.primary_model = "paraformer-zh"
        recognizer.fallback_models = ["small", "base"]
        recognizer.cpu_fallback_model = "base"
        recognizer.allow_cpu_fallback = True
        recognizer.device_info = None
        recognizer.device = "cpu"
        recognizer._paraformer = None
        recognizer._whisper_models = {}
        recognizer._disabled_attempts = set()
        recognizer.last_backend = None
        recognizer.last_model = None

        with patch.object(
            recognizer,
            "_transcribe_paraformer",
        ) as paraformer, patch.object(
            recognizer,
            "_transcribe_whisper",
            return_value=("CPU识别成功", []),
        ) as whisper:
            result = recognizer.transcribe("voice.mp3")

        paraformer.assert_not_called()
        whisper.assert_called_once_with("voice.mp3", "base", "zh-CN", "cpu")
        self.assertEqual(result.device, "cpu")

    def test_reports_when_cuda_and_cpu_fallback_are_unavailable(self):
        recognizer = object.__new__(LocalSpeechRecognizer)
        recognizer.primary_model = "paraformer-zh"
        recognizer.fallback_models = ["small", "base"]
        recognizer.cpu_fallback_model = "base"
        recognizer.allow_cpu_fallback = False
        recognizer.device_info = None
        recognizer._disabled_attempts = set()

        with self.assertRaisesRegex(RuntimeError, "CPU 回退已关闭"):
            recognizer.transcribe("voice.mp3")

    def test_reports_when_all_configured_attempts_were_disabled(self):
        recognizer = object.__new__(LocalSpeechRecognizer)
        recognizer.primary_model = "paraformer-zh"
        recognizer.fallback_models = ["small", "base"]
        recognizer.cpu_fallback_model = "base"
        recognizer.allow_cpu_fallback = True
        recognizer.device_info = None
        recognizer._disabled_attempts = {
            ("faster-whisper", "base", "cpu")
        }

        with self.assertRaisesRegex(RuntimeError, "此前均已失败"):
            recognizer.transcribe("voice.mp3")

    def test_split_uses_cached_local_timestamps_without_azure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio = self._audio_file(root, "voice.mp3")
            (root / "subtitles.json").write_text(
                json.dumps(
                    {
                        "version": 2,
                        "items": {
                            "voice.mp3": {
                                "text": "前半句，后半句",
                                "splits": {},
                                "recognition": {
                                    "timestamps": [
                                        {"text": "前", "start_ms": 0, "end_ms": 200},
                                        {"text": "半", "start_ms": 200, "end_ms": 400},
                                        {"text": "句", "start_ms": 400, "end_ms": 600},
                                        {"text": "后", "start_ms": 1000, "end_ms": 1200},
                                        {"text": "半", "start_ms": 1200, "end_ms": 1400},
                                        {"text": "句", "start_ms": 1400, "end_ms": 1600},
                                    ]
                                },
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch(
                "modules.subtitle_tools._speech_timestamp_ratio_segments"
            ) as azure_timestamps:
                segments = build_subtitle_segments(
                    root,
                    audio,
                    10,
                    20,
                    split_timing_mode="speech_timestamps",
                )

            azure_timestamps.assert_not_called()
            self.assertEqual([item["text"] for item in segments], ["前半句", "后半句"])
            self.assertLess(segments[0]["end"], segments[1]["start"])

    def test_split_reads_compact_local_timestamps(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio = self._audio_file(root, "voice.mp3")
            (root / "subtitles.json").write_text(
                json.dumps(
                    {
                        "version": 2,
                        "items": {
                            "voice.mp3": {
                                "text": "前半句，后半句",
                                "recognition": {
                                    "timestamps": [
                                        ["前", 0, 200],
                                        ["半", 200, 400],
                                        ["句", 400, 600],
                                        ["后", 1000, 1200],
                                        ["半", 1200, 1400],
                                        ["句", 1400, 1600],
                                    ]
                                },
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            segments = build_subtitle_segments(
                root,
                audio,
                0,
                10,
                split_timing_mode="speech_timestamps",
            )

            self.assertEqual([item["text"] for item in segments], ["前半句", "后半句"])


if __name__ == "__main__":
    unittest.main()
