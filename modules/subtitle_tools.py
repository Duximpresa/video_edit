import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:  # pragma: no cover - handled at runtime by generator.
    speechsdk = None


AUDIO_EXTENSIONS = (".mp3", ".aac", ".acc", ".m4a", ".wav")
DEFAULT_SUBTITLE_FILE = "subtitles.json"
TRAILING_SUBTITLE_PUNCTUATION = "。."
SUBTITLE_SPLIT_SEPARATORS = re.compile(r"[，,]")
VALID_SPLIT_TIMING_MODES = {"character_ratio", "speech_timestamps"}


def load_subtitle_map(audio_folder, filename=DEFAULT_SUBTITLE_FILE):
    subtitle_file = Path(audio_folder) / filename
    if not subtitle_file.exists():
        return {}

    with subtitle_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and isinstance(data.get("items"), dict):
        return data["items"]

    # Allow a plain {filename: text} file for quick manual edits.
    if isinstance(data, dict):
        return data

    return {}


def _subtitle_file_path(audio_folder, filename=DEFAULT_SUBTITLE_FILE):
    return Path(audio_folder) / filename


def _load_subtitle_payload(audio_folder, filename=DEFAULT_SUBTITLE_FILE):
    subtitle_file = _subtitle_file_path(audio_folder, filename)
    if not subtitle_file.exists():
        return {"version": 2, "items": {}}

    with subtitle_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and isinstance(data.get("items"), dict):
        return data

    if isinstance(data, dict):
        return {"version": 2, "items": data}

    return {"version": 2, "items": {}}


def _write_json_safely(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            prefix=f"{path.stem}_",
            dir=path.parent,
            delete=False,
        ) as temp_file:
            json.dump(payload, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
            temp_path = Path(temp_file.name)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _normalize_subtitle_item(item):
    if isinstance(item, dict):
        text = str(item.get("text", "") or "").strip()
        splits = item.get("splits", {})
        if not isinstance(splits, dict):
            splits = {}
        return {"text": text, "splits": splits}

    return {"text": str(item or "").strip(), "splits": {}}


def get_subtitle_text(audio_folder, audio_file, filename=DEFAULT_SUBTITLE_FILE):
    subtitles = load_subtitle_map(audio_folder, filename)
    audio_name = os.path.basename(audio_file)
    text = normalize_subtitle_text(_normalize_subtitle_item(subtitles.get(audio_name, "")).get("text", ""))
    if not text:
        print(f"字幕提示：未找到【{audio_name}】对应字幕，将跳过该段字幕")
    return text


def normalize_subtitle_text(text):
    text = str(text or "").strip()
    return text.rstrip(TRAILING_SUBTITLE_PUNCTUATION).strip()


def _visible_length(text):
    return len("".join(str(text or "").split()))


def _split_text_by_comma(text):
    return [
        part.strip()
        for part in SUBTITLE_SPLIT_SEPARATORS.split(normalize_subtitle_text(text))
        if part.strip()
    ]


def _ratio_segments_from_parts(parts):
    total = sum(_visible_length(part) for part in parts)
    if total <= 0:
        return []

    cursor = 0.0
    segments = []
    for index, part in enumerate(parts):
        if index == len(parts) - 1:
            end_ratio = 1.0
        else:
            end_ratio = cursor + (_visible_length(part) / total)
        segments.append({
            "text": part,
            "start_ratio": cursor,
            "end_ratio": end_ratio,
        })
        cursor = end_ratio
    return segments


def _clean_for_alignment(text):
    return re.sub(r"\s+", "", str(text or ""))


def _ticks_to_seconds(value):
    return float(value or 0) / 10_000_000


def _extract_word_offsets(result):
    json_result = result.properties.get_property(
        speechsdk.PropertyId.SpeechServiceResponse_JsonResult
    )
    if not json_result:
        return []

    data = json.loads(json_result)
    words = (((data.get("NBest") or [{}])[0]).get("Words") or [])
    offsets = []
    for word in words:
        text = word.get("Word") or word.get("DisplayText") or ""
        text = _clean_for_alignment(text)
        if not text:
            continue
        start = _ticks_to_seconds(word.get("Offset"))
        end = start + _ticks_to_seconds(word.get("Duration"))
        offsets.append({"text": text, "start": start, "end": end})
    return offsets


def _transcribe_word_offsets(audio_path, speech_key, service_region, language="zh-CN"):
    if speechsdk is None:
        raise RuntimeError("缺少 azure-cognitiveservices-speech，请先安装依赖")
    if not speech_key or not service_region:
        raise RuntimeError("缺少 Azure Speech 配置，无法获取语音级时间戳")

    wav_path = _convert_audio_to_temp_wav(audio_path)
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_recognition_language = language
    speech_config.output_format = speechsdk.OutputFormat.Detailed
    if hasattr(speech_config, "request_word_level_timestamps"):
        speech_config.request_word_level_timestamps()
    else:
        speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps,
            "true",
        )

    audio_config = None
    recognizer = None
    try:
        audio_config = speechsdk.audio.AudioConfig(filename=str(wav_path))
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )
        result = recognizer.recognize_once_async().get()
        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            raise RuntimeError(f"语音时间戳识别失败：{result.reason}")
        return _extract_word_offsets(result)
    finally:
        if recognizer is not None:
            del recognizer
        if audio_config is not None:
            del audio_config
        _safe_unlink(wav_path)


