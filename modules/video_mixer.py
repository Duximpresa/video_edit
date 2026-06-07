import os
import random
import tempfile
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from distutils.command.config import config
from pathlib import Path

from moviepy import VideoFileClip, concatenate_videoclips
from moviepy import *
from moviepy.audio.fx import AudioLoop
# from moviepy.audio.io import AudioFileClip
from datetime import datetime
from app import voice
from utils import utils
import azure.cognitiveservices.speech as speechsdk
#pip install azure-cognitiveservices-speech
# from moviepy.video import fx
import psutil
import json
from modules.subtitle_tools import (
    build_ass_ffmpeg_filter,
    burn_subtitles_to_video,
    build_subtitle_segments,
    create_ass_subtitle_file,
    ensure_ffmpeg_ass_filter,
    get_subtitle_text,
)

root_dir = utils.root_dir()
AUDIO_END_PADDING = 0.05


def resolve_config_value(value):
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.getenv(value[2:-1], "")
    return value


def scale_audio_volume(audio_clip, factor):
    return audio_clip.with_updated_frame_function(
        lambda t, get_frame=audio_clip.get_frame: get_frame(t) * factor
    )

def kill_ffmpeg_processes():
    for proc in psutil.process_iter():
        try:
            if 'ffmpeg' in proc.name().lower():
                proc.kill()
        except psutil.NoSuchProcess:
            pass

def random_clip(video_path, clip_duration, output_path):
    # 加载视频
    video = VideoFileClip(video_path)
    max_start = video.duration - clip_duration
    start_time = random.uniform(0, max_start)

    # 截取视频片段
    clip = video.subclipped(start_time, start_time + clip_duration)

    # 输出视频片段
    # clip.write_videofile(output_path, codec='libx264')
    clip.write_videofile(output_path, codec='h264_nvenc')


def generate_random_float(number, range_control):
    # Calculate the lower and upper bounds based on the range_control parameter
    lower_bound = number - range_control
    upper_bound = number + range_control

    # Generate a random float within the bounds and round it to 1 decimal place
    random_float = round(random.uniform(lower_bound, upper_bound), 1)

    return random_float

# 生成唯一文件名
def generate_datetime_string(prefix, include_milliseconds=False, task_index=None):
    # 获取当前的日期和时间
    now = datetime.now()
    # 将日期和时间格式化为字符串
    datetime_string = now.strftime("%Y-%m-%d_%H-%M-%S")
    if include_milliseconds:
        datetime_string += f"-{now.microsecond // 1000:03d}"
    if task_index is not None:
        datetime_string += f"_task-{int(task_index) + 1:03d}"
    # 返回带有前缀的日期和时间字符串
    return f"{prefix}_{datetime_string}"


def get_bgm_list_choice(BGM_folder):
    BGM_list = [f for f in os.listdir(BGM_folder) if f.lower().endswith((".mp3", ".wav"))]
    random.shuffle(BGM_list)
    random.shuffle(BGM_list)
    return random.choice(BGM_list)

def create_video_montage(folder_path, number_of_videos, clip_duration, with_audio=False):
    # 从指定文件夹获取所有视频文件
    video_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if
                   f.endswith(('.mp4', '.avi', '.mov'))]
    print('从指定文件夹获取所有视频文件')
    # 随机选择指定数量的视频文件
    selected_videos = random.sample(video_files, number_of_videos)
    print('随机选择指定数量的视频文件')

    # 存储片段的列表
    clips = []

    # 遍历每个选中的视频
    for video in selected_videos:
        # 加载视频文件
        print(f'加载视频文件:{video}')
        video_clip = VideoFileClip(video)
        # video_clip = video_clip.resized((1080, 1920))
        print(f'视频分辨率：{video_clip.size}')

        # 随机选择片段的开始时间
        print('随机选择片段的开始时间')
        number = clip_duration
        random_clip_duration = generate_random_float(number, 0.5)
        print(f'clip_duration：{random_clip_duration}')
        max_start_time = max(0, video_clip.duration - random_clip_duration)
        start_time = random.uniform(0, max_start_time)

        print(f'video_clip.duration :{video_clip.duration }')
        print(f'random_clip_duration:{random_clip_duration}')
        print(f'start_time:{start_time}')
        print(f'max_start_time:{max_start_time}')
        print(f'end_time:{start_time + random_clip_duration}')

        if video_clip.duration > random_clip_duration:
            # 创建指定长度的子片段
            print('创建指定长度的子片段')
            subclip = video_clip.subclipped(start_time, start_time + random_clip_duration)
        else:
            print('片段时长小于所需时长')
            start_time = 0
            end_time = video_clip.duration
            subclip = video_clip.subclipped(start_time, end_time)

        # 根据 with_audio 参数设置子片段的音频
        if not with_audio:
            subclip = subclip.without_audio()

        # 将子片段添加到片段列表中
        print('将子片段添加到片段列表中')
        clips.append(subclip)
        # subclip.close()
        # video_clip.close()
        # video_clip.close()

    # 随机打乱片段列表
    # print(clips)
    random.shuffle(clips)
    print('返回剪辑')
    return clips

