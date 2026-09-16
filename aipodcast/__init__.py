"""aipodcast - AI 单口播客生成器（给 AI Agent 用）"""
from .api import generate_podcast, clone_voice, PodcastResult, AIPodcastError
from .pipeline import run_pipeline, ProgressCallback
from .script_generator import generate_script, parse_script_lines
from .tts_synthesizer import synthesize_voice
from .speaker_clone import clone_voice as _clone_voice_fn
from .exceptions import (
    AIPodcastError,
    ConfigError,
    InputError,
    APIKeyError,
    RateLimitError,
    APIError,
    TTSError,
    AudioProcessingError,
)

__version__ = "0.2.1"
__all__ = [
    "generate_podcast",
    "clone_voice",
    "generate_script",
    "parse_script_lines",
    "synthesize_voice",
    "run_pipeline",
    "PodcastResult",
    "ProgressCallback",
    "AIPodcastError",
    "ConfigError",
    "InputError",
    "APIKeyError",
    "RateLimitError",
    "APIError",
    "TTSError",
    "AudioProcessingError",
]
