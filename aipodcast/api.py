"""
api.py - 公开 Python API（AI Agent 主入口）
"""
from typing import Optional
from .pipeline import run_pipeline, PodcastResult, ProgressCallback
from .speaker_clone import clone_voice, generate_voice_id, validate_voice_id
from .script_generator import generate_script, parse_script_lines
from .tts_synthesizer import synthesize_voice, stream_synthesize, concatenate_chunks
from .exceptions import AIPodcastError

__all__ = [
    "generate_podcast",
    "clone_voice",
    "generate_script",
    "parse_script_lines",
    "PodcastResult",
    "AIPodcastError",
]


def generate_podcast(
    text: Optional[str] = None,
    file: Optional[str] = None,
    url: Optional[str] = None,
    output: Optional[str] = None,
    voice: str = "mini",
    custom_voice_id: Optional[str] = None,
    language: str = "zh",
    duration_min: int = 22,
    duration_max: int = 25,
    api_key: Optional[str] = None,
    on_progress: Optional[ProgressCallback] = None,
    skip_rescript: bool = False,
) -> PodcastResult:
    """
    生成单口播客（最常用入口）

    三选一输入：
        text: 直接传入文本
        file: 文件路径（.pdf / .html / .md / .txt）
        url: 网页 URL

    Args:
        voice: "mini" / "max"（默认 mini）
        custom_voice_id: 自定义声音 ID（来自 clone_voice）
        duration_min/max: 目标时长（分钟）
        api_key: 显式 API Key（或环境变量 AIPODCAST_API_KEY）
        on_progress: 进度回调 callback(stage, message)

    Returns:
        PodcastResult(success, audio_path, duration_s, ...)

    Example:
        >>> from aipodcast import generate_podcast
        >>> r = generate_podcast(text="今天讲...", output="out.mp3")
        >>> print(r.audio_path, r.duration_s)
    """
    return run_pipeline(
        text=text,
        file=file,
        url=url,
        output=output,
        voice=voice,
        custom_voice_id=custom_voice_id,
        language=language,
        duration_min=duration_min,
        duration_max=duration_max,
        api_key=api_key,
        on_progress=on_progress,
        skip_rescript=skip_rescript,
    )
