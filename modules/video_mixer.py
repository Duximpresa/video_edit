import os
import random
from distutils.command.config import config

from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.editor import *
# from moviepy.audio.io import AudioFileClip
from datetime import datetime
from app import voice
from utils import utils
import azure.cognitiveservices.speech as speechsdk
#pip install azure-cognitiveservices-speech
# from moviepy.video import fx
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process
import psutil
import json

root_dir = utils.root_dir()

def random_clip(video_path, clip_duration, output_path):
    # 加载视频
    video = VideoFileClip(video_path)
    max_start = video.duration - clip_duration
    start_time = random.uniform(0, max_start)

    # 截取视频片段
    clip = video.subclip(start_time, start_time + clip_duration)

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
def generate_datetime_string(prefix):
    # 获取当前的日期和时间
    now = datetime.now()
    # 将日期和时间格式化为字符串
    datetime_string = now.strftime("%Y-%m-%d_%H-%M-%S")
    # 返回带有前缀的日期和时间字符串
    return f"{prefix}_{datetime_string}"


def get_bgm_list_choice(BGM_folder):
    BGM_list = [f for f in os.listdir(BGM_folder) if f.lower().endswith((".mp3", ".wav"))]
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
        # video_clip = video_clip.resize((1080, 1920))
        print(f'视频分辨率：{video_clip.size}')

        # 随机选择片段的开始时间
        print('随机选择片段的开始时间')
        number = clip_duration
        random_clip_duration = generate_random_float(number, 0.5)
        print(f'clip_duration：{random_clip_duration}')
        max_start_time = max(0, video_clip.duration - random_clip_duration)
        start_time = random.uniform(0, max_start_time)

        # 创建指定长度的子片段
        print('创建指定长度的子片段')
        subclip = video_clip.subclip(start_time, start_time + random_clip_duration)

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
                                        one_clip_duration):
    # 检查输出文件夹
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 随机选择BGM
    bgm_file = get_bgm_list_choice(bgm_folder_path)
    print(bgm_file)
    bgm_file_path = os.path.join(root_dir, bgm_folder_path, bgm_file)

    # # 配音和BGM进行混音
    # audio_clip = AudioFileClip(voice_filename).volumex(audio_volumex)
    # bgm_clip = AudioFileClip(bgm_file_path).volumex(bgm_volumex)
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
        clip = create_video_montage(folder_path, number_of_video_list[index], one_clip_duration, with_audio=False)
        clips_list.append(clip)
    clips = [j for i in clips_list for j in i]

    final_clip_name = generate_datetime_string(project_name)
    print(final_clip_name)
    output_file = f'{os.path.join(output_folder, final_clip_name)}.mp4'
    print(output_file)

    final_clip = concatenate_videoclips(clips)
    # final_clip.size = clip_size
    print(f'成片尺寸：{final_clip.size}')
    final_clip_duration = final_clip.duration
    print(f'视频长度：{final_clip_duration}')

    # 生成bgm片段
    bgm_clip = AudioFileClip(bgm_file_path).volumex(bgm_volumex)
    final_clip = final_clip.set_audio(bgm_clip)
    # 因为BGM是超长的，这里截取视频长度
    final_clip = final_clip.set_duration(final_clip_duration)

    # final_clip.write_videofile(output_file, audio_codec="libmp3lame", codec="libx264", bitrate="20000k", fps=fps,audio_bitrate="320k")
    final_clip.write_videofile(output_file, audio_codec="libmp3lame", codec="h264_nvenc", bitrate="15000k", fps=fps,audio_bitrate="320k")

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
        speech_key = config["voice_config"]["speech_key"]
        service_region = config["voice_config"]["service_region"]
        number_of_video_list = config["number_of_video_list"]
        generated_quantity = config["generated_quantity"]
        one_clip_duration = config["one_clip_duration"]

        folder_path_list = utils.get_sorted_absolute_subdirectories(video_folder_path)

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
                                        one_clip_duration=one_clip_duration)

def main():
    config_file_dir = os.path.join(root_dir, 'config/蛇厂')
    batch_multiple_video_bgm_generation(config_file_dir)

if __name__ == '__main__':
    main()
