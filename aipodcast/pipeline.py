"""
pipeline.py - 核心编排：input → parser → LLM → TTS → output
"""
import logging
import re
import time
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field
from .config import PODCAST_CONFIG, DEFAULT_OUTPUT_DIR
from .content_parser import content_parser
from .script_generator import generate_script, parse_script_lines
from .tts_synthesizer import stream_synthesize, concatenate_chunks
from .exceptions import InputError
from .output import default_output_path

logger = logging.getLogger(__name__)


def _split_into_sentences(text: str) -> list[str]:
    """
    智能切句(用于 --no-rescript 路径)
    按中英文标点(。!?;)切,过滤空白/标题行,合并过短句(>20 字合并到下一段)
    """
    # 去 markdown 标题(以 # 开头)和空行
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        lines.append(line)
    joined = " ".join(lines)

    # 按中英文终止标点切(保留标点)
    parts = re.split(r'(?<=[。!?;])\s*', joined)
    sentences = []
    for p in parts:
        p = p.strip()
        if not p or len(p) < 2:
            continue
        # 过短句(<8 字)合并到上一句
        if sentences and len(sentences[-1]) < 8:
            sentences[-1] = sentences[-1] + p
        else:
            sentences.append(p)
    return sentences


@dataclass
class PodcastResult:
    """AI Agent 友好的结果对象"""
    success: bool
    audio_path: str
    duration_s: float = 0.0
    script_chars: int = 0
    script_sentences: int = 0
    voice: str = "mini"
    language: str = "zh"
    trace_id: Optional[str] = None
    error: Optional[str] = None


ProgressCallback = Callable[[str, str], None]
"""
Progress callback signature: callback(stage: str, message: str)
stages: parsing / scripting / tts / mixing / done / error
"""


def _detect_and_parse(
    text: Optional[str] = None,
    file: Optional[str] = None,
    url: Optional[str] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> str:
    """
    三种输入源 → 文本内容
    """
    sources = [s for s in [text, file, url] if s]
    if len(sources) != 1:
        raise InputError(
            f"必须且只能传一种输入源（text/file/url），你传了 {len(sources)} 个"
        )

    if text is not None:
        if on_progress:
            on_progress("parsing", "使用直接传入的文本")
        return text

    if file is not None:
        path = Path(file)
        if not path.exists():
            raise InputError(f"文件不存在: {file}")
        if path.suffix.lower() == ".pdf":
            if on_progress:
                on_progress("parsing", f"解析 PDF: {file}")
            result = content_parser.parse_pdf(str(path))
        elif path.suffix.lower() in [".html", ".htm"]:
            if on_progress:
                on_progress("parsing", f"解析 HTML: {file}")
            result = content_parser.parse_file(str(path))
        elif path.suffix.lower() in [".md", ".txt"]:
            if on_progress:
                on_progress("parsing", f"读取文本: {file}")
            content = path.read_text(encoding="utf-8")
            return content
        else:
            raise InputError(f"不支持的文件类型: {path.suffix}")
        if not result.get("success"):
            raise InputError(f"解析失败: {result.get('error', 'unknown')}")
        return result["content"]

    if url is not None:
        if on_progress:
            on_progress("parsing", f"抓取 URL: {url}")
        result = content_parser.parse_url(url)
        if not result.get("success"):
            raise InputError(f"URL 抓取失败: {result.get('error', 'unknown')}")
        return result["content"]

    raise InputError("no input source provided")  # 不会到这里


def run_pipeline(
    text: Optional[str] = None,
    file: Optional[str] = None,
    url: Optional[str] = None,
    output: Optional[str] = None,
    voice: str = "mini",
    custom_voice_id: Optional[str] = None,
    language: str = "zh",
    duration_min: int = PODCAST_CONFIG["target_duration_min"],
    duration_max: int = PODCAST_CONFIG["target_duration_max"],
    api_key: Optional[str] = None,
    on_progress: Optional[ProgressCallback] = None,
    skip_rescript: bool = False,
) -> PodcastResult:
    """
    单口播客生成全流程

    阶段：
      1. parsing - 输入源 → 文本
      2. scripting - LLM 生成单口脚本
      3. tts - TTS 流式合成
      4. done - 完成
    """
    try:
        # 1) 解析输入
        content = _detect_and_parse(text=text, file=file, url=url, on_progress=on_progress)

        # 2) 生成脚本
        if skip_rescript:
            # 跳过 LLM,直接用输入内容作为脚本
            if on_progress:
                on_progress("scripting", "跳过 LLM,直接用输入内容作为脚本")
            script = content
            sentences = _split_into_sentences(script)
        else:
            if on_progress:
                on_progress("scripting", f"LLM 生成 {duration_min}-{duration_max} 分钟单口脚本")
            script = generate_script(
                content=content,
                duration_min=duration_min,
                duration_max=duration_max,
                api_key=api_key,
            )
            sentences = parse_script_lines(script)
        if not sentences:
            raise InputError("LLM 没生成任何句子")
        if on_progress:
            on_progress("scripting", f"脚本生成完成: {len(script)} 字符 / {len(sentences)} 句")

        # 3) TTS 合成
        if on_progress:
            on_progress("tts", f"TTS 合成 {len(sentences)} 句（{voice}）")
        hex_chunks = []
        for event in stream_synthesize(
            sentences=sentences,
            voice=voice,
            custom_voice_id=custom_voice_id,
            api_key=api_key,
        ):
            if event["type"] == "audio_chunk":
                hex_chunks.append(event["hex"])
                if on_progress and event["index"] % 10 == 0:
                    on_progress("tts", f"已合成 {event['index']}/{len(sentences)} 句")
            elif event["type"] == "tts_complete":
                if on_progress:
                    on_progress("tts", f"TTS 完成: {event['success']} 成功 / {event['fail']} 失败")
                if event["fail"] > 0 and event["success"] == 0:
                    raise InputError(f"TTS 全部失败 ({event['fail']} 句)")

        # 4) 输出
        if output is None:
            source = text or file or url or "podcast"
            output = str(default_output_path(input_source=source, voice=voice, language=language))
        output, actual_duration = concatenate_chunks(hex_chunks, output)

        if on_progress:
            on_progress("done", f"生成完成: {output} ({actual_duration:.0f}s)")

        return PodcastResult(
            success=True,
            audio_path=output,
            duration_s=actual_duration,
            script_chars=len(script),
            script_sentences=len(sentences),
            voice=voice,
            language=language,
        )
    except Exception as e:
        if on_progress:
            on_progress("error", str(e))
        return PodcastResult(
            success=False,
            audio_path=output or "",
            error=str(e),
            voice=voice,
            language=language,
        )
