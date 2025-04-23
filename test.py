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
from modules.video_mixer import batch_multiple_video_bgm_generation
from modules.video_mixer import batch_multiple_video_voice_bgm_generation
root_dir = utils.root_dir()


def main():
    config_file_path = 'config/风景'

    config_file_dir = os.path.join(root_dir, config_file_path)
    batch_multiple_video_bgm_generation(config_file_dir)

def main2():
    config_file_path = 'config/索罗娜'

    config_file_dir = os.path.join(root_dir, config_file_path)
    batch_multiple_video_voice_bgm_generation(config_file_dir)

if __name__ == '__main__':
    main2()