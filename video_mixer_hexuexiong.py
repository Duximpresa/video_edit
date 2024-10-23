import os
import random
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


# random_float = generate_random_float(3, 2)
# print(random_float)
# 输入视频路径、片段长度（秒）、输出文件名
# random_clip('2023_12_26_15_57_IMG_2995.mp4', random_float, 'output1.mp4')


# 从指定文件夹中的视频中随机挑选片段，然后合成一个新视频的函数
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
def create_video_and_voice_montage(folder_path, number_of_videos, voice_file, with_audio=True):
    # 获取配音长度

    print('获取配音时长')
    voice_duration = AudioFileClip(voice_file).duration
    print(f'【配音时长】：{voice_duration}')
    # clip_duration = voice_duration


    # 从指定文件夹获取所有视频文件
    video_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if
                   f.endswith(('.mp4', '.avi', '.mov'))]
    print('从指定文件夹获取所有视频文件')
    # 判断要选择的视频数量
    print('判断视频数量')
    # 随机选择指定数量的视频文件
    selected_videos = random.sample(video_files, number_of_videos)

    clips = []

    if number_of_videos == 1:
        print(f'{"-"*50}执行单文件模式{"-"*50}')
        clip_duration = voice_duration
        # 存储片段的列表
        selected_videos = random.sample(video_files, number_of_videos)
        video = selected_videos[0]
        # 加载视频文件
        print(f'加载视频文件:{video}')
        video_clip = VideoFileClip(video)
        # video_clip = video_clip.resize((1080, 1920))
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
        subclip = video_clip.subclip(start_time, start_time + clip_duration + 0.2)
        # 添加配音
        print(f'添加配音：{voice_file}')
        # audio_clip = AudioFileClip(voice_file).write_audiofile(f'output/test_{voice_file[-10:]}.mp3')
        audio_clip = AudioFileClip(voice_file)
        subclip = subclip.without_audio()
        subclip = subclip.set_audio(audio_clip)
        # audio_clip.write_audiofile(f'output/test_{voice_file[-10:]}.mp3')
        print(f'音频时长{audio_clip.duration}')
        print(f'视频时长{subclip.duration}')

        # 根据 with_audio 参数设置子片段的音频
        # if not with_audio:
        #     subclip = subclip.without_audio()

        # 将子片段添加到片段列表中
        # subclip.write_videofile(f'output/test_{voice_file[-10:]}.mp4', audio_codec="libmp3lame", codec="libx264", bitrate="25000k", fps=60, audio_bitrate="320k", threads=28, audio=True)
        print('将子片段添加到片段列表中')
        clips.append(subclip)
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
            # video_clip = video_clip.resize((1080, 1920))
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
            subclip = video_clip.subclip(start_time, start_time + clip_duration + 0.1)
            # 加入子片段列表
            subclips.append(subclip)
        # 添加配音
        print(f'添加配音：{voice_file}')
        # audio_clip = AudioFileClip(voice_file).write_audiofile(f'output/test_{voice_file[-10:]}.mp3')
        audio_clip = AudioFileClip(voice_file)
        # 合并剪辑
        subclip_all = concatenate_videoclips(subclips)
        # 去除源音频
        subclip_all = subclip_all.without_audio()
        # 加入配音
        subclip_all = subclip_all.set_audio(audio_clip)
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
    return clips


def video_generator(clips, output_file, with_audio=True):
    # 连接所有片段以创建最终视频
    final_clip = concatenate_videoclips(clips)
    # final_clip.size = [2160, 3840]
    print(f'成片尺寸：{final_clip.size}')
    # final_clip = clips

    # 将结果写入输出文件
    # final_clip.write_videofile(output_file, audio_codec='aac' if with_audio else None)
    # final_clip.write_videofile(output_file, audio_codec=None,  codec="libx264", bitrate="20000k")
    final_clip.write_videofile(output_file, audio_codec=None, codec="h264_nvenc", bitrate="35000k")
    final_clip.close()


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