# 一个文件夹里的素材随机抽取来混剪
def multiple_video_bgm_generation(project_name,
                                        output_folder,
                                        folder_path_list,
                                        number_of_video_list,
                                        bgm_folder_path,
                                        audio_volumex,
                                        bgm_volumex,
                                        clip_size,
                                        fps,
                                        one_clip_duration,
                                  duration_of_video_list):
    # 检查输出文件夹
    os.makedirs(output_folder, exist_ok=True)

    # 随机选择BGM
    bgm_file = get_bgm_list_choice(bgm_folder_path)
    print(bgm_file)
    bgm_file_path = os.path.join(root_dir, bgm_folder_path, bgm_file)

    # # 配音和BGM进行混音
    # audio_clip = AudioFileClip(voice_filename) * (audio_volumex)
    # bgm_clip = AudioFileClip(bgm_file_path) * (bgm_volumex)
    # composite_audio = CompositeAudioClip([audio_clip, bgm_clip])
    # all_clips_number = sum(number_of_video_list)
    # one_clip_duration = round((audio_clip.duration + 1) / all_clips_number, 1)
    # print(all_clips_number)
    # print(audio_clip.duration)
    # print(one_clip_duration)

    # 片段混剪
    clips_list = []
    for index, folder_path in enumerate(folder_path_list):
        print(folder_path)
        print(number_of_video_list[index])
        print(duration_of_video_list[index])
        clip_duration = duration_of_video_list[index]
        clip = create_video_montage(folder_path, number_of_video_list[index], clip_duration, with_audio=False)
        clips_list.append(clip)
    clips = [j for i in clips_list for j in i]

    final_clip_name = generate_datetime_string(project_name)
    print(final_clip_name)
    output_file = f'{os.path.join(output_folder, final_clip_name)}.mp4'
    print(output_file)
    print(clips)
    final_clip = concatenate_videoclips(clips)
    # final_clip.size = clip_size
    print(f'成片尺寸：{final_clip.size}')
    final_clip_duration = final_clip.duration
    print(f'视频长度：{final_clip_duration}')

    # 生成bgm片段
    bgm_clip = scale_audio_volume(AudioFileClip(bgm_file_path), bgm_volumex)
    final_clip = final_clip.with_audio(bgm_clip)
    # 因为BGM是超长的，这里截取视频长度
    final_clip = final_clip.with_duration(final_clip_duration)

    ffmpeg_params = [
        "-pix_fmt", "yuv420p",  # 强制输出 YUV 像素格式
        "-vf", "format=yuv420p", # 使用滤镜确保输入转换为 YUV
        "-colorspace", "bt709",  # 指定色彩空间为 Rec.709
        "-color_primaries", "bt709",  # 指定色彩原色
        "-color_trc", "bt709",  # 指定传递特性（gamma）
        "-color_range", "pc"  # 指定色彩范围（tv 表示有限范围，pc 表示全范围）
    ]

    # final_clip.write_videofile(output_file, audio_codec="libmp3lame", codec="libx264", bitrate="15000k", fps=fps,audio_bitrate="256k")
    # final_clip.write_videofile(output_file, audio_codec="libmp3lame", codec="h264_nvenc", bitrate="15000k", fps=fps,audio_bitrate="320k")
    final_clip.write_videofile(output_file, audio_codec="aac", codec="h264_nvenc", bitrate="19000k", fps=fps,audio_bitrate="320k", ffmpeg_params=ffmpeg_params)
    # final_clip.write_videofile(output_file, audio_codec="aac", codec="libx264", bitrate="19000k", fps=fps,audio_bitrate="320k", ffmpeg_params=ffmpeg_params)

    final_clip.close()
    del final_clip


