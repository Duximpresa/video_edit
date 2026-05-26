import os

from modules import speech_service

root_dir = speech_service.root_dir
voice_name_list = speech_service.DEFAULT_VOICE_NAMES


def read_txt(file_path):
    return speech_service.read_text_file(file_path)


def get_all_file(path):
    file_list = []
    walks = os.walk(path)
    for root, _, files in walks:
        for filename in files:
            file_list.append(os.path.join(root, filename))
    return file_list


def get_txt_title(file):
    return file.split("\\")[-1][:-4]


def get_speechText(file):
    return speech_service.read_text_file(file)


def text2speech(voice_txt_file, voice_name, project_name, speech_config, voice_speed):
    return speech_service.text_to_speech_from_file(
        voice_txt_file=voice_txt_file,
        voice_name=voice_name,
        project_name=project_name,
        speech_config=speech_config,
        voice_speed=voice_speed,
    )