def multiple_video_generation():
    # 总参数设置
    project_name = '赫学熊混剪_秋季长袖'
    output_folder = 'output\\赫学熊\\赫学熊混剪\\1022'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 输入文件夹，按类型分好
    folder_path_list = ['input/赫学熊/2024-08-29 仓库']

    # 每个文件夹选几个视频
    number_of_video_01 = 8
    # number_of_video_02 = 8
    # number_of_video_03 = 1

    # 每个片段截取多少秒
    clip_duration = 3
    clip_duration_01 = 3
    # clip_duration_02 = 3
    # clip_duration_03 = 2

    # 片段截取
    print(f'片段1 素材开始拼接')
    clip_01 = create_video_montage(folder_path_list[0], number_of_video_01, clip_duration_01, with_audio=False)
    print(f'片段1 素材拼接完毕')
    # print(f'片段2 素材开始拼接')
    # clip_02 = create_video_montage(folder_path_list[1], number_of_video_02, clip_duration_02, with_audio=False)
    # print(f'片段2 素材拼接完毕')
    # print(f'片段3 素材开始拼接')
    # clip_03 = create_video_montage(folder_path_list[2], number_of_video_03, clip_duration_03, with_audio=False)
    # print(f'片段3 素材拼接完毕')

    # 拼合片段列表
    print(f'剪辑素材合并')
    # clips = clip_01 + clip_02 + clip_03
    clips = clip_01
    # clips = clip_01 + clip_02

    # 合并片段，生成视频
    print(f'剪辑生成')
    video_name = generate_datetime_string(project_name)
    print(f'【视频名称】：{video_name}')
    output_file = f'{os.path.join(output_folder, video_name)}.mp4'
    print(f'【视频文件名】：{output_file}')
    print(f'{"-" * 50}视频渲染开始{"-" * 50}')
    video_generator(clips, output_file, with_audio=False)
    print(f'{"-" * 50}{video_name}生成完毕{"-" * 50}')


def multiple_video_voice_bgm_generation(project_name,
                                        output_folder,
                                        folder_path_list,
                                        number_of_video_list,
                                        voice_txt_file,
                                        voice_name,
                                        speech_config,
                                        bgm_folder_path,
                                        audio_volumex,
                                        bgm_volumex,
                                        clip_size,
                                        fps,
                                        voice_speed):
    # 检查输出文件夹
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 生成配音
    voice_filename = voice.text2speech(voice_txt_file, voice_name, project_name, speech_config, voice_speed=voice_speed)

    # 随机选择BGM
    bgm_file = get_bgm_list_choice(bgm_folder_path)
    print(bgm_file)
    bgm_file_path = os.path.join(root_dir, bgm_folder_path, bgm_file)

    # 配音和BGM进行混音
    audio_clip = AudioFileClip(voice_filename).volumex(audio_volumex)
    bgm_clip = AudioFileClip(bgm_file_path).volumex(bgm_volumex)
    # bgm_clip = afx.audio_loop(bgm_clip, duration=audio_clip.duration)
    # bgm_clip = bgm_clip.set_start(0)
    composite_audio = CompositeAudioClip([audio_clip, bgm_clip])
    # composite_audio.write_audiofile('test.mp3', codec='libmp3lame', fps=audio_clip.fps)
    # final_clip_duration = audio_clip.duration

    all_clips_number = sum(number_of_video_list)
    one_clip_duration = round((audio_clip.duration + 1) / all_clips_number, 1)
    print(all_clips_number)
    print(audio_clip.duration)
    print(one_clip_duration)

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
    final_clip.size = clip_size
    print(f'成片尺寸：{final_clip.size}')
    final_clip_duration = final_clip.duration
    print(f'视频长度：{final_clip_duration}')
    print(f'音频长度：{audio_clip.duration}')

    if final_clip_duration > audio_clip.duration:
        bgm_clip = afx.audio_loop(bgm_clip, duration=final_clip_duration)
        bgm_clip = bgm_clip.set_start(0)
        composite_audio = CompositeAudioClip([audio_clip, bgm_clip])
        final_clip = final_clip.set_audio(composite_audio)
        final_clip.write_videofile(output_file, audio_codec="libmp3lame", codec="h264_nvenc", bitrate="20000k", fps=fps, audio_bitrate="320k")
        # final_clip.write_videofile(output_file, audio_codec=None, codec="h264_nvenc", bitrate="20000k", fps=fps, audio_bitrate="320k")
    else:
        print('音频长度不够')

    final_clip.close()
    del final_clip

    # 片段截取
    # clip_01 = create_video_montage(folder_path_list[0], number_of_video_01, clip_duration_01, with_audio=False)

    # 合并片段，生成视频
    # video_name = generate_datetime_string(project_name)
    # print(video_name)
    # output_file = f'{os.path.join(output_folder, video_name)}.mp4'
    # print(output_file)
    # video_generator(clips, output_file, with_audio=False)

