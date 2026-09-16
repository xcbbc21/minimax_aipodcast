"""examples/from_text.py - 最简单的用法：直接传入文本"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from aipodcast import generate_podcast


def main():
    result = generate_podcast(
        text="""
        今天讲讲读书何以改变命运。一篇有意思的论文，
        用 2018 年中国家庭收入调查数据，结合高考分数线，
        估计重点大学对个人收入的长期回报。
        """,
        output="text_podcast.mp3",
        voice="mini",
        language="zh",
        duration_min=3,
        duration_max=4,
    )

    if result.success:
        print(f"✓ 成功: {result.audio_path}")
        print(f"  时长: ~{result.duration_s:.0f}s")
        print(f"  脚本: {result.script_chars} 字符 / {result.script_sentences} 句")
    else:
        print(f"✗ 失败: {result.error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
