import os
import random
from moviepy.editor import VideoFileClip, concatenate_videoclips
from datetime import datetime


def random_clip(video_path, clip_duration, output_path):
    # 加载视频
    video = VideoFileClip(video_path)
    max_start = video.duration - clip_duration
    start_time = random.uniform(0, max_start)

    # 截取视频片段
    clip = video.subclip(start_time, start_time + clip_duration)

    # 输出视频片段
    clip.write_videofile(output_path, codec='libx264')


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

    # 随机打乱片段列表
    random.shuffle(clips)
    return clips

def generate_clips(folder_path_list, number_of_videos, clip_duration, output_file):
    clips = []
    for folder_path in folder_path_list:
        clip = create_video_montage(folder_path, number_of_videos, clip_duration, output_file, with_audio=False)
        clips.append(clip)

def video_generator(clips, output_file, with_audio=True):
    # 连接所有片段以创建最终视频
    final_clip = concatenate_videoclips(clips)
    # final_clip = clips

    # 将结果写入输出文件
    final_clip.write_videofile(output_file, audio_codec='aac' if with_audio else None)
    # final_clip.write_videofile(output_file, audio_codec=None,  codec="libx264")

#生成唯一文件名
def generate_datetime_string(prefix):
    # 获取当前的日期和时间
    now = datetime.now()
    # 将日期和时间格式化为字符串
    datetime_string = now.strftime("%Y-%m-%d_%H-%M-%S")
    # 返回带有前缀的日期和时间字符串
    return f"{prefix}_{datetime_string}"


# video_name = generate_datetime_string('video')
# 示例用法
# create_video_montage('input/', 6, 4, f'output/{video_name}.mp4', with_audio=False)

# 打印成功消息
# print("视频集锦已成功创建。")
def multiple_video_generation():
    #总参数设置
    project_name = '卖蛇视频'
    output_folder = 'output\\0403'

    #输入文件夹，按类型分好
    folder_path_list = ['input/video_01/',
                        'input/video_02/',
                        'input/video_03/']

    #每个文件夹选几个视频
    number_of_video_01 = 4
    number_of_video_02 = 2
    number_of_video_03 = 2

    #每个片段截取多少秒
    clip_duration = 2
    clip_duration_01 = clip_duration
    clip_duration_02 = 3
    clip_duration_03 = clip_duration

    #片段截取
    clip_01 = create_video_montage(folder_path_list[0], number_of_video_01, clip_duration_01, with_audio=False)
    clip_02 = create_video_montage(folder_path_list[1], number_of_video_02, clip_duration_02, with_audio=False)
    clip_03 = create_video_montage(folder_path_list[2], number_of_video_03, clip_duration_03, with_audio=False)

    #拼合片段列表
    clips = clip_01 + clip_02 + clip_03

    #合并片段，生成视频
    video_name = generate_datetime_string(project_name)
    print(video_name)
    output_file = f'{os.path.join(output_folder, video_name)}.mp4'
    print(output_file)
    video_generator(clips, output_file, with_audio=False)

def main():
    generated_quantity = 50
    for i in range(generated_quantity):
        multiple_video_generation()


if __name__ == '__main__':
    main()