import cv2
from PIL import ImageFont, ImageDraw, Image
import numpy as np
import os
from tqdm import tqdm

def video_text(video_path, texts, output_path):
    # 打开视频文件
    cap = cv2.VideoCapture(video_path)

    # 获取视频的宽度、高度和帧率
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print("total_frames:", total_frames)

    # 定义输出视频文件
    output_path = output_path
    # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fourcc = cv2.VideoWriter.fourcc(*'x264')
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    # out.set(cv2.VIDEOWRITER_PROP_QUALITY, 10)

    # 加载中文字体
    font_path = 'font/AlibabaPuHuiTi-2-105-Heavy.ttf'  # 替换为你的中文字体路径
    font = ImageFont.truetype(font_path, 67)



    with tqdm(total=total_frames, desc="Processing video") as pbar:
        while cap.isOpened():
            # print('\r', end='')
            # print(f'【开始输出】：{video_path}', end='')
            ret, frame = cap.read()
            if not ret:
                break

            # 将OpenCV图像转换为Pillow图像
            frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            # 获取文本的边界框
            # bbox = draw.textbbox((0, 0), text, font=font)

            # 在Pillow图像上添加文字
            draw = ImageDraw.Draw(frame_pil)
            text = texts

            # 计算文本的起始位置，使其居中
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            # position = ((frame_width - text_width) // 2, (frame_height - text_height) // 2)
            position = ((frame_width - text_width) // 2-20, 10)

            # print(f'frame_width:{frame_width}', end='')
            # print(f'text_width:{text_width}', end='')
            # print(f'position:{position}', end='')

            # position = (540, 200)
            # draw.text(position, text, font=font, fill=(255, 222, 0, 0))
            draw.multiline_text(position, text,
                                fill=(255, 222, 0, 0),
                                font=font,
                                align="center",
                                stroke_width=5,
                                stroke_fill=(0, 0, 0))

            # 将Pillow图像转换回OpenCV图像
            frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)

            # 写入帧到输出视频
            out.write(frame)

            # 更新进度条
            pbar.update(1)


    # 释放资源
    cap.release()
    out.release()
    cv2.destroyAllWindows()

def add_text_to_videos(video_folder, texts, output_folder):
    # 获取视频文件夹中的所有视频文件
    video_files = [f for f in os.listdir(video_folder) if f.lower().endswith((".mp4", ".avi", ".mkv"))]
    output_files = [f for f in os.listdir(output_folder) if f.lower().endswith((".mp4", ".avi", ".mkv"))]
    # music_files = [f for f in os.listdir(music_folder) if f.lower().endswith((".mp3", ".wav"))]
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

        print('-' * 50)
        print(f'【视频】：{video_name}')
        # print(f'【音乐】：{music_name}')
        # print(f'【视频时长】：{video_clip.duration}')
        print('-' * 50)

        output_path = os.path.join(output_folder, f"{video_name.split('.')[0]}_text.{video_name.split('.')[-1]}")

        # # 添加文本
        video_text(video_path, texts, output_path)

        print('-' * 50)
        print(f'{output_path_name}_已完成_【OK】')
        print('-' * 50)

    print("所有视频处理完成！")

def main():

    texts = '''
    得知我们的造粒机产能高后
    每天都有很多老板带料来挤压
    厂里也越来越热闹了
    '''

    video_folder_path = 'output/造粒机混剪/0731'
    output_folder_path = 'output/造粒机混剪/0731/text_to_video'
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    add_text_to_videos(video_folder_path, texts, output_folder_path)

if __name__ == '__main__':
    main()