def batch_multiple_video_bgm_generation(config_file_dir):
    # config_file_dir = 'config'
    print(f"开始在【{config_file_dir}】找配置文件")
    config_file_list = utils.find_files_by_extensions(config_file_dir, extensions=['.json'])
    for config_file in config_file_list:
        print(f'现在读取文件【{config_file}】')
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        project_name = config["project_name"]
        output_folder = config["output_folder"]
        bgm_folder_path = config["bgm_folder_path"]
        voice_folder_path = config["voice_folder_path"]
        video_folder_path = config["video_folder_path"]
        audio_volumex = config["audio_volumex"]
        bgm_volumex = config["bgm_volumex"]
        clip_size = config["clip_size"]
        fps = config["fps"]
        voice_speed = config["voice_speed"]
        voice_txt_file = config["voice_config"]["voice_txt_file"]
        voice_name = config["voice_config"]["voice_name"]
        speech_key = resolve_config_value(config["voice_config"]["speech_key"])
        service_region = config["voice_config"]["service_region"]
        number_of_video_list = config["number_of_video_list"]
        generated_quantity = config["generated_quantity"]
        one_clip_duration = config["one_clip_duration"]
        duration_of_video_list = config["duration_of_video_list"]

        folder_path_list = utils.get_sorted_absolute_subdirectories(video_folder_path)
        print(folder_path_list)

        for i in range(generated_quantity):
            # multiple_video_generation()
            multiple_video_bgm_generation(project_name=project_name,
                                      output_folder=output_folder,
                                      folder_path_list=folder_path_list,
                                      number_of_video_list=number_of_video_list,
                                      bgm_folder_path=bgm_folder_path,
                                      audio_volumex=audio_volumex,
                                      bgm_volumex=bgm_volumex,
                                      clip_size=clip_size,
                                      fps=fps,
                                    one_clip_duration=one_clip_duration,
                                    duration_of_video_list=duration_of_video_list)



