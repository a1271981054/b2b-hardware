# B 端产品经理双人播客

把 `B端产品经理问题集.md` 中不断新增的知识点，自动扫描成独立剧集，再用小米 MiMo TTS 合成双人中文播客。

## 已生成 4 集完整音频

- 101：B端硬件产品经理：职责、KPI 与商业嗅觉（约 37.7 分钟）
- 102：客户价值地图与采购决策链（约 37.0 分钟）
- 103：机会、行业、商业模式与定价（约 36.1 分钟）
- 104：需求优先级与交付阶段门（约 37.5 分钟）

本地播放列表：[index.html](index.html) / [index.md](index.md)

当前音色采用小米 `mimo-v2.5-tts-voicedesign` 定制：

- 主持人：30 岁左右女性，知性温暖、积极、语速稍快
- 嘉宾：30 多岁男性，成熟积极、极具分享欲、语速更快

1 分钟音色示例：[sample-voice.mp3](sample-voice.mp3)

## 重新渲染

```bash
cd "/Users/zlearn/Documents/B端硬件"

# 依次渲染 4 集完整音频
python3 ~/.codex/skills/b2b-podcast/scripts/podcast.py render --episode 101
python3 ~/.codex/skills/b2b-podcast/scripts/podcast.py render --episode 102
python3 ~/.codex/skills/b2b-podcast/scripts/podcast.py render --episode 103
python3 ~/.codex/skills/b2b-podcast/scripts/podcast.py render --episode 104
```

已生成的音频分片会复用；更换音色后，脚本会检测到音色配置变化并自动重新合成。

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
python3 ~/.codex/skills/b2b-podcast/scripts/podcast.py render --episode 101

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
