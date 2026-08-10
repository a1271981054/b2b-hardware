# B 端产品经理双人播客

把 `B端产品经理问题集.md` 中不断新增的知识点，自动扫描成独立剧集，再用小米 MiMo TTS 合成双人中文播客。

## 已生成

- 001：Q1. B 端硬件产品经理的核心职责边界是什么？KPI 怎么定？（约 4 分 46 秒）
- 003：Q1 追问 2. JTBD 框架详细讲解（约 5 分 34 秒）

本地播放列表：打开 `podcast/index.html` 即可直接播放已生成的剧集。

## 常用命令

```bash
cd "/Users/zlearn/Documents/B端硬件"

# 查看新增/更新的知识点
python3 ~/.codex/skills/b2b-podcast/scripts/podcast.py scan

# 为新增知识点建立剧集目录和写稿提示
python3 ~/.codex/skills/b2b-podcast/scripts/podcast.py prepare

# 写稿：编辑 podcast/episodes/<id>/script.md
# 格式：主持人: ... 或 嘉宾: ...

# 渲染一个剧集
python3 ~/.codex/skills/b2b-podcast/scripts/podcast.py render --episode 001

# 只渲染还没有音频的剧集
python3 ~/.codex/skills/b2b-podcast/scripts/podcast.py render --new

# 查看剧集和时长
python3 ~/.codex/skills/b2b-podcast/scripts/podcast.py list
```

## 开源参考

本项目组合并改造了以下 MIT 开源项目：

- [aprilvkuo/podcast-skill](https://github.com/aprilvkuo/podcast-skill)：双人对话稿、分段 TTS、ffmpeg 拼接和播客发布思路。
- [StarDuster/paper2podcast-skill](https://github.com/StarDuster/paper2podcast-skill)：中文双人技术播客的分轮 TTS 渲染思路。
- [zhouchang1988/xiaomi-tts-chapters](https://github.com/zhouchang1988/xiaomi-tts-chapters)：小米 MiMo TTS 分段合成和断点续传。
- [zhbcher/xiaomi-tts](https://github.com/zhbcher/xiaomi-tts)：小米 TTS OpenAI 兼容接口封装。
- [yshtcn/xiaomiTTS2OpenAITTSAPI](https://github.com/yshtcn/xiaomiTTS2OpenAITTSAPI)：小米 TTS 到 OpenAI TTS 兼容代理。