def create_video_and_voice_montage(
        folder_path,
        number_of_videos,
        voice_folder_path,
        with_audio=True,
        subtitle_filename='subtitles.json',
        return_metadata=False):
    # 从指定文件夹获取所有的音频文件
    print('从指定文件夹获取所有的音频文件')
    voice_files = [os.path.join(voice_folder_path, f) for f in os.listdir(voice_folder_path) if
                   f.endswith(('.mp3', '.acc', '.m4a'))]
    # 配音的文件列表
    print(voice_files)
    # 随机选择单个的音频文件
    print('随机选择单个的音频文件')
    voice_file = random.sample(voice_files, 1)[0]
    subtitle_text = get_subtitle_text(voice_folder_path, voice_file, subtitle_filename)
    print(f'选择的配音文件{voice_file}')
    # 获取配音长度
    print('获取配音时长')
    voice_duration = AudioFileClip(voice_file).duration
    print(f'【配音时长】：{voice_duration}')
    # clip_duration = voice_duration

    # 从指定文件夹获取所有视频文件
    video_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if
                   f.endswith(('.mp4', '.avi', '.mov'))]
    print(f'video_files: {video_files}')
    print('从指定文件夹获取所有视频文件')
    # 判断要选择的视频数量
    print('判断视频数量')
    print(f'number_of_videos:{number_of_videos}')
    # 随机选择指定数量的视频文件
    selected_videos = random.sample(video_files, number_of_videos)

    clips = []

    if number_of_videos == 1:
        print(f'{"-" * 50}执行单文件模式{"-" * 50}')
        subclips = []
        clip_duration = voice_duration
        # 存储片段的列表
        selected_videos = random.sample(video_files, number_of_videos)
        video = selected_videos[0]
        # 加载视频文件
        print(f'加载视频文件:{video}')
        video_clip = VideoFileClip(video)
        # video_clip = video_clip.resized((1080, 1920))
        print(f'视频分辨率：{video_clip.size}')

        # 随机选择片段的开始时间
        print('随机选择片段的开始时间')
        # number = clip_duration
        # random_clip_duration = generate_random_float(number, 0.5)
        print(f'clip_duration：{clip_duration}')
        max_start_time = max(0, video_clip.duration - clip_duration)
        start_time = random.uniform(0, max_start_time)

        # 创建指定长度的子片段
        print('创建指定长度的子片段')
        end_time = min(video_clip.duration, start_time + clip_duration)
        subclip = video_clip.subclipped(start_time, end_time)
        # 添加配音
        print(f'添加配音：{voice_file}')
        # audio_clip = AudioFileClip(voice_file).write_audiofile(f'output/test_{voice_file[-10:]}.mp3')
        audio_clip = AudioFileClip(voice_file)
        safe_audio_duration = max(0, audio_clip.duration - AUDIO_END_PADDING)
        audio_clip = audio_clip.subclipped(0, safe_audio_duration)
        subclip = subclip.without_audio()
        subclip = subclip.with_audio(audio_clip)
        subclip = subclip.with_duration(safe_audio_duration)
        # audio_clip.write_audiofile(f'output/test_{voice_file[-10:]}.mp3')
        print(f'音频时长{audio_clip.duration}')
        print(f'视频时长{subclip.duration}')

        # 根据 with_audio 参数设置子片段的音频
        # if not with_audio:
        #     subclip = subclip.without_audio()

        # 将子片段添加到片段列表中
        # subclip.write_videofile(f'output/test_{voice_file[-10:]}.mp4', audio_codec="libmp3lame", codec="libx264", bitrate="25000k", fps=60, audio_bitrate="320k", threads=28, audio=True)
        print('将子片段添加到片段列表中')
        subclips.append(subclip)
        subclip_all = concatenate_videoclips(subclips)
        clips.append(subclip_all)
        testname = f'output/{os.path.basename(voice_file).split('.')[0]}.mp4'
        print(testname)
        # subclip.write_videofile(testname, audio_codec="libmp3lame", codec="libx264", bitrate="25000k", fps=60, audio_bitrate="320k", threads=28, audio=True)
        # subclip_all.write_videofile(testname, audio_codec="libmp3lame", codec="libx264", bitrate="25000k", fps=60, audio_bitrate="320k", threads=28, audio=True)



        # clips.append(subclip)
        # subclip.close()
        # subclip_all.close()
        # del subclip
        # del subclip_all
        # kill_ffmpeg_processes()
        # subclip.close()
        # video_clip.close()
        # video_clip.close()
    else:
        print(f'{"-" * 50}执行多片段模式{"-" * 50}')
        # 存储片段的列表
        selected_videos = random.sample(video_files, number_of_videos)
        # 计算每个分片段的长度
        clip_duration = voice_duration / number_of_videos
        subclips = []
        for video in selected_videos:
            # 加载视频文件
            print(f'加载视频文件:{video}')
            video_clip = VideoFileClip(video)
            # video_clip = video_clip.resized((1080, 1920))
            print(f'视频分辨率：{video_clip.size}')

            # 随机选择片段的开始时间
            print('随机选择片段的开始时间')
            # number = clip_duration
            # random_clip_duration = generate_random_float(number, 0.5)
            print(f'clip_duration：{clip_duration}')
            max_start_time = max(0, video_clip.duration - clip_duration)
            start_time = random.uniform(0, max_start_time)

            # 创建指定长度的子片段
            print('创建指定长度的子片段')
            end_time = min(video_clip.duration, start_time + clip_duration)
            subclip = video_clip.subclipped(start_time, end_time)
            # 加入子片段列表
            subclips.append(subclip)
            # Keep clip handles alive until final render; closing here can
            # break downstream audio/video reads during write_videofile.
            # kill_ffmpeg_processes()
        # 添加配音
        print(f'添加配音：{voice_file}')
        # audio_clip = AudioFileClip(voice_file).write_audiofile(f'output/test_{voice_file[-10:]}.mp3')
        audio_clip = AudioFileClip(voice_file)
        safe_audio_duration = max(0, audio_clip.duration - AUDIO_END_PADDING)
        audio_clip = audio_clip.subclipped(0, safe_audio_duration)
        # 合并剪辑
        subclip_all = concatenate_videoclips(subclips)
        # 去除源音频
        subclip_all = subclip_all.without_audio()
        # 加入配音
        subclip_all = subclip_all.with_audio(audio_clip)
        subclip_all = subclip_all.with_duration(safe_audio_duration)
        # audio_clip.write_audiofile(f'output/test_{voice_file[-10:]}.mp3')
        print(f'音频时长{audio_clip.duration}')
        print(f'视频时长{subclip_all.duration}')

        # 将子片段添加到片段列表中
        # subclip_all.write_videofile(f'output/test_{voice_file[-10:]}.mp4', audio_codec="libmp3lame", codec="libx264", bitrate="25000k", fps=60, audio_bitrate="320k", threads=28, audio=True)
        print('将子片段添加到片段列表中')
        clips.append(subclip_all)
        # subclip.close()
        # video_clip.close()
        # video_clip.close()

    # 随机打乱片段列表
    # print(clips)
    # random.shuffle(clips)
    print('返回剪辑')
    if return_metadata:
        return {
            "clips": clips,
            "voice_file": voice_file,
            "subtitle_text": subtitle_text,
        }
    return clips


