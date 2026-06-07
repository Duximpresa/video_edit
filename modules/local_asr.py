import gc
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


MINIMUM_CUDA_MEMORY_GB = 6.0
_DOWNLOAD_PROGRESS_CONFIGURED = None
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class TranscriptionResult:
    text: str
    backend: str
    model: str
    device: str
    elapsed_seconds: float
    timestamps: list[dict] = field(default_factory=list)

    def to_dict(self):
        return {
            "backend": self.backend,
            "model": self.model,
            "device": self.device,
            "elapsed_seconds": self.elapsed_seconds,
            "timestamps": [
                [item["text"], item["start_ms"], item["end_ms"]]
                for item in self.timestamps
            ],
        }


def _expand_path(value):
    value = os.path.expandvars(os.path.expanduser(str(value)))
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _cuda_info_from_torch():
    try:
        import torch
    except ImportError:
        return None

    if not torch.cuda.is_available():
        return None
    properties = torch.cuda.get_device_properties(0)
    return {
        "name": properties.name,
        "memory_gb": properties.total_memory / (1024**3),
        "compute_capability": f"{properties.major}.{properties.minor}",
    }


def _cuda_info_from_nvidia_smi():
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,compute_cap",
        "--format=csv,noheader,nounits",
        "--id=0",
    ]
    try:
        output = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        name, memory_mb, compute_capability = [part.strip() for part in output.split(",", 2)]
        return {
            "name": name,
            "memory_gb": float(memory_mb) / 1024,
            "compute_capability": compute_capability,
        }
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
        return None


def detect_cuda_device(minimum_memory_gb=MINIMUM_CUDA_MEMORY_GB):
    info = _cuda_info_from_torch() or _cuda_info_from_nvidia_smi()
    if info is None:
        raise RuntimeError("未检测到可用的 NVIDIA CUDA 显卡，本地识别未启用 CPU 回退")
    if info["memory_gb"] < minimum_memory_gb:
        raise RuntimeError(
            f"显卡显存只有 {info['memory_gb']:.1f}GB，"
            f"最低要求为 {minimum_memory_gb:.1f}GB（GTX 1060 6GB）"
        )
    return info


def _is_memory_error(exc):
    message = str(exc).lower()
    return any(
        marker in message
        for marker in ("out of memory", "cuda error", "cublas", "cudnn", "memory")
    )


def _should_disable_attempt(exc):
    message = str(exc).lower()
    return _is_memory_error(exc) or any(
        marker in message
        for marker in (
            "运行库不可用",
            "不是 cuda",
            "no module named",
            "failed to load",
            "model is not found",
        )
    )


def _clean_text(text):
    return str(text or "").strip()


def _compact_chinese_spacing(text):
    text = _clean_text(text)
    cjk = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
    text = re.sub(rf"(?<=[{cjk}])\s+", "", text)
    text = re.sub(rf"\s+(?=[{cjk}])", "", text)
    return text


def _configure_download_progress(mode="auto"):
    global _DOWNLOAD_PROGRESS_CONFIGURED

    mode = str(mode or "auto").lower()
    if mode not in {"auto", "show", "quiet"}:
        raise ValueError("download_progress 只支持 auto、show、quiet")

    show_progress = mode == "show" or (
        mode == "auto" and (sys.stdout.isatty() or sys.stderr.isatty())
    )
    if show_progress:
        os.environ.pop("TQDM_DISABLE", None)
        return
    if _DOWNLOAD_PROGRESS_CONFIGURED == "quiet":
        return

    os.environ["TQDM_DISABLE"] = "1"
    try:
        import tqdm.auto

        original_tqdm = tqdm.auto.tqdm

        def quiet_tqdm(*args, **kwargs):
            kwargs["disable"] = True
            return original_tqdm(*args, **kwargs)

        tqdm.auto.tqdm = quiet_tqdm
    except ImportError:
        pass
    _DOWNLOAD_PROGRESS_CONFIGURED = "quiet"
    print("模型文件正在后台下载，当前控制台不支持单行刷新，已隐藏高频下载进度")


def _normalize_paraformer_timestamps(text, timestamps):
    if not isinstance(timestamps, list):
        return []

    punctuation = set("，。！？、；：,.!?;:（）()【】[]“”\"'")
    visible_chars = [
        char for char in text
        if not char.isspace() and char not in punctuation
    ]
    normalized = []
    for index, item in enumerate(timestamps):
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        token = visible_chars[index] if index < len(visible_chars) else ""
        normalized.append({
            "text": token,
            "start_ms": int(item[0]),
            "end_ms": int(item[1]),
        })
    return normalized


