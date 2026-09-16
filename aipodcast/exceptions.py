"""aipodcast 异常类型（AI Agent 友好）"""
from typing import Optional


class AIPodcastError(Exception):
    """所有 aipodcast 异常的基类"""
    exit_code: int = 1

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigError(AIPodcastError):
    """配置缺失或无效"""
    exit_code = 1


class InputError(AIPodcastError):
    """输入源（text/file/url）无效"""
    exit_code = 1


class APIKeyError(AIPodcastError):
    """API Key 缺失或鉴权失败"""
    exit_code = 1


class RateLimitError(AIPodcastError):
    """MiniMax TTS/LLM 触发了 RPM 限流"""
    exit_code = 3


class APIError(AIPodcastError):
    """MiniMax API 返回非预期结果"""
    exit_code = 2


class TTSError(AIPodcastError):
    """TTS 合成失败（多次重试后）"""
    exit_code = 2


class AudioProcessingError(AIPodcastError):
    """ffmpeg / pydub 音频处理失败"""
    exit_code = 2