def multiple_video_voice_bgm_generation(project_name,
                              output_folder,
                              folder_path_list,
                              number_of_video_list,
                              bgm_folder_path,
                              audio_volumex,
                              bgm_volumex,
                              clip_size,
                              fps,
                              voice_folder_path_list,
                              subtitle_enabled=True,
                              subtitle_filename='subtitles.json',
                              subtitle_style=None,
                              split_on_comma=True,
                              split_timing_mode="character_ratio",
                              speech_key=None,
                              service_region=None,
                              subtitle_render_mode="legacy_opencv",
                              task_index=0,
                              random_seed=None,
                              parallel_mode=False):
    started_at = time.perf_counter()
    timings = {
        "material_prepare": 0.0,
        "audio_mix": 0.0,
        "video_render": 0.0,
        "subtitle_render": 0.0,
        "total": 0.0,
    }
    if random_seed is not None:
        random.seed(random_seed)
    if subtitle_render_mode not in {"legacy_opencv", "single_pass_ass"}:
        raise ValueError(f"不支持的字幕渲染模式：{subtitle_render_mode}")

    os.makedirs(output_folder, exist_ok=True)

    #选择配音文件
    # voice_filename=voice_path_list[0]
    # 随机选择BGM
    bgm_file = get_bgm_list_choice(bgm_folder_path)
    print(f'选择的BGM为：【{bgm_file}】')
    bgm_file_path = os.path.join(root_dir, bgm_folder_path, bgm_file)

    # 配音和BGM进行混音
    # audio_clip = AudioFileClip(voice_filename) * (audio_volumex)
    # bgm_clip = AudioFileClip(bgm_file_path) * (bgm_volumex)

    # 片段混剪
    clips_list = []
    subtitle_segments = []
    subtitle_cursor = 0
    for index, folder_path in enumerate(folder_path_list):
        print(f'【配音文件夹】：{voice_folder_path_list[index]}')
        print(f'【视频文件夹】：{folder_path}')
        print(f'【视频数量】：{number_of_video_list[index]}')
        # voice_file = voice_path_list[index]

        # voice_duration = AudioFileClip(voice_path_list[index]).duration
        # print(f'【配音时长】：{voice_duration}')
        # clip_duration = voice_duration
        voice_folder_path = voice_folder_path_list[index]
        montage = create_video_and_voice_montage(
            folder_path,
            number_of_video_list[index],
            voice_folder_path,
            with_audio=True,
            subtitle_filename=subtitle_filename,
            return_metadata=True,
        )
        clip = montage["clips"]
        for item in clip:
            segment_start = subtitle_cursor
            segment_end = subtitle_cursor + item.duration
            subtitle_segments.extend(build_subtitle_segments(
                voice_folder_path,
                montage["voice_file"],
                segment_start,
                segment_end,
                filename=subtitle_filename,
                split_on_comma=split_on_comma,
                split_timing_mode=split_timing_mode,
                speech_key=speech_key,
                service_region=service_region,
            ))
            subtitle_cursor += item.duration
        print(f'成功返回剪辑{clip}')
        clips_list.append(clip)
        print(f'加入剪辑列表')
        print(clips_list)
        print(len(clips_list))
    clips = [j for i in clips_list for j in i]
    for a in clips:
        print(a)
    final_clip_name = generate_datetime_string(
        project_name,
        include_milliseconds=parallel_mode,
        task_index=task_index if parallel_mode else None,
    )
    print(final_clip_name)
    output_file = f'{os.path.join(output_folder, final_clip_name)}.mp4'
    print(output_file)

    final_clip = concatenate_videoclips(clips)
    final_clip = final_clip.resized((clip_size[0], clip_size[1]))
    print(f'成片尺寸：{final_clip.size}')
    final_clip_duration = final_clip.duration
    print(f'视频长度：{final_clip_duration}')
    timings["material_prepare"] = time.perf_counter() - started_at
    # print(f'音频长度：{audio_clip.duration}')
    # final_clip.write_videofile(output_file, audio_codec="libmp3lame", codec="h264_nvenc", bitrate="20000k", fps=fps,audio_bitrate="320k")

    audio_mix_started = time.perf_counter()
    audio_clip = scale_audio_volume(final_clip.audio, audio_volumex)
    # audio_clip = final_clip.audio
    print(audio_clip.duration)
    print(final_clip.duration)
    # audio_clip.write_audiofile(f'output/test_测试.mp3')

    # audio_clip = AudioFileClip(final_clip) * (audio_volumex)
    bgm_clip = scale_audio_volume(AudioFileClip(bgm_file_path), bgm_volumex)

    bgm_clip = bgm_clip.with_effects([AudioLoop(duration=final_clip_duration)])
    bgm_clip = bgm_clip.with_start(0)

    composite_audio = CompositeAudioClip([audio_clip, bgm_clip])
    final_clip = final_clip.with_audio(composite_audio)
    timings["audio_mix"] = time.perf_counter() - audio_mix_started
    print(final_clip)
    print(f'最终成片尺寸：{final_clip.size}')

    video_filter = "format=yuv420p"
    temp_prefix = f"video-edit-task-{int(task_index) + 1:03d}-"
    try:
        with tempfile.TemporaryDirectory(prefix=temp_prefix) as temp_dir:
            if (
                subtitle_enabled
                and subtitle_render_mode == "single_pass_ass"
                and subtitle_segments
            ):
                subtitle_started = time.perf_counter()
                ensure_ffmpeg_ass_filter()
                ass_result = create_ass_subtitle_file(
                    subtitle_segments,
                    subtitle_style,
                    clip_size,
                    Path(temp_dir) / "subtitles.ass",
                )
                if ass_result["event_count"] <= 0:
                    raise RuntimeError("ASS 字幕没有可渲染的有效事件")
                video_filter = build_ass_ffmpeg_filter(
                    ass_result["path"],
                    Path(ass_result["font_path"]).parent,
                )
                timings["subtitle_render"] = (
                    time.perf_counter() - subtitle_started
                )

            ffmpeg_params = [
                "-pix_fmt", "yuv420p",
                "-vf", video_filter,
                "-colorspace", "bt709",
                "-color_primaries", "bt709",
                "-color_trc", "bt709",
                "-color_range", "pc",
            ]

            render_started = time.perf_counter()
            final_clip.write_videofile(
                output_file,
                audio_codec="aac",
                codec="h264_nvenc",
                bitrate="18000k",
                fps=fps,
                audio_bitrate="256k",
                temp_audiofile=str(Path(temp_dir) / "moviepy-audio.mp4"),
                remove_temp=True,
                ffmpeg_params=ffmpeg_params,
            )
            timings["video_render"] = time.perf_counter() - render_started
    finally:
        final_clip.close()

    if subtitle_enabled and subtitle_render_mode == "legacy_opencv":
        subtitle_started = time.perf_counter()
        burn_subtitles_to_video(
            output_file,
            subtitle_segments,
            style=subtitle_style,
        )
        timings["subtitle_render"] = time.perf_counter() - subtitle_started
    if not parallel_mode:
        kill_ffmpeg_processes()

    timings["total"] = time.perf_counter() - started_at
    result = {
        "task_index": task_index,
        "status": "success",
        "output_file": output_file,
        "seed": random_seed,
        "subtitle_render_mode": subtitle_render_mode,
        "timings": timings,
        "error": None,
    }
    print(f"任务完成：{json.dumps(result, ensure_ascii=False)}")
    return result


