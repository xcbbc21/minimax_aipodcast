"""examples/from_pdf.py - PDF 输入"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from aipodcast import generate_podcast


def main():
    pdf_path = "paper.pdf"
    if not Path(pdf_path).exists():
        print(f"✗ 文件不存在: {pdf_path}")
        raise SystemExit(1)

    def on_progress(stage: str, message: str):
        print(f"  [{stage}] {message}")

    result = generate_podcast(
        file=pdf_path,
        output="pdf_podcast.mp3",
        voice="mini",
        on_progress=on_progress,
    )

    if result.success:
        print(f"✓ {result.audio_path} ({result.duration_s:.0f}s)")
    else:
        print(f"✗ {result.error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
