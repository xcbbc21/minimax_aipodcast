"""
script_generator.py - LLM 流式生成单口脚本
从 backend/podcast_generator.py 拆出
"""
import logging
from typing import Iterator, Dict, Any, Optional
from .config import resolve_api_key, MODELS, TIMEOUTS
from .exceptions import APIError

logger = logging.getLogger(__name__)


SINGLE_SPEAKER_PROMPT_TEMPLATE = """你是一个专业的播客脚本编写助手。请基于以下材料，生成一段 {duration_min}-{duration_max} 分钟的**单人口播**脚本。

要求：
1. 风格：连续口播，亲切自然，像在跟一个朋友讲解
2. 说话人：只有 Mini 一个，**不要使用 Speaker1/Speaker2 双人对谈**
3. 文本要自然，包含适当的重复、语气词、停顿等真人讲解特征
4. 每句话单独一行，格式为：Mini: 内容
5. 严格忠于原文：人物名字、具体数字、关键概念、原文措辞不能改
6. 时长 {duration_min}-{duration_max} 分钟
7. 对话内容中不能包含（笑）（停顿）（思考）等动作、心理活动或场景描述

材料内容：
{content}

请开始生成播客脚本。"""


def stream_script(
    content: str,
    duration_min: int = 22,
    duration_max: int = 25,
    api_key: Optional[str] = None,
) -> Iterator[Dict[str, Any]]:
    """
    流式生成单口脚本

    Yields:
        {"type": "script_chunk", "content": str}     ← 脚本片段
        {"type": "script_complete", "trace_id": str} ← 完成
        {"type": "error", "message": str}            ← 错误
    """
    import requests
    import json

    api_key = resolve_api_key(api_key)
    url = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    prompt = SINGLE_SPEAKER_PROMPT_TEMPLATE.format(
        duration_min=duration_min,
        duration_max=duration_max,
        content=content,
    )
    payload = {
        "model": MODELS["text"],
        "messages": [
            {"role": "system", "name": "MiniMax AI", "content": "你是 MiniMax AI 播客脚本编写助手。"},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
    }

    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=TIMEOUTS["script_generation"]) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    yield {"type": "script_complete", "trace_id": None}
                    return
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if "choices" in obj:
                    delta = obj["choices"][0].get("delta", {})
                    chunk = delta.get("content", "")
                    if chunk:
                        yield {"type": "script_chunk", "content": chunk}
    except Exception as e:
        logger.error(f"script generation failed: {e}")
        yield {"type": "error", "message": str(e)}
        return


def generate_script(
    content: str,
    duration_min: int = 22,
    duration_max: int = 25,
    api_key: Optional[str] = None,
) -> str:
    """
    一次性返回完整脚本
    """
    chunks = []
    for event in stream_script(content, duration_min, duration_max, api_key):
        if event["type"] == "script_chunk":
            chunks.append(event["content"])
        elif event["type"] == "error":
            raise APIError(f"script generation failed: {event['message']}")
    return "".join(chunks)


def parse_script_lines(script: str) -> list[str]:
    """解析 'Mini: xxx' 每行，提取纯文本内容"""
    sentences = []
    for line in script.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("Mini:"):
            txt = line[5:].strip()
            if txt:
                sentences.append(txt)
        elif ":" not in line and len(line) > 5:
            sentences.append(line)
    return sentences