def _speech_timestamp_ratio_segments(audio_path, full_text, parts, speech_key, service_region):
    word_offsets = _transcribe_word_offsets(audio_path, speech_key, service_region)
    if not word_offsets:
        raise RuntimeError("Azure 未返回词级时间戳")

    recognized_text = "".join(item["text"] for item in word_offsets)
    audio_start = word_offsets[0]["start"]
    audio_end = word_offsets[-1]["end"]
    audio_duration = max(audio_end - audio_start, 0)
    if audio_duration <= 0:
        raise RuntimeError("语音时间戳时长无效")

    segments = []
    search_start = 0
    for index, part in enumerate(parts):
        target = _clean_for_alignment(part)
        if not target:
            continue

        char_start = recognized_text.find(target, search_start)
        if char_start < 0:
            raise RuntimeError(f"语音时间戳无法匹配字幕片段：{part}")
        char_end = char_start + len(target)
        search_start = char_end

        cursor = 0
        matched_words = []
        for word in word_offsets:
            word_start = cursor
            word_end = cursor + len(word["text"])
            cursor = word_end
            if word_end <= char_start:
                continue
            if word_start >= char_end:
                break
            matched_words.append(word)

        if not matched_words:
            raise RuntimeError(f"语音时间戳未找到字幕片段对应词：{part}")

        start_ratio = (matched_words[0]["start"] - audio_start) / audio_duration
        end_ratio = (matched_words[-1]["end"] - audio_start) / audio_duration
        segments.append({
            "text": part,
            "start_ratio": _clamp(start_ratio, 0, 1),
            "end_ratio": _clamp(end_ratio, 0, 1),
        })

    if len(segments) != len(parts):
        raise RuntimeError("语音时间戳分段数量不一致")

    segments[0]["start_ratio"] = 0.0
    segments[-1]["end_ratio"] = 1.0
    for index in range(1, len(segments)):
        if segments[index]["start_ratio"] < segments[index - 1]["end_ratio"]:
            segments[index]["start_ratio"] = segments[index - 1]["end_ratio"]
    return segments


def _valid_cached_segments(cached_segments, parts):
    if not isinstance(cached_segments, list) or len(cached_segments) != len(parts):
        return False
    for cached, part in zip(cached_segments, parts):
        if not isinstance(cached, dict):
            return False
        if normalize_subtitle_text(cached.get("text", "")) != normalize_subtitle_text(part):
            return False
        if "start_ratio" not in cached or "end_ratio" not in cached:
            return False
    return True


def _write_split_cache(audio_folder, filename, audio_name, item, mode, segments):
    payload = _load_subtitle_payload(audio_folder, filename)
    items = payload.setdefault("items", {})
    current = _normalize_subtitle_item(items.get(audio_name, item))
    current["text"] = item["text"]
    current.setdefault("splits", {})[mode] = segments
    items[audio_name] = current
    payload["version"] = max(int(payload.get("version", 1) or 1), 2)

    subtitle_file = _subtitle_file_path(audio_folder, filename)
    with subtitle_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _map_ratios_to_timeline(start, end, ratio_segments):
    duration = max(0, end - start)
    timeline_segments = []
    for index, segment in enumerate(ratio_segments):
        segment_start = start + duration * float(segment.get("start_ratio", 0))
        if index == len(ratio_segments) - 1:
            segment_end = end
        else:
            segment_end = start + duration * float(segment.get("end_ratio", 1))
        if segment.get("text") and segment_end > segment_start:
            timeline_segments.append({
                "start": segment_start,
                "end": segment_end,
                "text": segment["text"],
            })
    return timeline_segments


