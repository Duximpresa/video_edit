import os
import random
from moviepy.editor import VideoFileClip, concatenate_videoclips
from datetime import datetime




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
def create_video_montage(folder_path, number_of_videos, clip_duration, output_file, with_audio=True):
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

    # 连接所有片段以创建最终视频
    final_clip = concatenate_videoclips(clips)

    # 将结果写入输出文件
    final_clip.write_videofile(output_file, audio_codec='aac' if with_audio else None)


def generate_datetime_string(prefix):
    # 获取当前的日期和时间
    now = datetime.now()
    # 将日期和时间格式化为字符串
    datetime_string = now.strftime("%Y-%m-%d_%H-%M-%S")
    # 返回带有前缀的日期和时间字符串
    return f"{prefix}_{datetime_string}"


video_name = generate_datetime_string('video')
# 示例用法
create_video_montage('input/', 6, 4, f'output/{video_name}.mp4', with_audio=False)

# 打印成功消息
print("视频集锦已成功创建。")
