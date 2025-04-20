from moviepy.editor import *
from moviepy.editor import VideoFileClip

new_size = (1080, 1920)
print(f'设置项目尺寸{new_size}')
video_file_01 = 'test/IMG_1770.MOV'
video_file_02 = 'test/IMG_1866.MOV'
bgm_file = 'BGM/赫学熊/Deep East Music - The Dollhouse Dance.mp3'

clip_01 = VideoFileClip(video_file_01)
clip_01 = clip_01.subclip(1, 6)
clip_01 = clip_01.resize(new_size)

clip_02 = VideoFileClip(video_file_02)
clip_02 = clip_02.subclip(3, 8)
clip_02 = clip_02.resize(new_size)

final_clip = concatenate_videoclips([clip_01, clip_02])

bgm_clip = AudioFileClip(bgm_file)
bgm_clip = bgm_clip.volumex(1.2)
if bgm_clip.duration < final_clip.duration:
    # 如果背景音乐短于视频，循环播放
    bgm_clip = bgm_clip.loop(duration=final_clip.duration)
elif bgm_clip.duration > final_clip.duration:
    # 如果背景音乐长于视频，截取到视频长度
    bgm_clip = bgm_clip.subclip(0, final_clip.duration)

final_clip = final_clip.set_audio(bgm_clip)


test_file_name = 'test/test_video_01.mp4'

ffmpeg_params = [
        "-vf", "colorspace=all=bt709:iall=bt601-6-625:space=bt709,eq=gamma=2.2",  # 色彩空间转换滤镜
        "-pix_fmt", "yuv420p",  # 确保输出像素格式兼容大多数播放器
        "-colorspace", "bt709",  # 指定输出色彩空间为 Rec.709
        "-color_primaries", "bt709",
        "-color_trc", "bt709"
    ]
final_clip.write_videofile(test_file_name, codec='libx264', bitrate='18M', audio_codec='aac', audio_bitrate='320k', ffmpeg_params=ffmpeg_params)
final_clip.close()
