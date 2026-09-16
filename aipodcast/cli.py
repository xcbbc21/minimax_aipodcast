"""
cli.py - Typer CLI 入口（AI Agent 友好）
"""
import sys
import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .api import generate_podcast, clone_voice, generate_voice_id
from .config import DEFAULT_VOICES, resolve_api_key
from .exceptions import AIPodcastError, ConfigError, APIKeyError, RateLimitError, TTSError, InputError
from .pipeline import PodcastResult

app = typer.Typer(
    name="aipodcast",
    help="AI 单口播客生成器（CLI + Python API，给 AI Agent 用）",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)

# ========== 顶层选项 ==========
def _setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="DEBUG 日志"),
    log_file: Optional[Path] = typer.Option(None, "--log-file", help="日志文件"),
):
    """aipodcast - AI 单口播客生成器"""
    _setup_logging(verbose)
    if log_file:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logging.getLogger().addHandler(handler)


# ========== generate 子命令 ==========
generate_app = typer.Typer(help="生成单口播客")
app.add_typer(generate_app, name="generate")


def _progress_cb(stage: str, message: str):
    err_console.print(f"  [{stage}] {message}")


@generate_app.callback(invoke_without_command=True)
def generate_main(
    ctx: typer.Context,
    text: Optional[str] = typer.Option(None, "--text", "-t", help="直接传入文本"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="文件路径（.pdf/.html/.md/.txt）"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="网页 URL"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出 MP3 路径"),
    voice: str = typer.Option("mini", "--voice", help="声音: mini (女) / max (男) / 自定义 voice_id"),
    language: str = typer.Option("zh", "--language", "-l", help="语言: zh/en/ja 等"),
    duration_min: int = typer.Option(22, "--duration-min", help="目标最短时长（分钟）"),
    duration_max: int = typer.Option(25, "--duration-max", help="目标最长时长（分钟）"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="MiniMax API Key（或环境变量）"),
    json_output: bool = typer.Option(False, "--json", help="JSON 输出到 stdout"),
    no_progress: bool = typer.Option(False, "--no-progress", help="不打印进度"),
    custom_voice_id: Optional[str] = typer.Option(None, "--custom-voice-id", help="已克隆的 voice_id（声音克隆后用）"),
    no_rescript: bool = typer.Option(False, "--no-rescript", help="跳过 LLM 重写,直接 TTS 化输入内容"),
):
    """生成单口播客"""
    try:
        # 进度回调
        on_progress = None if no_progress or json_output else _progress_cb

        result = generate_podcast(
            text=text,
            file=str(file) if file else None,
            url=url,
            output=str(output) if output else None,
            voice=voice if not custom_voice_id else "custom",
            custom_voice_id=custom_voice_id,
            language=language,
            duration_min=duration_min,
            duration_max=duration_max,
            api_key=api_key,
            on_progress=on_progress,
            skip_rescript=no_rescript,
        )

        if json_output:
            # JSON 到 stdout
            print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        else:
            if result.success:
                console.print(f"\n[green]✓ 成功[/green] {result.audio_path}")
                console.print(f"  时长: ~{result.duration_s:.0f} 秒")
                console.print(f"  脚本: {result.script_chars} 字符 / {result.script_sentences} 句")
                console.print(f"  声音: {result.voice} ({language})")
            else:
                console.print(f"\n[red]✗ 失败[/red] {result.error}", err=True)
                raise typer.Exit(1)
    except AIPodcastError as e:
        if json_output:
            err_console.print(json.dumps({"error": e.message, "type": type(e).__name__}, ensure_ascii=False))
        else:
            err_console.print(f"[red]{type(e).__name__}[/red]: {e.message}")
        raise typer.Exit(e.exit_code)
    except Exception as e:
        if json_output:
            err_console.print(json.dumps({"error": str(e), "type": "UnexpectedError"}, ensure_ascii=False))
        else:
            err_console.print(f"[red]UnexpectedError[/red]: {e}")
        raise typer.Exit(1)


# ========== voices 子命令 ==========
voices_app = typer.Typer(help="声音管理")
app.add_typer(voices_app, name="voices")


@voices_app.command("list")
def voices_list(
    json_output: bool = typer.Option(False, "--json", help="JSON 输出"),
):
    """列出所有可用声音"""
    if json_output:
        print(json.dumps(DEFAULT_VOICES, ensure_ascii=False, indent=2))
    else:
        for name, info in DEFAULT_VOICES.items():
            console.print(f"[cyan]{name}[/cyan] ({info['gender']}) — {info['description']}")
            console.print(f"  voice_id: {info['voice_id']}")


# ========== clone 子命令 ==========
clone_app = typer.Typer(help="声音克隆")
app.add_typer(clone_app, name="clone")


@clone_app.command("voice")
def clone_voice_cmd(
    audio: Path = typer.Argument(..., help="参考音频文件（10-30 秒 WAV/MP3）"),
    voice_id: Optional[str] = typer.Option(None, "--id", help="指定 voice_id（不指定自动生成）"),
    sample_text: str = typer.Option("您好，我是客户经理李娜。", "--text", help="试听文本"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="MiniMax API Key"),
    json_output: bool = typer.Option(False, "--json", help="JSON 输出"),
):
    """从参考音频克隆声音"""
    try:
        result = clone_voice(
            audio_file_path=str(audio),
            sample_text=sample_text,
            voice_id=voice_id,
            api_key=api_key,
        )
        if json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            console.print(f"\n[green]✓ 克隆成功[/green]")
            console.print(f"  voice_id: {result['voice_id']}")
            console.print(f"  trace_id: {result['trace_id']}")
            console.print(f"  后续使用: --voice custom --custom-voice-id {result['voice_id']}")
    except AIPodcastError as e:
        if json_output:
            err_console.print(json.dumps({"error": e.message, "type": type(e).__name__}, ensure_ascii=False))
        else:
            err_console.print(f"[red]{type(e).__name__}[/red]: {e.message}")
        raise typer.Exit(e.exit_code)


# ========== config 子命令 ==========
config_app = typer.Typer(help="配置管理")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(
    json_output: bool = typer.Option(False, "--json", help="JSON 输出"),
):
    """显示当前配置"""
    info = {
        "api_key": "***" + resolve_api_key()[-8:] if resolve_api_key() else "missing",
        "voices": list(DEFAULT_VOICES.keys()),
    }
    if json_output:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        console.print(f"API Key: {info['api_key']}")
        console.print(f"Voices: {', '.join(info['voices'])}")


if __name__ == "__main__":
    app()
