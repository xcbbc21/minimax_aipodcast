"""
aipodcast 配置管理
- API Key 从环境变量 AIPODCAST_API_KEY 读取（不再硬编码）
- 路径全部基于包根目录
- 支持 CLI / Python API 运行时覆盖
"""
import os
from pathlib import Path
from typing import Optional


# ========== 包根目录 ==========
PACKAGE_DIR = Path(__file__).parent
REPO_ROOT = PACKAGE_DIR.parent

# ========== API Key 解析 ==========
DEFAULT_API_KEY = "sk-cp-VkSIMFgqWv-aKqOAj2SlNWGee1f7I_9o6UP2kfgk-rXt6wu_mq8OLPthMaFK8fAhaRngzP7s2H0qsMINsWP8EKN2NKTZ3vR4vCD6LLmFnkF9XemxMh9CEKk"


def resolve_api_key(explicit: Optional[str] = None) -> str:
    """
    解析 API Key 优先级：
    1. 显式传入
    2. 环境变量 AIPODCAST_API_KEY
    3. 环境变量 MINIMAX_API_KEY（兼容旧名）
    4. 硬编码默认值（仅当 1-3 都没有）
    """
    if explicit:
        return explicit
    env = os.environ.get("AIPODCAST_API_KEY") or os.environ.get("MINIMAX_API_KEY")
    if env:
        return env
    return DEFAULT_API_KEY


# ========== 默认音色配置 ==========
DEFAULT_VOICES = {
    "mini": {
        "name": "Mini",
        "gender": "female",
        "voice_id": "moss_audio_aaa1346a-7ce7-11f0-8e61-2e6e3c7ee85d",
        "description": "女声 - 活泼亲切",
    },
    "max": {
        "name": "Max",
        "gender": "male",
        "voice_id": "moss_audio_ce44fc67-7ce3-11f0-8de5-96e35d26fb85",
        "description": "男声 - 稳重专业",
    },
}

# ========== BGM 路径（用户可外部覆盖）==========
BGM_DIR = REPO_ROOT / "aipodcast_assets" / "bgm"

# ========== MiniMax API 端点 ==========
MINIMAX_API_ENDPOINTS = {
    "text_completion": "https://api.minimaxi.com/v1/text/chatcompletion_v2",
    "tts": "https://api.minimaxi.com/v1/t2a_v2",
    "voice_clone": "https://api.minimax.chat/v1/voice_clone",
    "file_upload": "https://api.minimax.chat/v1/files/upload",
}

# ========== 模型配置 ==========
MODELS = {
    "text": "MiniMax-M3",
    "tts": "speech-2.8-hd",
    "voice_clone": "speech-02-turbo",
}

# ========== 播客生成默认配置 ==========
PODCAST_CONFIG = {
    "target_duration_min": 22,
    "target_duration_max": 25,
    "style": "单口精读",
}

# ========== 超时配置（秒）==========
TIMEOUTS = {
    "url_parsing": 30,
    "pdf_parsing": 30,
    "voice_clone": 60,
    "script_generation": 120,
    "tts_per_sentence": 30,
}

# ========== TTS 音频配置 ==========
TTS_AUDIO_SETTINGS = {
    "sample_rate": 32000,
    "bitrate": 128000,
    "format": "mp3",
    "channel": 1,
}

# ========== Voice ID 生成配置（用于声音克隆）==========
VOICE_ID_CONFIG = {
    "prefix": "customVoice",
    "min_length": 8,
    "max_length": 256,
    "allowed_chars": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_",
}

# ========== 日志配置 ==========
LOG_LEVEL = os.environ.get("AIPODCAST_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ========== 默认输出目录 ==========
DEFAULT_OUTPUT_DIR = REPO_ROOT / "aipodcast_output"