def hexuexiong_multiple_video(project_name,
                                        output_folder,
                                        folder_path_list,
                                        number_of_video_list,
                                        voice_txt_file,
                                        voice_name,
                                        speech_config,
                                        bgm_folder_path,
                                        audio_volumex,
                                        bgm_volumex,
                                        clip_size,
                                        fps,
                                        voice_speed,
                                        voice_path_list):

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    #选择配音文件
    # voice_filename=voice_path_list[0]
    # 随机选择BGM
    bgm_file = get_bgm_list_choice(bgm_folder_path)
    print(f'选择的BGM为：【{bgm_file}】')
    bgm_file_path = os.path.join(root_dir, bgm_folder_path, bgm_file)

    # 配音和BGM进行混音
    # audio_clip = AudioFileClip(voice_filename).volumex(audio_volumex)
    # bgm_clip = AudioFileClip(bgm_file_path).volumex(bgm_volumex)


    # 片段混剪
    clips_list = []
    for index, folder_path in enumerate(folder_path_list):
        print(f'【配音文件】：{voice_path_list[index]}')
        print(f'【视频文件夹】：{folder_path}')
        print(f'【视频数量】：{number_of_video_list[index]}')
        voice_file = voice_path_list[index]

        # voice_duration = AudioFileClip(voice_path_list[index]).duration
        # print(f'【配音时长】：{voice_duration}')
        # clip_duration = voice_duration

        clip = create_video_and_voice_montage(folder_path, number_of_video_list[index], voice_file, with_audio=True)
        print(f'成功返回剪辑{clip}')
        clips_list.append(clip)
        print(f'加入剪辑列表')
        print(clips_list)
        print(len(clips_list))
    clips = [j for i in clips_list for j in i]
    final_clip_name = generate_datetime_string(project_name)
    print(final_clip_name)
    output_file = f'{os.path.join(output_folder, final_clip_name)}.mp4'
    print(output_file)

    final_clip = concatenate_videoclips(clips)
    # final_clip.size = clip_size
    # print(f'成片尺寸：{final_clip.size}')
    final_clip_duration = final_clip.duration
    print(f'视频长度：{final_clip_duration}')
    # print(f'音频长度：{audio_clip.duration}')
    # final_clip.write_videofile(output_file, audio_codec="libmp3lame", codec="h264_nvenc", bitrate="20000k", fps=fps,audio_bitrate="320k")

    audio_clip = final_clip.audio.volumex(audio_volumex)

    # audio_clip = AudioFileClip(final_clip).volumex(audio_volumex)
    bgm_clip = AudioFileClip(bgm_file_path).volumex(bgm_volumex)

    bgm_clip = afx.audio_loop(bgm_clip, duration=final_clip_duration)
    bgm_clip = bgm_clip.set_start(0)


    composite_audio = CompositeAudioClip([audio_clip, bgm_clip])
    final_clip = final_clip.set_audio(composite_audio)

    final_clip.write_videofile(output_file, audio_codec="libmp3lame", codec="libx264", bitrate="25000k", fps=fps, audio_bitrate="320k", threads=64)
    # final_clip.write_videofile(output_file, audio_codec="libmp3lame", codec="h264_nvenc", bitrate="25000k", fps=fps, audio_bitrate="320k", threads=8)

    final_clip.close()
    del final_clip


