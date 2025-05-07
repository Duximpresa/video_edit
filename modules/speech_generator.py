from operator import index

import azure.cognitiveservices.speech as speechsdk
import os
from utils import utils
from tqdm import tqdm

root_dir = utils.root_dir()

def read_txt(file_path):
    with open("speechText.txt", mode="r", encoding="utf-8") as f:
        speechText = f.read()
        # print(speechText)
        # synthesizer.speak_text_async(f"{speechText}")
        return speechText


def get_all_file(path):
    file_list = []
    walks = os.walk(path)
    for root, dirs, files in walks:
        for filename in files:
            # print(os.path.join(root, filename))
            file_list.append(os.path.join(root, filename))
    return file_list


def get_txt_title(file):
    suffix = file.split('.')[-1]
    title = file.split('\\')[-1][:-4]
    # print(title)
    return title


def get_speechText(file):
    f = open(file, mode="r", encoding="utf-8")
    speechText = f.read()
    # print(speechText)
    f.close
    return speechText

def find_files_by_extensions(dir_path, extensions):
    """
    扫描指定根目录下的所有文件夹，查找指定后缀名的文件。

    Args:
        dir_path (str): 根目录路径。
        extensions (list): 文件后缀名列表，例如 ['.txt', '.pdf', '.jpg']。

    Returns:
        list: 符合条件的文件路径列表。
    """
    found_files = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            if any(file.lower().endswith(ext.lower()) for ext in extensions):
                found_files.append(os.path.join(root, file))
    return found_files

def text2speech_hash_code(text, voice_name, project_name, speech_config, voice_speed):
    print(text)
    hash_text = (project_name + voice_name + text + voice_speed)
    hash_code = utils.generate_hash_code(hash_text)
    print(hash_code)
    voice_storage = f'{root_dir}/storage/Voices'
    utils.check_dir_and_make_dir(voice_storage)
    # datetime_string = utils.generate_datetime_string()
    voice_filename = f"{voice_storage}/{project_name}_{hash_code}.wav"
    if not os.path.exists(voice_filename):
        speech_config.speech_synthesis_voice_name = voice_name
        audio_config = speechsdk.audio.AudioOutputConfig(filename=voice_filename)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        # synthesizer.speak_text_async(f'{speechText}')\
        ssml_string = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
          <voice name='{voice_name}'>
            <prosody rate='{voice_speed}'>{text}</prosody>
          </voice>
        </speak>
        """
        try:
            print("【获取音频数据中】")
            # result = synthesizer.speak_text_async(ssml_string).get()
            result = synthesizer.speak_ssml_async(ssml_string).get()
            print("【获取音频数据成功】")
        except speechsdk:
            print("【获取音频数据失败】")
        try:
            size = len(result.audio_data)
            # print(size)
            print(f"文件大小{str(size / 1024 / 1024)[0:4]}MB")
            chunk_size = 8
            with open(voice_filename, 'wb') as audio_file:
                for i in tqdm(range(0, size, chunk_size), desc="Writing audio data"):
                    audio_file.write(result.audio_data[i:i + chunk_size])
            print(f'-----【{voice_filename}】生成完毕-----')
            return voice_filename
        except IOError:
            print(f'-----【{voice_filename}】生成失败-----')
    else:
        print(f'【{voice_filename}】文件已存在')
        return voice_filename

def text2speech(text, voice_name, voice_filename, speech_config, voice_speed):
    if not os.path.exists(voice_filename):
        speech_config.speech_synthesis_voice_name = voice_name
        audio_config = speechsdk.audio.AudioOutputConfig(filename=voice_filename)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        # synthesizer.speak_text_async(f'{speechText}')\
        ssml_string = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
          <voice name='{voice_name}'>
            <prosody rate='{voice_speed}'>{text}</prosody>
          </voice>
        </speak>
        """
        try:
            print("【获取音频数据中】")
            # result = synthesizer.speak_text_async(ssml_string).get()
            result = synthesizer.speak_ssml_async(ssml_string).get()
            print("【获取音频数据成功】")
        except speechsdk:
            print("【获取音频数据失败】")
        try:
            size = len(result.audio_data)
            # print(size)
            print(f"文件大小{str(size / 1024 / 1024)[0:4]}MB")
            chunk_size = 8
            with open(voice_filename, 'wb') as audio_file:
                for i in tqdm(range(0, size, chunk_size), desc="Writing audio data"):
                    audio_file.write(result.audio_data[i:i + chunk_size])
            print(f'-----【{voice_filename}】生成完毕-----')
            return voice_filename
        except IOError:
            print(f'-----【{voice_filename}】生成失败-----')
    else:
        print(f'【{voice_filename}】文件已存在')
        return voice_filename



def text2speech_batch_txtfile(txtfile, voice_name, project_name, speech_config, voice_speed):
    print(txtfile)
    # 假设你的文件名为 example.txt
    index = 1
    with open(txtfile, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        for line in lines:
            # 去除每行末尾的换行符
            print(line.strip())
            voice_storage = f'{root_dir}/storage/Voices'
            utils.check_dir_and_make_dir(voice_storage)
            utils.check_dir_and_make_dir(f'{voice_storage}/{project_name}')
            voice_filename = f'{voice_storage}/{project_name}/{project_name}_{index:02d}.wav'
            print(voice_filename)
            index += 1
            text = line.strip()
            text2speech(text, voice_name, voice_filename, speech_config, voice_speed)


def main():
    speech_key = "8b7335e4c1cf4708a48453f878a6c802"
    service_region = "southeastasia"
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff44100Hz16BitMonoPcm)

    text = '人活着的意义不在乎得到了什么，而在于你如何面对失去。活着本身就是一种坚持，无论命运如何无常，都要用尽全力去感受生命的每一刻温暖与苦痛。'
    project_name = '测试语音'
    voice_name = "zh-CN-XiaoqiuNeural"
    voice_speed = '0%'

    voice_filename = text2speech_hash_code(text, voice_name, project_name, speech_config, voice_speed)

def main2():
    speech_key = "8b7335e4c1cf4708a48453f878a6c802"
    service_region = "southeastasia"
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff44100Hz16BitMonoPcm)



    txtfile_path = 'voice_txt'
    project_name = '短裤-01-开头'
    voice_name = "zh-CN-XiaochenMultilingualNeural"
    voice_speed = '0%'
    txtfile_list = find_files_by_extensions(txtfile_path, '.txt')
    for txtfile in txtfile_list:
        project_name = os.path.splitext(os.path.basename(txtfile))[0]
        print(project_name)
        text2speech_batch_txtfile(txtfile, voice_name, project_name, speech_config, voice_speed)
if __name__ == "__main__":
    main2()