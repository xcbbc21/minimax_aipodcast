"""输出路径管理 + 命名"""
from pathlib import Path
from datetime import datetime
from typing import Optional
import re


def sanitize_filename(s: str, max_len: int = 60) -> str:
    """把任意字符串转成安全文件名"""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', s)
    s = re.sub(r'\s+', '_', s.strip())
    return s[:max_len]


def default_output_path(
    input_source: str = "",
    voice: str = "mini",
    language: str = "zh",
    ext: str = "mp3",
    output_dir: Optional[str] = None,
) -> Path:
    """
    默认输出路径：<output_dir>/<timestamp>_<voice>_<lang>.<ext>
    或：<output_dir>/<sanitized_input>_<voice>_<lang>.<ext>
    """
    output_dir = Path(output_dir) if output_dir else Path.cwd() / "aipodcast_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if input_source:
        # 短前缀 + timestamp
        base = sanitize_filename(Path(input_source).stem if Path(input_source).exists() else input_source[:30])
        name = f"{ts}_{base}_{voice}_{language}.{ext}"
    else:
        name = f"{ts}_{voice}_{language}.{ext}"
    return output_dir / name
