import azure.cognitiveservices.speech as speechsdk
import os
from utils import utils
from tqdm import tqdm

# Configure speech subscription key and region
# 登录
root_dir = utils.root_dir()

speech_key = "8b7335e4c1cf4708a48453f878a6c802"
service_region = "southeastasia"
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff44100Hz16BitMonoPcm)
# audio_config = speechsdk.audio.AudioOutputConfig()
voice_name_list = ["zh-CN-XiaoxiaoNeural",
                   "zh-CN-XiaochenNeural",
                   "zh-CN-YunfengNeural",
                   "zh-CN-YunxiNeural",
                   "zh-CN-YunzeNeural",
                   "zh-CN-XiaoqiuNeural",
                   "zh-CN-guangxi-YunqiNeural",
                   "zh-CN-XiaoxiaoMultilingualNeural"]


# speech_config.speech_synthesis_voice_name = voice_name_list[7]
# Create a speech synthesizer object
# synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

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


def text2speech(voice_txt_file, voice_name, project_name, speech_config, voice_speed):
    speechText = get_speechText(voice_txt_file)
    print(speechText)
    hash_text = (project_name + voice_name + speechText)
    hash_code = utils.generate_hash_code(speechText)
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
            <prosody rate='{voice_speed}'>{speechText}</prosody>
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

    # result = synthesizer.speak_text_async(f'{speechText}').get()


# Synthesize the text
# result = synthesizer.speak_text_async(f'{speechText}').get()

# Save the synthesized audio to a file
# with open('output.wav', 'wb') as audio_file:
# audio_file.write(result.audio_data)


def main():
    voice_file = f'{root_dir}/input/Voice_Text/摆地摊.txt'
    project_name = '测试语音'
    voice_name = "zh-CN-XiaoxiaoMultilingualNeural"
    voice_speed = '-50%'
    text2speech(voice_file, voice_name, project_name, speech_config, voice_speed=voice_speed)


if __name__ == '__main__':
    main()
