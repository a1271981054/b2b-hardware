# B 端硬件 PM 教学视频管道

把 `课堂笔记-从零学B端硬件PM.md` 中每个已完成课时做成一条 16:9 教学视频：老师口语讲稿 → 小米 MiMo 配音 → HyperFrames HTML 动画 → FFmpeg 渲染 MP4。

## 常用命令

```bash
cd "/Users/zlearn/Documents/B端硬件"

# 查看文档里有哪些课时，以及哪些是新增/变更
python3 video/scripts/build_video.py scan

# 生成/更新课时目录与 source.md
python3 video/scripts/build_video.py prepare

# 合成旁白 + 逐字时间轴（自动跳过未变化课时）
python3 video/scripts/build_video.py tts --all

# 重新生成 HTML 合成与字幕
python3 video/scripts/build_video.py compose --all

# lint + validate + 渲染 MP4（需要 PATH 里先找到带 libx264 的 ffmpeg）
PATH="/opt/homebrew/bin:$PATH" python3 video/scripts/build_video.py render --all

# 生成播放列表 video/index.html / index.md
python3 video/scripts/build_video.py index
```

## 目录结构

- `config.json`：MiMo API、老师音色、分辨率、帧率、转写参数
- `DESIGN.md`：全局视觉规范（楷体板书 + 宋体正文 + Menlo 标签）
- `lessons/<id>-<标题>/`：每课一个 HyperFrames 项目
  - `script.md`：老师讲稿，一行一句，格式 `老师: 台词 #关键词 @visual:xxx @note:短说明`
  - `narration.mp3`：MiMo 合成旁白（gitignored）
  - `timing.json`：每句真实起止时间
  - `transcript.json`：按句内字符等比例切分的确定性逐字时间戳
  - `index.html`：HyperFrames 合成（GSAP 动画 + 字幕 + 进度条）
  - `render/lesson-<id>.mp4`：最终视频（gitignored）
- `vendor/gsap.min.js`：本地 GSAP，保证渲染确定性

## 字幕说明

字幕文本直接来自讲稿，逐字时间戳按每句真实 TTS 时长做字符等比例切分，因此文本 100% 正确、句级对齐精确、可复现；不再依赖本地 Whisper 识别（中文识别质量不稳定）。

## 密钥

`video/.env` 存放 `MIMO_API_KEY`，已被 `.gitignore` 忽略，不进入版本库。
