import os

from modules import speech_service

root_dir = speech_service.root_dir


def get_speechText(file):
    return speech_service.read_text_file(file)


def find_files_by_extensions(dir_path, extensions):
    if isinstance(extensions, str):
        extensions = [extensions]
    return speech_service.utils.find_files_by_extensions(dir_path, extensions)


def text2speech_hash_code(text, voice_name, project_name, speech_config, voice_speed):
    voice_storage = f"{root_dir}/storage/Voices"
    speech_service.utils.check_dir_and_make_dir(voice_storage)
    hash_code = speech_service.utils.generate_hash_code(project_name + voice_name + text + voice_speed)
    voice_filename = f"{voice_storage}/{project_name}_{hash_code}.wav"
    return speech_service.text_to_speech(text, voice_name, voice_filename, speech_config, voice_speed)


def text2speech(text, voice_name, voice_filename, speech_config, voice_speed):
    return speech_service.text_to_speech(text, voice_name, voice_filename, speech_config, voice_speed)


def text2speech_batch_txtfile(txtfile, voice_name, project_name, speech_config, voice_speed):
    return speech_service.batch_text_to_speech(
        txtfile=txtfile,
        voice_name=voice_name,
        project_name=project_name,
        speech_config=speech_config,
        voice_speed=voice_speed,
    )


if __name__ == "__main__":
    config = speech_service.build_speech_config_from_env()
    txtfile_path = "voice_txt"
    voice_name = "zh-CN-XiaochenMultilingualNeural"
    voice_speed = "0%"
    for txtfile in find_files_by_extensions(txtfile_path, ".txt"):
        project_name = os.path.splitext(os.path.basename(txtfile))[0]
        text2speech_batch_txtfile(txtfile, voice_name, project_name, config, voice_speed)