def _render_video_task(task):
    task_index = int(task["task_index"])
    random_seed = int(task["seed"])
    started_at = time.perf_counter()
    try:
        return multiple_video_voice_bgm_generation(
            **task["generation_kwargs"],
            task_index=task_index,
            random_seed=random_seed,
            parallel_mode=bool(task.get("parallel_mode", False)),
        )
    except Exception as exc:
        error = "".join(
            traceback.format_exception_only(type(exc), exc)
        ).strip()
        result = {
            "task_index": task_index,
            "status": "failed",
            "output_file": None,
            "seed": random_seed,
            "subtitle_render_mode": task["generation_kwargs"].get(
                "subtitle_render_mode",
                "legacy_opencv",
            ),
            "timings": {
                "material_prepare": 0.0,
                "audio_mix": 0.0,
                "video_render": 0.0,
                "subtitle_render": 0.0,
                "total": time.perf_counter() - started_at,
            },
            "error": error,
        }
        print(f"任务失败：{json.dumps(result, ensure_ascii=False)}")
        return result


def _failed_task_result(task, error):
    return {
        "task_index": int(task["task_index"]),
        "status": "failed",
        "output_file": None,
        "seed": int(task["seed"]),
        "subtitle_render_mode": task["generation_kwargs"].get(
            "subtitle_render_mode",
            "legacy_opencv",
        ),
        "timings": {
            "material_prepare": 0.0,
            "audio_mix": 0.0,
            "video_render": 0.0,
            "subtitle_render": 0.0,
            "total": 0.0,
        },
        "error": str(error),
    }


