"""examples/clone_voice.py - 声音克隆 + 用克隆声音生成"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from aipodcast import clone_voice, generate_podcast


def main():
    # 1. 从 10-30 秒参考音频克隆
    print("正在克隆声音...")
    clone = clone_voice(
        audio_file_path="reference.wav",
        sample_text="您好，这是我的声音样本，用于测试克隆效果。",
    )
    voice_id = clone["voice_id"]
    print(f"✓ 克隆完成: voice_id={voice_id}")
    print(f"  trace_id: {clone['trace_id']}")

    # 2. 用克隆的声音生成播客
    result = generate_podcast(
        text="今天我们来聊一个有意思的话题...",
        output="cloned_voice_podcast.mp3",
        voice="custom",
        custom_voice_id=voice_id,
        duration_min=3,
        duration_max=5,
    )

    if result.success:
        print(f"✓ {result.audio_path}")
    else:
        print(f"✗ {result.error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
