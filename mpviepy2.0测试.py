from moviepy.editor import *
from moviepy.editor import VideoFileClip

new_size = (1080, 1920)

video_file_01 = 'test/IMG_1770.mp4'
video_file_02 = 'test/IMG_1866.mp4'
bgm_file = 'BGM/赫学熊/Deep East Music - The Dollhouse Dance.mp3'

clip_01 = VideoFileClip(video_file_01)
clip_01 = clip_01.subclip(1, 6)
clip_01 = clip_01.resize((1080, 1920))

clip_02 = VideoFileClip(video_file_02)
clip_02 = clip_02.subclip(3, 8)
clip_02 = clip_02.resize((1080, 1920))

final_clip = concatenate_videoclips([clip_01, clip_02])

bgm_clip = AudioFileClip(bgm_file)
bgm_clip = bgm_clip.volumex(2)
if bgm_clip.duration < final_clip.duration:
    # 如果背景音乐短于视频，循环播放
    bgm_clip = bgm_clip.loop(duration=final_clip.duration)
elif bgm_clip.duration > final_clip.duration:
    # 如果背景音乐长于视频，截取到视频长度
    bgm_clip = bgm_clip.subclip(0, final_clip.duration)

final_clip = final_clip.set_audio(bgm_clip)


test_file_name = 'test/test_video_01.mp4'

# ffmpeg_params = ["-vf", "colorspace=iall=bt709:ospace=bt709:trc=bt709:range=pc"]
final_clip.write_videofile(test_file_name, codec='h264_nvenc', bitrate='10M', audio_codec='aac', audio_bitrate='320k', )
final_clip.close()
