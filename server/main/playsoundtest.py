import pygame
import time

async def play_and_release(sound_path):
    pygame.mixer.init()
    pygame.mixer.music.load(sound_path)
    pygame.mixer.music.play()
    
    # 等待播放结束
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    
    # 主动释放资源
    pygame.mixer.music.stop()
    pygame.mixer.quit()

async def play_audio_list():
    print("正在播放音频")
    with open("./main/audio/audio_index.txt", "r") as f:
        audio_files = f.readlines()
    audio_files = [ audio.strip() for audio in audio_files]
    print(audio_files)
    
    for audio in audio_files:
        await play_and_release(audio)  # 播放后文件可立即操作
    
if __name__ == "__main__":
    # 使用示例
    audio_files = ['./audio/audio_0.mp3']
    for audio in audio_files:
        play_and_release(audio)  # 播放后文件可立即操作