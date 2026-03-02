from pydub import AudioSegment

def merge_audio_files(file_list, output_path):
    """
    合并多个音频文件
    :param file_list: 待合并的音频文件路径列表（格式需一致）
    :param output_path: 合并后的输出路径
    """
    if not file_list:
        raise ValueError("文件列表不能为空！")

    # 加载第一个音频文件作为初始片段
    combined = AudioSegment.from_file(file_list[0])

    # 逐个追加其他音频文件
    for file in file_list[1:]:
        audio = AudioSegment.from_file(file)
        combined += audio  # 拼接音频

    # 导出合并后的文件
    combined.export(output_path, format="mp3")  # 格式可改为 wav/flac 等
    print(f"合并完成，文件已保存至: {output_path}")

# 示例用法
if __name__ == "__main__":
    audio_files = [
        "audio_0.mp3",
        "audio_100.mp3",
        "audio_200.mp3"
    ]
    audio_files = ["main/audio/"+f for f in audio_files]
    merge_audio_files(audio_files, "main/audio/audio.mp3")
    from playsound import playsound
    playsound("main/audio/audio.mp3")