def build_subtitle_segments(
    audio_folder,
    audio_file,
    start,
    end,
    filename=DEFAULT_SUBTITLE_FILE,
    split_on_comma=True,
    split_timing_mode="character_ratio",
    speech_key=None,
    service_region=None,
):
    payload = _load_subtitle_payload(audio_folder, filename)
    items = payload.get("items", {})
    audio_name = os.path.basename(audio_file)
    item = _normalize_subtitle_item(items.get(audio_name, ""))
    text = normalize_subtitle_text(item["text"])
    if not text:
        print(f"字幕提示：未找到【{audio_name}】对应字幕，将跳过该段字幕")
        return []

    if not split_on_comma:
        return [{"start": start, "end": end, "text": text}]

    parts = _split_text_by_comma(text)
    if len(parts) <= 1:
        return [{"start": start, "end": end, "text": text}]

    mode = split_timing_mode if split_timing_mode in VALID_SPLIT_TIMING_MODES else "character_ratio"
    cached = item.get("splits", {}).get(mode)
    if _valid_cached_segments(cached, parts):
        return _map_ratios_to_timeline(start, end, cached)

    actual_mode = mode
    try:
        if mode == "speech_timestamps":
            ratio_segments = _speech_timestamp_ratio_segments(
                audio_file,
                text,
                parts,
                speech_key,
                service_region,
            )
        else:
            ratio_segments = _ratio_segments_from_parts(parts)
    except Exception as exc:
        print(f"字幕提示：语音级分段失败，改用字数比例分段。【{audio_name}】{exc}")
        actual_mode = "character_ratio"
        ratio_segments = _ratio_segments_from_parts(parts)

    if not ratio_segments:
        return [{"start": start, "end": end, "text": text}]

    _write_split_cache(audio_folder, filename, audio_name, item, actual_mode, ratio_segments)
    return _map_ratios_to_timeline(start, end, ratio_segments)


def transcribe_audio_file(audio_path, speech_key, service_region, language="zh-CN"):
    if speechsdk is None:
        raise RuntimeError("缺少 azure-cognitiveservices-speech，请先安装依赖")

    wav_path = _convert_audio_to_temp_wav(audio_path)
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_recognition_language = language
    audio_config = None
    recognizer = None
    try:
        audio_config = speechsdk.audio.AudioConfig(filename=str(wav_path))
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )
        result = recognizer.recognize_once_async().get()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text.strip()

        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation = speechsdk.CancellationDetails(result)
            print(f"转写失败：{audio_path}，原因：{cancellation.reason}，详情：{cancellation.error_details}")
        else:
            print(f"转写失败：{audio_path}，原因：{result.reason}")
    finally:
        if recognizer is not None:
            del recognizer
        if audio_config is not None:
            del audio_config
        _safe_unlink(wav_path)

    return ""


def _safe_unlink(path, retries=5, delay=0.2):
    for _ in range(retries):
        try:
            if path.exists():
                path.unlink()
            return
        except PermissionError:
            time.sleep(delay)
    print(f"临时文件仍被占用，稍后可手动删除：{path}")


