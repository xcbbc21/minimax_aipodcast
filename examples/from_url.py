"""examples/from_url.py - 网页 URL 输入"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from aipodcast import generate_podcast


def main():
    result = generate_podcast(
        url="https://example.com/article.html",
        output="url_podcast.mp3",
        voice="mini",
        language="zh",
    )

    if result.success:
        print(f"✓ {result.audio_path}")
    else:
        print(f"✗ {result.error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
