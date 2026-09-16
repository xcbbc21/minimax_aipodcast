# aipodcast

**AI 单口播客生成器** — 给 AI Agent 用，从文本/PDF/网页生成单人口播 MP3。

基于 [minimax_aipodcast](https://github.com/mm-demo-collection/minimax_aipodcast) 改造，去掉 Web 端，专为 CLI 和 Python API 设计。

## ✨ 特性

- **三种输入源**：直接文本 / 文件（PDF/HTML/MD/TXT）/ 网页 URL
- **单口精读模式**：自动 LLM 生成 22-25 分钟单口脚本
- **两种声音**：mini（女，活泼亲切）/ max（男，稳重专业）
- **声音克隆**：从 10-30 秒参考音频克隆任意声音
- **AI Agent 友好**：
  - 明确退出码（0/1/2/3）
  - JSON 结构化输出（`--json`）
  - 进度回调（Python API）
  - 断点续传（hex cache 缓存）
- **限流友好**：单路顺序 TTS + 2 秒节流 + 限流时 30-45 秒退避（实测 0 失败）

## 📦 安装

```bash
cd ~/minimax_aipodcast
uv sync                    # uv 项目（pyproject.toml + uv.lock）
# 或
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install typer rich
```

## 🚀 快速开始

### CLI

```bash
# 直接文本
./venv/bin/python -m aipodcast.cli generate \
  --text "今天讲讲读书何以改变命运" \
  --output out.mp3

# 文件（PDF/HTML/MD/TXT 自动识别）
./venv/bin/python -m aipodcast.cli generate \
  --file paper.pdf \
  --output podcast.mp3

# 网页 URL
./venv/bin/python -m aipodcast.cli generate \
  --url "https://example.com/article.html" \
  --output podcast.mp3

# 完整选项
./venv/bin/python -m aipodcast.cli generate \
  --text "..." \
  --output out.mp3 \
  --voice mini \                # mini / max / custom
  --language zh \               # zh / en / ja / es / ar
  --duration-min 22 \
  --duration-max 25 \
  --json \                      # JSON 输出（agent 友好）
  --no-progress                 # 静默模式

# 声音克隆（10-30 秒参考音频）
./venv/bin/python -m aipodcast.cli clone voice ref.wav
# 输出 voice_id，后续用：
./venv/bin/python -m aipodcast.cli generate \
  --text "..." \
  --voice custom \
  --custom-voice-id customVoice_xxxxxxxx_1234

# 看可用声音
./venv/bin/python -m aipodcast.cli voices list

# 看当前配置
./venv/bin/python -m aipodcast.cli config show
```

### Python API

```python
from aipodcast import generate_podcast, clone_voice, PodcastResult

# 1. 文本输入
result = generate_podcast(
    text="今天讲讲读书何以改变命运...",
    output="out.mp3",
    voice="mini",
    language="zh",
    duration_min=22,
    duration_max=25,
)
print(f"✓ {result.audio_path} ({result.duration_s:.0f}s)")

# 2. 文件输入
result = generate_podcast(file="paper.pdf", output="paper_podcast.mp3")

# 3. URL 输入
result = generate_podcast(
    url="https://example.com/article",
    output="article_podcast.mp3",
)

# 4. 带进度回调
def on_progress(stage: str, message: str):
    print(f"[{stage}] {message}")

result = generate_podcast(
    text="...",
    output="out.mp3",
    on_progress=on_progress,
)

# 5. 声音克隆
clone_result = clone_voice(
    audio_file_path="ref.wav",
    sample_text="您好，我是测试声音。",
)
voice_id = clone_result["voice_id"]
# 用克隆的声音
result = generate_podcast(
    text="...",
    voice="custom",
    custom_voice_id=voice_id,
    output="out.mp3",
)
```

### 环境变量

```bash
export AIPODCAST_API_KEY="sk-cp-..."  # 显式 API Key
# 或
export MINIMAX_API_KEY="sk-cp-..."    # 兼容旧名
export AIPODCAST_LOG_LEVEL="DEBUG"    # 调试日志
```

## 📁 项目结构

```
minimax_aipodcast/
├── aipodcast/                    # 主包
│   ├── __init__.py               # 公开 API
│   ├── cli.py                    # Typer CLI
│   ├── api.py                    # Python API（generate_podcast）
│   ├── pipeline.py               # 核心编排
│   ├── script_generator.py       # LLM 流式生成脚本
│   ├── tts_synthesizer.py        # TTS 流式合成
│   ├── speaker_clone.py          # 声音克隆
│   ├── content_parser.py         # PDF/URL 解析
│   ├── audio_utils.py            # 音频处理
│   ├── config.py                 # 配置（API key、声音、BGM）
│   ├── output.py                 # 输出路径管理
│   └── exceptions.py             # 自定义异常
├── examples/                     # 使用示例
├── tests/                        # 测试
├── pyproject.toml                # uv 项目配置
└── venv/                         # Python venv（Py 3.10-3.12）
```

## 🐛 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 输入错误 / 配置错误 |
| 2 | MiniMax API 错误 / TTS 错误 / 音频处理错误 |
| 3 | RPM 限流（多次重试后仍失败） |

## 📊 已知限制

- **Python 版本**：3.10 - 3.12（3.13+ 移除了 `audioop`，pydub 0.25 不兼容）
- **RPM 限流**：单路顺序 2 秒节流，~4-5 分钟/30 句
- **中文字数 → 时长**：~200 字/分钟朗读速度

## 🔄 与 minimax_aipodcast 关系

| | minimax_aipodcast | aipodcast |
|---|---|---|
| 形态 | Web App (Flask + React) | Python CLI + API |
| 输入 | 浏览器表单 | CLI / Python 函数 |
| 输出 | Web 播放器 | MP3 文件 |
| 适合 | 人类交互 | AI Agent |

底层用同一套 MiniMax TTS API（同 `voice_id`、同模型 `speech-2.8-hd`、同 `MiniMax-M3` LLM）。

## 📜 License

MIT