def main():
    project_name = '赫学熊混剪_秋季长袖'
    output_folder = 'output\\赫学熊混剪\\秋季长袖\\1023'
    bgm_folder_path = 'BGM/赫学熊'
    voice_folder_path = 'input/赫学熊/秋季长袖/2024_10_20/Audio'
    audio_volumex = 3
    bgm_volumex = 0.6
    clip_size = [1080, 1920]
    fps = 60
    voice_speed = '20%'

    # 配音部分参数
    voice_txt_file = f'{root_dir}/input/Voice_Text/摆地摊.txt'
    voice_name = "zh-CN-XiaoxiaoMultilingualNeural"
    speech_key = "8b7335e4c1cf4708a48453f878a6c802"
    service_region = "southeastasia"
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff44100Hz16BitMonoPcm)

    # 输入文件夹，按类型分好
    folder_path_list = ['input/赫学熊/秋季长袖/2024_10_20/秋季长袖_01_开头',
                        'input/赫学熊/秋季长袖/2024_10_20/秋季长袖_02_中间_寒暄',
                        'input/赫学熊/秋季长袖/2024_10_20/秋季长袖_03_中间_面料',
                        'input/赫学熊/秋季长袖/2024_10_20/秋季长袖_04_中间_衣领',
                        'input/赫学熊/秋季长袖/2024_10_20/秋季长袖_05_中间_反光条_1',
                        'input/赫学熊/秋季长袖/2024_10_20/秋季长袖_05_中间_反光条_2',
                        'input/赫学熊/秋季长袖/2024_10_20/秋季长袖_06_中间_透气性',
                        'input/赫学熊/秋季长袖/2024_10_20/秋季长袖_07_结尾']
    # voice_path_list = [f for f in os.listdir(voice_folder_path) if f.lower().endswith((".mp3", ".wav"))]
    voice_path_list = [os.path.join(voice_folder_path, f) for f in os.listdir(voice_folder_path) if f.endswith(('.MP3', '.wav'))]
    print(voice_path_list)
    # voice_path_list = ['input/赫学熊/秋季长袖/2024_10_20/Audio/秋季长袖_01_开头.MP3',
    #                     'input/赫学熊/秋季长袖/2024_10_20/Audio/秋季长袖_02_中间_寒暄.MP3',
    #                     'input/赫学熊/秋季长袖/2024_10_20/Audio/秋季长袖_03_中间_面料.MP3',
    #                     'input/赫学熊/秋季长袖/2024_10_20/Audio/秋季长袖_04_中间_衣领.MP3',
    #                    'input/赫学熊/秋季长袖/2024_10_20/Audio/秋季长袖_05_中间_反光条_1.MP3',
    #                    'input/赫学熊/秋季长袖/2024_10_20/Audio/秋季长袖_05_中间_反光条_2.MP3',
    #                    'input/赫学熊/秋季长袖/2024_10_20/Audio/秋季长袖_06_中间_透气性.MP3',
    #                    'input/赫学熊/秋季长袖/2024_10_20/Audio/秋季长袖_07_结尾.MP3']

    number_of_video_dict = {'number_of_video_1': 1,
                            'number_of_video_2': 1,
                            'number_of_video_3': 1,
                            'number_of_video_4': 1,
                            'number_of_video_5': 1,
                            'number_of_video_6': 1,
                            'number_of_video_7': 1,
                            'number_of_video_8': 1}
    number_of_video_list = [1, 1, 2, 2, 2, 2, 1, 1]
    generated_quantity = 5
    for i in range(generated_quantity):
        # multiple_video_generation()
        hexuexiong_multiple_video(project_name=project_name,
                                            output_folder=output_folder,
                                            folder_path_list=folder_path_list,
                                            number_of_video_list=number_of_video_list,
                                            voice_txt_file=voice_txt_file,
                                            voice_name=voice_name,
                                            speech_config=speech_config,
                                            bgm_folder_path=bgm_folder_path,
                                            audio_volumex=audio_volumex,
                                            bgm_volumex=bgm_volumex,
                                            clip_size=clip_size,
                                            fps=fps,
                                            voice_speed=voice_speed,
                                            voice_path_list=voice_path_list)

def main2():
    audio_volumex = 3
    bgm_volumex = 0.2

    bgm_folder_path = 'BGM'
    bgm_file = get_bgm_list_choice(bgm_folder_path)
    print(bgm_file)
    bgm_file_path = os.path.join(root_dir, bgm_folder_path, bgm_file)
    voice_filename = 'storage/Voices/测试项目_fabdf1707ce6133379d73e94ba529f52650ba0378fdaed2b6eb0e8cefde052b7.wav'
    audio_clip = AudioFileClip(voice_filename).volumex(audio_volumex)
    bgm_clip = AudioFileClip(bgm_file_path).volumex(bgm_volumex)
    bgm_clip = afx.audio_loop(bgm_clip, duration=audio_clip.duration)
    bgm_clip = bgm_clip.set_start(0)
    # composite_audio = CompositeAudioClip([audio_clip, bgm_clip])
    # composite_audio.write_audiofile('test.mp3', codec='libmp3lame', fps=audio_clip.fps)
    final_clip_duration = audio_clip.duration
    print(final_clip_duration)

def main3():
    generated_quantity = 5
    for i in range(generated_quantity):
        multiple_video_generation()


if __name__ == '__main__':
    main()