def _convert_audio_to_temp_wav(audio_path):
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        ffmpeg = get_ffmpeg_exe()
    except Exception:
        ffmpeg = "ffmpeg"

    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_path = Path(temp_file.name)
    temp_file.close()

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(audio_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(temp_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return temp_path


def generate_subtitle_maps(
    voice_root,
    speech_key,
    service_region,
    subtitle_filename=DEFAULT_SUBTITLE_FILE,
    overwrite=False,
    language="zh-CN",
    return_report=False,
):
    voice_root = Path(voice_root)
    if not voice_root.exists():
        raise FileNotFoundError(f"音频根目录不存在：{voice_root}")
    if not voice_root.is_dir():
        raise NotADirectoryError(f"音频根路径不是文件夹：{voice_root}")

    audio_folders = []
    for folder in [voice_root, *sorted(path for path in voice_root.rglob("*") if path.is_dir())]:
        if any(
            path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
            for path in folder.iterdir()
        ):
            audio_folders.append(folder)

    written_files = []
    failed_files = []
    recognized_count = 0
    skipped_count = 0
    for audio_folder in audio_folders:
        audio_files = [
            p for p in sorted(audio_folder.iterdir())
            if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
        ]

        subtitle_path = audio_folder / subtitle_filename
        payload = _load_subtitle_payload(audio_folder, subtitle_filename)
        items = payload.setdefault("items", {})
        changed = not subtitle_path.exists()

        print(f"开始生成字幕映射：{audio_folder}")
        for audio_file in audio_files:
            existing_item = items.get(audio_file.name)
            existing_text = _normalize_subtitle_item(existing_item)["text"]
            if not overwrite and existing_text:
                print(f"跳过已有字幕：{audio_file.name}")
                skipped_count += 1
                continue

            if not speech_key or not service_region:
                raise RuntimeError(
                    "存在需要转写的音频，但缺少 Azure Speech 配置。"
                    "请设置 AZURE_SPEECH_KEY 环境变量，并确认配置文件中的 "
                    "service_region 正确。"
                )

            print(f"转写音频：{audio_file.name}")
            try:
                text = transcribe_audio_file(
                    audio_file,
                    speech_key,
                    service_region,
                    language=language,
                )
            except Exception as exc:
                text = ""
                print(f"转写异常：{audio_file}，原因：{exc}")

            text = str(text or "").strip()
            if text:
                recognized_count += 1
            else:
                failed_files.append(str(audio_file))

            if isinstance(existing_item, dict):
                updated_item = dict(existing_item)
                updated_item["text"] = text
                updated_item.pop("splits", None)
                items[audio_file.name] = updated_item
                payload["version"] = max(int(payload.get("version", 1) or 1), 2)
            else:
                items[audio_file.name] = text
            changed = True

        if changed:
            _write_json_safely(subtitle_path, payload)
            written_files.append(str(subtitle_path))
            print(f"已写入字幕映射：{subtitle_path}")
        else:
            print(f"字幕映射无需更新：{subtitle_path}")

    report = {
        "voice_root": str(voice_root),
        "audio_folder_count": len(audio_folders),
        "audio_file_count": recognized_count + skipped_count + len(failed_files),
        "recognized_count": recognized_count,
        "skipped_count": skipped_count,
        "failed_count": len(failed_files),
        "failed_files": failed_files,
        "written_files": written_files,
    }
    print(
        "字幕映射处理完成："
        f"文件夹 {report['audio_folder_count']} 个，"
        f"识别成功 {recognized_count} 个，"
        f"跳过 {skipped_count} 个，"
        f"失败 {len(failed_files)} 个"
    )
    if failed_files:
        print("以下音频未识别出文字，可稍后重新运行或手工补充：")
        for failed_file in failed_files:
            print(f"- {failed_file}")

    return report if return_report else written_files


def _find_font(font_name=None):
    repo_root = Path(__file__).resolve().parents[1]
    font_dir = repo_root / "font"
    font_name = font_name or "SourceHanSansSC-Bold.otf"

    candidate = Path(font_name)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)

    candidates = [font_dir / font_name]
    if candidate.name != font_name:
        candidates.append(font_dir / candidate.name)

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    available_fonts = ", ".join(sorted(p.name for p in font_dir.glob("*") if p.is_file()))
    raise FileNotFoundError(f"未找到字幕字体：{font_name}。请使用 font 文件夹中的字体：{available_fonts}")


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _parse_color(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("#") and len(value) == 7:
            return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return tuple(int(_clamp(int(v), 0, 255)) for v in value[:3])
    return default


def _rgba(color, opacity):
    opacity = float(_clamp(float(opacity), 0, 1))
    return (*color, int(round(opacity * 255)))


def _line_width(text, draw, font, letter_spacing=0):
    chars = list(str(text))
    if not chars:
        return 0
    width = sum(draw.textlength(char, font=font) for char in chars)
    width += max(0, len(chars) - 1) * letter_spacing
    return width


def _wrap_text(text, draw, font, max_width, letter_spacing=0):
    lines = []
    for source_line in str(text).splitlines() or [""]:
        current = ""
        for char in source_line:
            trial = current + char
            if _line_width(trial, draw, font, letter_spacing) <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
    return "\n".join(lines)


def _spaced_text_block_size(lines, draw, font, stroke_width, letter_spacing, line_spacing):
    widths = [_line_width(line, draw, font, letter_spacing) for line in lines]
    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line or " ", font=font, stroke_width=stroke_width)
        heights.append(bbox[3] - bbox[1])
    total_height = sum(heights) + max(0, len(lines) - 1) * line_spacing
    return (max(widths) if widths else 0), total_height, heights


def _draw_spaced_multiline_text(
    draw,
    position,
    lines,
    font,
    fill,
    stroke_width,
    stroke_fill,
    letter_spacing,
    line_spacing,
    max_width,
):
    x, y = position
    current_y = y
    for line in lines:
        line_width = _line_width(line, draw, font, letter_spacing)
        current_x = x + (max_width - line_width) / 2
        bbox = draw.textbbox((0, 0), line or " ", font=font, stroke_width=stroke_width)
        line_height = bbox[3] - bbox[1]
        for char in line:
            draw.text(
                (current_x, current_y),
                char,
                fill=fill,
                font=font,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
            current_x += draw.textlength(char, font=font) + letter_spacing
        current_y += line_height + line_spacing


def _active_subtitle_text(subtitle_segments, time_seconds):
    for item in subtitle_segments:
        if item["start"] <= time_seconds < item["end"]:
            return item.get("text", "")
    return ""


def _mux_original_audio(video_only_path, original_video_path, output_path, video_codec="h264_nvenc", video_bitrate="18000k"):
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        ffmpeg = get_ffmpeg_exe()
    except Exception:
        ffmpeg = "ffmpeg"

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_only_path),
        "-i",
        str(original_video_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        "-c:v",
        video_codec,
        "-b:v",
        video_bitrate,
        "-c:a",
        "copy",
        "-shortest",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        fallback_cmd = cmd.copy()
        fallback_cmd[fallback_cmd.index(video_codec)] = "libx264"
        subprocess.run(fallback_cmd, check=True)


def burn_subtitles_to_video(input_video_path, subtitle_segments, output_video_path=None, style=None):
    subtitle_segments = [
        item for item in subtitle_segments
        if item.get("text") and item.get("end", 0) > item.get("start", 0)
    ]
    if not subtitle_segments:
        print("字幕提示：没有可烧录的字幕，保留原视频")
        return input_video_path

    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
        from tqdm import tqdm
    except ImportError as exc:
        raise RuntimeError(
            "缺少字幕烧录依赖，请先执行：pip install opencv-python pillow numpy tqdm"
        ) from exc

    style = style or {}
    input_video_path = Path(input_video_path)
    output_video_path = Path(output_video_path or input_video_path)
    tmp_video = output_video_path.with_name(output_video_path.stem + "_subtitle_video_tmp.mp4")
    tmp_output = output_video_path.with_name(output_video_path.stem + "_subtitle_mux_tmp.mp4")

    cap = cv2.VideoCapture(str(input_video_path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频文件：{input_video_path}")

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(tmp_video), fourcc, fps, (frame_width, frame_height))
    if not out.isOpened():
        cap.release()
        raise RuntimeError(f"无法创建字幕临时视频：{tmp_video}")

    font_size = int(style.get("font_size", max(42, frame_height * 0.035)))
    font_path = _find_font(style.get("font") or style.get("font_path"))
    font = ImageFont.truetype(font_path, font_size)
    max_width_percent = float(_clamp(float(style.get("max_width_percent", 86)), 1, 100))
    max_text_width = int(frame_width * max_width_percent / 100)
    fill = _rgba(_parse_color(style.get("color", style.get("fill")), (255, 222, 0)), style.get("opacity", 1.0))
    stroke_enabled = bool(style.get("stroke_enabled", True))
    stroke_fill = _rgba(
        _parse_color(style.get("stroke_color", style.get("stroke_fill")), (0, 0, 0)),
        style.get("stroke_opacity", 1.0),
    )
    stroke_width = int(style.get("stroke_width", 4)) if stroke_enabled else 0
    vertical_percent = float(_clamp(float(style.get("vertical_percent", 12)), 0, 100))
    letter_spacing = float(style.get("letter_spacing", 0))
    line_spacing = max(0, int(font_size * 0.18))

    with tqdm(total=total_frames, desc="Burning subtitles") as pbar:
        frame_index = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            text = _active_subtitle_text(subtitle_segments, frame_index / fps)
            if text:
                frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
                text_layer = Image.new("RGBA", frame_pil.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(text_layer)
                wrapped_text = _wrap_text(text, draw, font, max_text_width, letter_spacing)
                lines = wrapped_text.splitlines()
                text_width, text_height, _ = _spaced_text_block_size(
                    lines,
                    draw,
                    font,
                    stroke_width,
                    letter_spacing,
                    line_spacing,
                )
                x = (frame_width - text_width) // 2
                y = int((100 - vertical_percent) / 100 * (frame_height - text_height))

                _draw_spaced_multiline_text(
                    draw,
                    (x, y),
                    lines,
                    font,
                    fill,
                    stroke_width,
                    stroke_fill,
                    letter_spacing,
                    line_spacing,
                    text_width,
                )
                frame_pil = Image.alpha_composite(frame_pil, text_layer).convert("RGB")
                frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)

            out.write(frame)
            frame_index += 1
            pbar.update(1)

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    _mux_original_audio(tmp_video, input_video_path, tmp_output)
    os.replace(tmp_output, output_video_path)
    if tmp_video.exists():
        tmp_video.unlink()

    print(f"字幕已内嵌到视频：{output_video_path}")
    return str(output_video_path)
