import os
from typing import Iterable, Optional

import azure.cognitiveservices.speech as speechsdk
from tqdm import tqdm

from utils import utils

root_dir = utils.root_dir()

DEFAULT_VOICE_NAMES = [
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-XiaochenNeural",
    "zh-CN-YunfengNeural",
    "zh-CN-YunxiNeural",
    "zh-CN-YunzeNeural",
    "zh-CN-XiaoqiuNeural",
    "zh-CN-guangxi-YunqiNeural",
    "zh-CN-XiaoxiaoMultilingualNeural",
]


def build_speech_config_from_env() -> speechsdk.SpeechConfig:
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    service_region = os.getenv("AZURE_SERVICE_REGION")
    if not speech_key or not service_region:
        raise RuntimeError(
            "Missing Azure speech credentials. Set AZURE_SPEECH_KEY and AZURE_SERVICE_REGION."
        )

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff44100Hz16BitMonoPcm
    )
    return speech_config


def read_text_file(file_path: str) -> str:
    with open(file_path, mode="r", encoding="utf-8") as f:
        return f.read()


def _synthesize_ssml(
    text: str,
    voice_name: str,
    voice_speed: str,
    output_file: str,
    speech_config: speechsdk.SpeechConfig,
) -> str:
    speech_config.speech_synthesis_voice_name = voice_name
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    ssml_string = f"""
    <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
      <voice name='{voice_name}'>
        <prosody rate='{voice_speed}'>{text}</prosody>
      </voice>
    </speak>
    """
    result = synthesizer.speak_ssml_async(ssml_string).get()
    size = len(result.audio_data)
    with open(output_file, "wb") as audio_file:
        chunk_size = 8
        for i in tqdm(range(0, size, chunk_size), desc="Writing audio data"):
            audio_file.write(result.audio_data[i : i + chunk_size])
    return output_file


def text_to_speech_from_file(
    voice_txt_file: str,
    voice_name: str,
    project_name: str,
    speech_config: speechsdk.SpeechConfig,
    voice_speed: str,
) -> str:
    speech_text = read_text_file(voice_txt_file)
    hash_code = utils.generate_hash_code(project_name + voice_name + speech_text + voice_speed)
    voice_storage = f"{root_dir}/storage/Voices"
    utils.check_dir_and_make_dir(voice_storage)
    output_file = f"{voice_storage}/{project_name}_{hash_code}.wav"
    if os.path.exists(output_file):
        return output_file
    return _synthesize_ssml(speech_text, voice_name, voice_speed, output_file, speech_config)


def text_to_speech(
    text: str,
    voice_name: str,
    output_file: str,
    speech_config: speechsdk.SpeechConfig,
    voice_speed: str,
) -> str:
    if os.path.exists(output_file):
        return output_file
    utils.check_dir_and_make_dir(os.path.dirname(output_file))
    return _synthesize_ssml(text, voice_name, voice_speed, output_file, speech_config)


def batch_text_to_speech(
    txtfile: str,
    voice_name: str,
    project_name: str,
    speech_config: speechsdk.SpeechConfig,
    voice_speed: str,
) -> Iterable[str]:
    output_files = []
    voice_storage = f"{root_dir}/storage/Voices/{project_name}"
    utils.check_dir_and_make_dir(voice_storage)
    with open(txtfile, "r", encoding="utf-8") as file:
        lines = file.readlines()
    for index, line in enumerate(lines, start=1):
        text = line.strip()
        output_file = f"{voice_storage}/{project_name}_{index:02d}.wav"
        output_files.append(text_to_speech(text, voice_name, output_file, speech_config, voice_speed))
    return output_files
