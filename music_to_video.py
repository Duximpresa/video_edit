from moviepy.editor import VideoFileClip, AudioFileClip
import os
import random


def add_music_to_videos(video_folder, music_folder, output_folder):
    """
    给视频文件夹中的视频添加音乐。

    Args:
        video_folder (str): 视频文件夹的路径。
        music_folder (str): 音乐文件夹的路径。
    """
    # 获取视频文件夹中的所有视频文件
    video_files = [f for f in os.listdir(video_folder) if f.lower().endswith((".mp4", ".avi", ".mkv"))]
    output_files = [f for f in os.listdir(output_folder) if f.lower().endswith((".mp4", ".avi", ".mkv"))]
    music_files = [f for f in os.listdir(music_folder) if f.lower().endswith((".mp3", ".wav"))]
    count = 1
    # 遍历视频文件夹中的每个视频文件
    for video_file in video_files:
        video_path = os.path.join(video_folder, video_file)
        video_name = video_path.split('\\')[-1]
        output_path = os.path.join(output_folder, f"{video_name.split('.')[0]}_music.{video_name.split('.')[-1]}")
        output_path_name = output_path.split('\\')[-1]
        if output_path_name in output_files:
            print(f"文件：【{output_path_name}】 已存在")
            continue

        # # 随机选择音乐文件夹中的一个音乐文件
        music_files = [f for f in os.listdir(music_folder) if f.lower().endswith((".mp3", ".wav"))]
        selected_music_file = random.choice(music_files)
        music_path = os.path.join(music_folder, selected_music_file)

        #
        # # 加载视频和音乐
        video_clip = VideoFileClip(video_path)
        music_clip = AudioFileClip(music_path)
        #
        music_name = music_path.split("\\")[-1]
        print('-' * 50)
        print(f'【视频】：{video_name}')
        print(f'【音乐】：{music_name}')
        print(f'【视频时长】：{video_clip.duration}')
        print('-' * 50)
        # # 将音乐添加到视频中，保持视频的主要时长
        final_clip = video_clip.set_audio(music_clip).set_duration(video_clip.duration)
        #
        # # 保存成新的视频文件
        # output_path = os.path.join(output_folder, f"{video_name.split('.')[0]}_music.{video_name.split('.')[-1]}")

        # final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", bitrate="10000k", audio_bitrate='192k')
        final_clip.write_videofile(output_path, codec="h264_nvenc", audio_codec="aac", bitrate="20000k", audio_bitrate='192k')
        #
        # print(f"已为视频文件 {video_file} 添加了音乐并保存到 {output_path}")
        print('-' * 50)
        print(f'{output_path_name}_已完成_【OK】')
        print('-' * 50)

    print("所有视频处理完成！")


def main():
    video_folder_path = "output\\造粒机混剪\\0731\\text_to_video"
    music_folder_path = "BGM"
    output_folder_path = "output\\造粒机混剪\\0731\\music_to_video"
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)
    add_music_to_videos(video_folder_path, music_folder_path, output_folder_path)

if __name__ == "__main__":
    main()