def _subtitle_style_from_config(config, subtitle_config):
    field_defaults = {
        "font": None,
        "font_path": None,
        "font_size": 67,
        "letter_spacing": 0,
        "color": "#FFDE00",
        "opacity": 1.0,
        "stroke_enabled": True,
        "stroke_color": "#000000",
        "stroke_opacity": 1.0,
        "stroke_width": 5,
        "vertical_percent": 12,
        "max_width_percent": 86,
    }
    return {
        field: subtitle_config.get(
            field,
            config.get(f"subtitle_{field}", default),
        )
        for field, default in field_defaults.items()
    }


def _generation_kwargs_from_config(config):
    subtitle_config = config.get("subtitle_config", {})
    subtitle_render_mode = subtitle_config.get(
        "render_mode",
        "legacy_opencv",
    )
    if subtitle_render_mode not in {"legacy_opencv", "single_pass_ass"}:
        raise ValueError(
            f"subtitle_config.render_mode 无效：{subtitle_render_mode}"
        )

    return {
        "project_name": config["project_name"],
        "output_folder": config["output_folder"],
        "folder_path_list": utils.get_sorted_absolute_subdirectories(
            config["video_folder_path"]
        ),
        "number_of_video_list": config["number_of_video_list"],
        "bgm_folder_path": config["bgm_folder_path"],
        "audio_volumex": config["audio_volumex"],
        "bgm_volumex": config["bgm_volumex"],
        "clip_size": config["clip_size"],
        "fps": config["fps"],
        "voice_folder_path_list": utils.get_sorted_absolute_subdirectories(
            config["voice_folder_path"]
        ),
        "subtitle_enabled": subtitle_config.get(
            "enabled",
            config.get("subtitle_enabled", True),
        ),
        "subtitle_filename": subtitle_config.get(
            "filename",
            config.get("subtitle_filename", "subtitles.json"),
        ),
        "subtitle_style": _subtitle_style_from_config(
            config,
            subtitle_config,
        ),
        "split_on_comma": subtitle_config.get(
            "split_on_comma",
            config.get("subtitle_split_on_comma", True),
        ),
        "split_timing_mode": subtitle_config.get(
            "split_timing_mode",
            config.get("subtitle_split_timing_mode", "character_ratio"),
        ),
        "speech_key": resolve_config_value(
            config.get("voice_config", {}).get("speech_key", "")
        ),
        "service_region": config.get("voice_config", {}).get(
            "service_region"
        ),
        "subtitle_render_mode": subtitle_render_mode,
    }


