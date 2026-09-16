"""
tts_synthesizer.py - TTS 合成（单路 + 限流友好 + 断点续传）
从 backend/podcast_generator.py 拆出
"""
import hashlib
import logging
import time
from pathlib import Path
from typing import Iterator, Dict, Any, Optional, List
from .config import resolve_api_key, MODELS, TIMEOUTS, TTS_AUDIO_SETTINGS, DEFAULT_VOICES
from .exceptions import TTSError, RateLimitError

logger = logging.getLogger(__name__)


def _cache_key_for(text: str, voice: str = "") -> str:
    """
    按 voice + text 双重 md5 索引 cache,避免:
    - 序号误用旧 audio(改 text → 不同 cache)
    - 换声音读到旧 audio(改 voice → 不同 cache)
    """
    return hashlib.md5(f"{voice}:{text}".encode("utf-8")).hexdigest()[:16]


def _tts_one(
    text: str,
    voice_id: str,
    api_key: str,
    max_retry: int = 5,
) -> Optional[str]:
    """
    合成单句（带限流长退避重试）
    Returns: hex string or None
    """
    import requests

    url = "https://api.minimaxi.com/v1/t2a_v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODELS["tts"],
        "text": text,
        "stream": False,
        "voice_setting": {"voice_id": voice_id, "speed": 1.0, "vol": 1.0, "pitch": 0},
        "audio_setting": TTS_AUDIO_SETTINGS,
        "subtitle_enable": False,
    }

    for attempt in range(max_retry + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUTS["tts_per_sentence"])
            r.raise_for_status()
            result = r.json()
            base = result.get("base_resp", {})
            if base.get("status_code") == 0 and "data" in result and "audio" in result["data"]:
                return result["data"]["audio"]
            err_code = base.get("status_code")
            err = base.get("status_msg", "unknown")
            # 配额硬错误立即失败,不再重试,避免空跑十几分钟才发现 quota 耗尽
            if err_code in (2056, 2057):
                raise TTSError(f"quota exhausted ({err_code}): {err}")
            # 限流时退避更长
            if "rate limit" in err.lower() or "rpm" in err.lower() or "1002" in err:
                wait = 30 if attempt == 0 else 45
                if attempt < max_retry:
                    logger.warning(f"TTS rate-limited, waiting {wait}s (attempt {attempt+1})")
                    time.sleep(wait)
                else:
                    return None
            else:
                wait = (2 ** attempt) * 3
                if attempt < max_retry:
                    time.sleep(wait)
                else:
                    return None
        except TTSError:
            raise
        except Exception as e:
            wait = (2 ** attempt) * 3
            if attempt < max_retry:
                time.sleep(wait)
            else:
                return None
    return None


def synthesize_voice(
    voice: str = "mini",
    custom_voice_id: Optional[str] = None,
) -> str:
    """
    解析声音 ID（mini / max / custom_voice_id 直接给）
    """
    if custom_voice_id:
        return custom_voice_id
    if voice in DEFAULT_VOICES:
        return DEFAULT_VOICES[voice]["voice_id"]
    raise TTSError(f"unknown voice: {voice}")


def stream_synthesize(
    sentences: List[str],
    voice: str = "mini",
    custom_voice_id: Optional[str] = None,
    api_key: Optional[str] = None,
    cache_dir: Optional[Path] = None,
) -> Iterator[Dict[str, Any]]:
    """
    单路顺序合成（避 RPM 限流）+ 断点续传

    Yields:
        {"type": "audio_chunk", "hex": str, "index": int} ← 一句合成
        {"type": "tts_complete", "success": int, "fail": int} ← 完成
        {"type": "error", "message": str}                    ← 错误
    """
    api_key = resolve_api_key(api_key)
    voice_id = synthesize_voice(voice, custom_voice_id)

    if cache_dir is None:
        cache_dir = Path.cwd() / ".aipodcast_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    fail = 0
    for i, text in enumerate(sentences, 1):
        # cache key 改用 voice + text md5(原 bug 是按序号 chunk_{i:04d},导致旧 audio 被误用;
        # 后续又发现换 voice 时也会读旧 audio,所以加 voice 维度)
        cache_file = cache_dir / f"chunk_{_cache_key_for(text, voice)}.hex"
        if cache_file.exists():
            hex_str = cache_file.read_text()
            success += 1
            yield {"type": "audio_chunk", "hex": hex_str, "index": i, "cached": True}
            continue
        hex_str = _tts_one(text, voice_id, api_key)
        if hex_str:
            cache_file.write_text(hex_str)
            success += 1
            yield {"type": "audio_chunk", "hex": hex_str, "index": i, "cached": False}
        else:
            fail += 1
            yield {"type": "audio_error", "index": i, "text": text}
        # 单路 + 2 秒节流（避 RPM 限流）
        time.sleep(2.0)

    yield {"type": "tts_complete", "success": success, "fail": fail}


def concatenate_chunks(hex_list: List[str], output_path: str) -> tuple[str, float]:
    """
    把 hex chunks 拼成一个 MP3 文件
    用 pydub 解码 + 拼接 + 重新 export（保证 MP3 帧结构正确）

    Returns:
        (output_path, duration_s)
    """
    if not hex_list:
        raise TTSError("no audio chunks to concatenate")

    from pydub import AudioSegment
    import io

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 解码每个 hex chunk → AudioSegment → append
    combined = AudioSegment.empty()
    for h in hex_list:
        if not h:
            continue
        audio_bytes = bytes.fromhex(h)
        seg = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
        combined += seg

    # 重新 export MP3（pydub 会生成单文件可解析的 MP3）
    combined.export(output_path, format="mp3", bitrate="128k")
    return output_path, len(combined) / 1000.0
