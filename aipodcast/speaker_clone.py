"""
speaker_clone.py - 声音克隆（CLI 给 AI agent 用）
保留 backend/voice_manager.py 的核心克隆能力，去掉 Web 上传流程
"""
import logging
import os
import time
import string
import random
from pathlib import Path
from typing import Optional, Dict, Any
from .config import resolve_api_key, MODELS, TIMEOUTS, VOICE_ID_CONFIG
from .exceptions import APIError, APIKeyError

logger = logging.getLogger(__name__)


def generate_voice_id(prefix: Optional[str] = None) -> str:
    """生成 voice ID（克隆用）"""
    if prefix is None:
        prefix = VOICE_ID_CONFIG["prefix"]
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    random_num = str(random.randint(1000, 9999))
    voice_id = f"{prefix}_{random_str}_{random_num}"
    if len(voice_id) < VOICE_ID_CONFIG["min_length"]:
        voice_id += "".join(random.choices(
            string.ascii_lowercase + string.digits,
            k=VOICE_ID_CONFIG["min_length"] - len(voice_id)
        ))
    elif len(voice_id) > VOICE_ID_CONFIG["max_length"]:
        voice_id = voice_id[:VOICE_ID_CONFIG["max_length"]]
    return voice_id


def validate_voice_id(voice_id: str) -> bool:
    """校验 voice ID 格式"""
    if len(voice_id) < VOICE_ID_CONFIG["min_length"]:
        return False
    if len(voice_id) > VOICE_ID_CONFIG["max_length"]:
        return False
    if not voice_id[0].isalpha():
        return False
    if voice_id[-1] in ["-", "_"]:
        return False
    return all(c in VOICE_ID_CONFIG["allowed_chars"] for c in voice_id)


def clone_voice(
    audio_file_path: str,
    sample_text: str = "您好，我是客户经理李娜。",
    voice_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    从参考音频克隆声音

    Args:
        audio_file_path: 参考音频路径（10-30 秒 WAV/MP3）
        sample_text: 试听文本
        voice_id: 指定 voice ID，None 自动生成
        api_key: 显式 API Key

    Returns:
        {"voice_id": str, "trace_id": str, "audio_path": str}
    """
    import requests
    api_key = resolve_api_key(api_key)
    if voice_id is None:
        voice_id = generate_voice_id()
    validation = validate_voice_id(voice_id)
    if not validation:
        raise APIError(f"invalid voice_id: {voice_id}")

    # 1) 上传音频
    upload_url = "https://api.minimax.chat/v1/files/upload"
    upload_headers = {"Authorization": f"Bearer {api_key}"}

    with open(audio_file_path, "rb") as f:
        files = {"file": (os.path.basename(audio_file_path), f, "audio/wav")}
        try:
            r = requests.post(upload_url, headers=upload_headers, files=files, timeout=TIMEOUTS["voice_clone"])
            r.raise_for_status()
            upload_result = r.json()
            file_id = upload_result.get("file", {}).get("file_id")
            if not file_id:
                raise APIError(f"upload failed: {upload_result}")
        except Exception as e:
            raise APIError(f"upload failed: {e}")

    # 2) 调用克隆 API
    clone_url = "https://api.minimax.chat/v1/voice_clone"
    clone_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    clone_payload = {
        "model": MODELS["voice_clone"],
        "file_id": file_id,
        "voice_id": voice_id,
        "text": sample_text,
        "output_audio": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3"},
    }
    try:
        r = requests.post(clone_url, headers=clone_headers, json=clone_payload, timeout=TIMEOUTS["voice_clone"])
        r.raise_for_status()
        clone_result = r.json()
        base = clone_result.get("base_resp", {})
        if base.get("status_code") != 0:
            raise APIError(f"clone failed: {base.get('status_msg', 'unknown')}")
        trace_id = base.get("trace_id")
    except Exception as e:
        raise APIError(f"clone failed: {e}")

    return {
        "voice_id": voice_id,
        "trace_id": trace_id,
        "audio_path": audio_file_path,
    }