def _print_batch_summary(results):
    ordered = sorted(results, key=lambda item: item["task_index"])
    succeeded = [item for item in ordered if item["status"] == "success"]
    failed = [item for item in ordered if item["status"] == "failed"]
    print(
        f"批量任务完成：成功 {len(succeeded)} 条，失败 {len(failed)} 条"
    )
    for item in succeeded:
        print(f"- 成功 task-{item['task_index'] + 1:03d}: {item['output_file']}")
    for item in failed:
        print(f"- 失败 task-{item['task_index'] + 1:03d}: {item['error']}")
    return ordered


def batch_multiple_video_voice_bgm_generation(config_file_dir):
    # config_file_dir = 'config'
    config_file_list = utils.find_files_by_extensions(config_file_dir, extensions=['.json'])
    all_results = []
    for config_file in config_file_list:
        print(f'现在读取文件【{config_file}】')
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        generated_quantity = config["generated_quantity"]
        batch_render = config.get("batch_render", {})
        execution_mode = batch_render.get("execution_mode", "serial")
        if execution_mode not in {"serial", "parallel"}:
            raise ValueError(
                f"batch_render.execution_mode 无效：{execution_mode}"
            )
        max_workers = int(batch_render.get("max_workers", 2))
        if max_workers < 1:
            raise ValueError("batch_render.max_workers 必须大于等于 1")
        if batch_render.get("continue_on_error", True) is not True:
            raise ValueError(
                "当前版本 batch_render.continue_on_error 必须为 true"
            )

        generation_kwargs = _generation_kwargs_from_config(config)
        print(
            f"voice_folder_path_list:"
            f"{generation_kwargs['voice_folder_path_list']}"
        )
        print(f'总共制作视频：{generated_quantity}条')
        base_seed = int(
            batch_render.get(
                "base_seed",
                random.SystemRandom().randrange(1, 2**31),
            )
        )
        print(f"本次批量随机种子：{base_seed}")
        tasks = [
            {
                "task_index": index,
                "seed": base_seed + index,
                "parallel_mode": execution_mode == "parallel",
                "generation_kwargs": generation_kwargs,
            }
            for index in range(generated_quantity)
        ]

        if execution_mode == "parallel":
            print(f"启用进程并发：max_workers={max_workers}")
            results = []
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(_render_video_task, task): task
                    for task in tasks
                }
                for future in as_completed(futures):
                    task = futures[future]
                    try:
                        results.append(future.result())
                    except Exception as exc:
                        results.append(_failed_task_result(task, exc))
        else:
            results = [_render_video_task(task) for task in tasks]

        all_results.extend(_print_batch_summary(results))
    return all_results



def main():
    config_file_dir = os.path.join(root_dir, 'config/蛇厂')
    batch_multiple_video_bgm_generation(config_file_dir)

if __name__ == '__main__':
    main()
