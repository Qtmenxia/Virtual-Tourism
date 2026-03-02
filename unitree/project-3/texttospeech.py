from aip import AipSpeech

APP_ID = '119131130'
API_KEY = '4rA3ep1RWIcOZ54BUHfZ0EOX'
SECRET_KEY = 'mvmhmWEvXsrgyo9DAUMm5osO3lhePhhE'

def text_to_speech(introduction_text, output_audio_file="output.mp3"):
    client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)

    result = client.synthesis(introduction_text, 'zh', 1, {'vol': 5})
    if not isinstance(result, dict):
        with open(output_audio_file, 'wb') as f:
            f.write(result)
        return output_audio_file  # 返回音频文件路径
    else:
        print("error")
        return None  # 返回 None 表示合成失败