class LocalSpeechRecognizer:
    def __init__(self, config=None):
        config = dict(config or {})
        self.primary_model = config.get("primary_model", "paraformer-zh")
        self.punctuation_model = config.get("punctuation_model", "ct-punc")
        self.fallback_models = list(config.get("fallback_models", ["small", "base"]))
        self.hotwords = config.get("hotwords", [])
        self.fallback_hotwords = config.get("fallback_hotwords", [])
        self.convert_to_simplified = bool(config.get("convert_to_simplified", True))
        self.download_progress = config.get("download_progress", "auto")
        self.minimum_memory_gb = float(
            config.get("minimum_cuda_memory_gb", MINIMUM_CUDA_MEMORY_GB)
        )
        self.cache_dir = _expand_path(
            config.get(
                "model_cache_dir",
                r"models\asr",
            )
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"本地语音模型目录：{self.cache_dir}")
        self.device_info = detect_cuda_device(self.minimum_memory_gb)
        self.device = "cuda:0"
        self._paraformer = None
        self._whisper_models = {}
        self._disabled_attempts = set()
        self.last_backend = None
        self.last_model = None

        print(
            "本地语音识别设备："
            f"{self.device_info['name']}，"
            f"显存 {self.device_info['memory_gb']:.1f}GB，"
            f"Compute Capability {self.device_info['compute_capability']}"
        )

    def _load_paraformer(self):
        if self._paraformer is not None:
            return self._paraformer
        _configure_download_progress(self.download_progress)
        try:
            import torch
            from funasr import AutoModel
        except (ImportError, OSError) as exc:
            raise RuntimeError(f"Paraformer 运行库不可用：{exc}") from exc
        if not torch.cuda.is_available():
            raise RuntimeError(
                "当前 PyTorch 不是 CUDA 版本，请安装 requirements-local-asr.txt"
            )

        self._paraformer = AutoModel(
            model=self.primary_model,
            punc_model=self.punctuation_model or None,
            device=self.device,
            disable_update=True,
            cache_dir=str(self.cache_dir / "funasr"),
        )
        return self._paraformer

    def _transcribe_paraformer(self, audio_path):
        model = self._load_paraformer()
        hotword = " ".join(self.hotwords) if isinstance(self.hotwords, list) else self.hotwords
        result = model.generate(
            input=str(audio_path),
            batch_size=1,
            hotword=hotword or None,
        )
        if not result:
            raise RuntimeError("Paraformer 未返回识别结果")

        item = result[0]
        text = _compact_chinese_spacing(item.get("text"))
        if not text:
            raise RuntimeError("Paraformer 未识别出文字")
        timestamps = _normalize_paraformer_timestamps(text, item.get("timestamp"))
        return text, timestamps

    def _load_whisper(self, model_name):
        if model_name in self._whisper_models:
            return self._whisper_models[model_name]
        _configure_download_progress(self.download_progress)
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("缺少 faster-whisper，请先安装本地识别依赖") from exc

        model = WhisperModel(
            model_name,
            device="cuda",
            compute_type="int8",
            download_root=str(self.cache_dir / "faster-whisper"),
        )
        self._whisper_models[model_name] = model
        return model

    def _transcribe_whisper(self, audio_path, model_name, language):
        model = self._load_whisper(model_name)
        language_code = "zh" if str(language).lower().startswith("zh") else language
        hotword_prompt = (
            "品牌名称可能包括：" + "、".join(self.fallback_hotwords)
            if isinstance(self.fallback_hotwords, list) and self.fallback_hotwords
            else str(self.fallback_hotwords or "")
        )
        segments, _ = model.transcribe(
            str(audio_path),
            language=language_code,
            beam_size=5,
            vad_filter=True,
            word_timestamps=True,
            initial_prompt=hotword_prompt or None,
            condition_on_previous_text=False,
        )

        text_parts = []
        timestamps = []
        for segment in segments:
            text_parts.append(segment.text)
            for word in segment.words or []:
                timestamps.append({
                    "text": _clean_text(word.word),
                    "start_ms": int(round(word.start * 1000)),
                    "end_ms": int(round(word.end * 1000)),
                })
        text = _clean_text("".join(text_parts))
        if self.convert_to_simplified and language_code == "zh":
            try:
                from opencc import OpenCC

                converter = OpenCC("t2s")
                text = converter.convert(text)
                for item in timestamps:
                    item["text"] = converter.convert(item["text"])
            except ImportError:
                pass
        if not text:
            raise RuntimeError(f"faster-whisper {model_name} 未识别出文字")
        return text, timestamps

    def _release_cuda_memory(self):
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def transcribe(self, audio_path, language="zh-CN"):
        attempts = [("paraformer", self.primary_model), *[
            ("faster-whisper", model_name) for model_name in self.fallback_models
        ]]
        attempts = [
            attempt for attempt in attempts if attempt not in self._disabled_attempts
        ]
        failures = []

        for backend, model_name in attempts:
            started_at = time.perf_counter()
            try:
                if backend == "paraformer":
                    text, timestamps = self._transcribe_paraformer(audio_path)
                else:
                    text, timestamps = self._transcribe_whisper(
                        audio_path,
                        model_name,
                        language,
                    )
                result = TranscriptionResult(
                    text=text,
                    backend=backend,
                    model=model_name,
                    device=self.device,
                    elapsed_seconds=round(time.perf_counter() - started_at, 3),
                    timestamps=timestamps,
                )
                self.last_backend = backend
                self.last_model = model_name
                print(
                    f"本地识别成功：{Path(audio_path).name}，"
                    f"模型 {backend}/{model_name}，"
                    f"耗时 {result.elapsed_seconds:.3f}s"
                )
                return result
            except Exception as exc:
                failures.append(f"{backend}/{model_name}: {exc}")
                if _should_disable_attempt(exc):
                    self._disabled_attempts.add((backend, model_name))
                print(f"本地识别模型失败，尝试下一级：{failures[-1]}")
                if backend == "paraformer":
                    self._paraformer = None
                else:
                    self._whisper_models.pop(model_name, None)
                self._release_cuda_memory()

        raise RuntimeError("所有本地识别模型均失败；" + "；".join(failures))
