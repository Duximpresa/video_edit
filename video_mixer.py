import os
import random
from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.editor import *
# from moviepy.audio.io import AudioFileClip
from datetime import datetime
from app import voice
from utils import utils
import azure.cognitiveservices.speech as speechsdk

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

    # 随机选择指定数量的视频文件
    selected_videos = random.sample(video_files, number_of_videos)

    # 存储片段的列表
    clips = []

    # 遍历每个选中的视频
    for video in selected_videos:
        # 加载视频文件
        video_clip = VideoFileClip(video)
        video_clip = video_clip.resize((1080, 1920))
        print(video_clip.size)

        # 随机选择片段的开始时间
        number = clip_duration
        random_clip_duration = generate_random_float(number, 1)
        print(f'clip_duration：{random_clip_duration}')
        max_start_time = max(0, video_clip.duration - random_clip_duration)
        start_time = random.uniform(0, max_start_time)

        # 创建指定长度的子片段
        subclip = video_clip.subclip(start_time, start_time + random_clip_duration)

        # 根据 with_audio 参数设置子片段的音频
        if not with_audio:
            subclip = subclip.without_audio()

        # 将子片段添加到片段列表中
        clips.append(subclip)
        # subclip.close()
        # video_clip.close()
        # video_clip.close()

    # 随机打乱片段列表
    # print(clips)
    random.shuffle(clips)
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
    final_clip.write_videofile(output_file, audio_codec=None,  codec="h264_nvenc", bitrate="20000k")
    final_clip.close()

#生成唯一文件名
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
    #总参数设置
    project_name = '造粒机混剪'
    output_folder = 'output\\造粒机混剪\\0809'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    #输入文件夹，按类型分好
    folder_path_list = ['input/造粒机/07-31/01/',
                        'input/造粒机/07-31/02/',
                        'input/造粒机/07-31/03/']

    #每个文件夹选几个视频
    number_of_video_01 = 1
    number_of_video_02 = 8
    number_of_video_03 = 1

    #每个片段截取多少秒
    clip_duration = 3
    clip_duration_01 = 2
    clip_duration_02 = 3
    clip_duration_03 = 2

    #片段截取
    clip_01 = create_video_montage(folder_path_list[0], number_of_video_01, clip_duration_01, with_audio=False)
    clip_02 = create_video_montage(folder_path_list[1], number_of_video_02, clip_duration_02, with_audio=False)
    clip_03 = create_video_montage(folder_path_list[2], number_of_video_03, clip_duration_03, with_audio=False)

    #拼合片段列表
    clips = clip_01 + clip_02 + clip_03
    # clips = clip_01 + clip_02

    #合并片段，生成视频
    video_name = generate_datetime_string(project_name)
    print(video_name)
    output_file = f'{os.path.join(output_folder, video_name)}.mp4'
    print(output_file)
    video_generator(clips, output_file, with_audio=False)

def multiple_video_voice_bgm_generation(project_name,
                                        output_folder,
                                        folder_path_list,
                                        number_of_video_dict,
                                        voice_txt_file,
                                        voice_name,
                                        speech_config,
                                        bgm_folder_path):
    #检查输出文件夹
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 生成配音
    voice_filename = voice.text2speech(voice_txt_file, voice_name, project_name, speech_config)

    # 随机选择BGM
    bgm_file = get_bgm_list_choice(bgm_folder_path)
    print(bgm_file)
    bgm_file_path = os.path.join(root_dir, bgm_folder_path, bgm_file)
    # print(bgm_file_path)



    #输入文件夹，按类型分好
    # folder_path_list = ['input/2024.4.1男孩女孩你该如何保护自己2/音频+素材2/素材/开头结尾',
    #                     'input/2024.4.1男孩女孩你该如何保护自己2/音频+素材2/素材/标题集',
    #                     'input/2024.4.1男孩女孩你该如何保护自己2/音频+素材2/素材/翻书',
    #                     'input/2024.4.1男孩女孩你该如何保护自己2/音频+素材2/素材/合书',
    #                     'input/2024.4.1男孩女孩你该如何保护自己2/音频+素材2/素材/开头结尾']

    #每个文件夹选几个视频
    # number_of_video_01 = 1
    # number_of_video_02 = 1
    # number_of_video_03 = 5
    # number_of_video_04 = 1
    # number_of_video_05 = 1

    #每个片段截取多少秒
    # clip_duration = 3
    # clip_duration_01 = 2
    # clip_duration_02 = 2
    # clip_duration_03 = 2
    # clip_duration_04 = 3
    # clip_duration_05 = 3

    #片段截取
    # clip_01 = create_video_montage(folder_path_list[0], number_of_video_01, clip_duration_01, with_audio=False)
    # clip_02 = create_video_montage(folder_path_list[1], number_of_video_02, clip_duration_02, with_audio=False)
    # clip_03 = create_video_montage(folder_path_list[2], number_of_video_03, clip_duration_03, with_audio=False)
    # clip_04 = create_video_montage(folder_path_list[3], number_of_video_04, clip_duration_04, with_audio=False)
    # clip_05 = create_video_montage(folder_path_list[4], number_of_video_05, clip_duration_05, with_audio=False)

    #拼合片段列表
    # clips = clip_01 + clip_02 + clip_03 + clip_04
    # clips = clip_01 + clip_02

    #合并片段，生成视频
    # video_name = generate_datetime_string(project_name)
    # print(video_name)
    # output_file = f'{os.path.join(output_folder, video_name)}.mp4'
    # print(output_file)
    # video_generator(clips, output_file, with_audio=False)

def main():
    project_name = '测试项目'
    output_folder = 'output\\图书\\男孩女孩你该如何保护自己'
    bgm_folder_path = 'BGM'

    # 配音部分参数
    voice_txt_file = f'{root_dir}/input/Voice_Text/摆地摊.txt'
    voice_name = "zh-CN-XiaoxiaoMultilingualNeural"
    speech_key = "8b7335e4c1cf4708a48453f878a6c802"
    service_region = "southeastasia"
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff44100Hz16BitMonoPcm)

    # 输入文件夹，按类型分好
    folder_path_list = ['input/2024.4.1男孩女孩你该如何保护自己2/音频+素材2/素材/开头结尾',
                        'input/2024.4.1男孩女孩你该如何保护自己2/音频+素材2/素材/标题集',
                        'input/2024.4.1男孩女孩你该如何保护自己2/音频+素材2/素材/翻书',
                        'input/2024.4.1男孩女孩你该如何保护自己2/音频+素材2/素材/合书',
                        'input/2024.4.1男孩女孩你该如何保护自己2/音频+素材2/素材/开头结尾']
    number_of_video_dict = {'number_of_video_1': 1,
                            'number_of_video_2': 1,
                            'number_of_video_3': 5,
                            'number_of_video_4': 1,
                            'number_of_video_5': 1}
    generated_quantity = 1
    for i in range(generated_quantity):
        # multiple_video_generation()
        multiple_video_voice_bgm_generation(project_name=project_name,
                                            output_folder=output_folder,
                                            folder_path_list=folder_path_list,
                                            number_of_video_dict=number_of_video_dict,
                                            voice_txt_file=voice_txt_file,
                                            voice_name=voice_name,
                                            speech_config=speech_config,
                                            bgm_folder_path=bgm_folder_path)


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
    composite_audio = CompositeAudioClip([audio_clip, bgm_clip])
    composite_audio.write_audiofile('test.mp3', codec='libmp3lame', fps=audio_clip.fps)


if __name__ == '__main__':
    main2()