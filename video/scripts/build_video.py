#!/usr/bin/env python3
"""B端硬件PM教学视频管道：扫描课时 -> 老师讲稿 -> MiMo TTS -> HyperFrames 合成 -> MP4。"""

import argparse
import base64
import copy
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_CONFIG = {
    "source_md": "课堂笔记-从零学B端硬件PM.md",
    "output_dir": "video",
    "api": {
        "base_url": "https://api.xiaomimimo.com/v1",
        "model": "mimo-v2.5-tts-voicedesign",
    },
    "voice": {
        "label": "老师",
        "voice_design": "一位30岁左右的女性，声音积极、热情、有感染力，语速偏快，吐字清晰，语气亲切耐心，像一位给完全零基础的学生讲生活常识的老师。",
    },
    "max_chars_per_request": 180,
    "silence_seconds": 0.35,
    "resolution": {"width": 1920, "height": 1080},
    "fps": 30,
    "render_quality": "high",
    "transcribe_model": "small",
}


VISUALS = {
    "teacher": ("👩‍🏫", "老师开讲", ""),
    "card": ("💳", "智能卡", ""),
    "reader": ("🚪", "读卡器", ""),
    "nfc": ("📶", "近距离对话", ""),
    "emv": ("🌐", "全球刷卡规矩", ""),
    "cert": ("✅", "合格证", ""),
    "pos": ("🛒", "收银台", ""),
    "gate": ("🚇", "闸机", ""),
    "access": ("🏢", "门禁考勤", ""),
    "id": ("🗂️", "身份证件", ""),
    "module": ("⚙️", "读卡器模块", ""),
    "money": ("💰", "赚钱路子", ""),
    "chart": ("📈", "公司数字", ""),
    "interview": ("🎤", "面试串讲", ""),
    "bom": ("📋", "物料清单", ""),
    "mold": ("🥮", "开模", ""),
    "nre": ("💸", "一次性费用", ""),
    "moq": ("🏭", "最小起订量", ""),
    "evt": ("🍳", "先试做一锅", ""),
    "dvt": ("🧪", "反复试吃", ""),
    "pvt": ("📦", "稳定量产", ""),
    "oem": ("📝", "你写菜谱", ""),
    "odm": ("🍽️", "现成招牌菜", ""),
    "doc": ("📄", "产品文档", ""),
    "brd": ("💼", "给老板看", ""),
    "mrd": ("👥", "做给谁", ""),
    "prd": ("🛠️", "施工图纸", ""),
    "q": ("❓", "课后想一想", "q"),
    "star": ("⭐", "一句话记住", "final"),
    "light": ("💡", "换个说法", ""),
    "generic": ("📌", "记重点", ""),
}


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
LESSON_RE = re.compile(r"^第\s*(\d+)\s*课[：:]\s*(.+)$")
BEAT_RE = re.compile(r"^老师\s*[:：]\s*(.+)$")
KEYWORD_RE = re.compile(r"#([^#\s@]+)")
VISUAL_RE = re.compile(r"@visual:([A-Za-z0-9_-]+)")
NOTE_RE = re.compile(r"@note:(.+)$")


def log(message: str) -> None:
    print(message)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slugify(text: str, max_len: int = 60) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text).strip("-")
    return text[:max_len].rstrip("-")


def find_project_root(args) -> Path:
    if getattr(args, "project", None):
        return Path(args.project).expanduser().resolve()
    return Path.cwd()


def config_path(root: Path) -> Path:
    return root / "video" / "config.json"


def state_path(root: Path) -> Path:
    return root / "video" / "state.json"


def load_config(root: Path) -> dict:
    path = config_path(root)
    if not path.exists():
        sys.exit(f"未找到配置 {path}，请先运行 prepare")
    user_config = json.loads(path.read_text(encoding="utf-8"))
    config = copy.deepcopy(DEFAULT_CONFIG)
    for key, value in user_config.items():
        if key in ("api", "voice"):
            continue
        config[key] = value
    config["api"].update(user_config.get("api", {}))
    config["voice"].update(user_config.get("voice", {}))
    return config


def load_state(root: Path) -> dict:
    path = state_path(root)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"voice_sha256": "", "lessons": {}}


def save_state(root: Path, state: dict) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_api_key(root: Path) -> str:
    env_file = root / "video" / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("MIMO_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return os.environ.get("MIMO_API_KEY", "")


def voice_config_hash(config: dict) -> str:
    payload = json.dumps(
        {"model": config["api"]["model"], "voice": config["voice"]},
        ensure_ascii=False,
        sort_keys=True,
    )
    return sha256_text(payload)


def parse_lessons(source_path: Path) -> list:
    text = source_path.read_text(encoding="utf-8")
    lessons = []
    current = None
    for raw in text.splitlines():
        m = HEADING_RE.match(raw)
        if not m:
            if current is not None:
                current["content"].append(raw)
            continue
        level = len(m.group(1))
        heading = m.group(2).strip()
        lm = LESSON_RE.match(heading)
        if lm:
            if current is not None:
                lessons.append(current)
            current = {
                "num": int(lm.group(1)),
                "title": lm.group(2).strip(),
                "level": level,
                "part": "第一段" if level == 2 else "第二段",
                "content": [],
            }
        else:
            if current is not None and level <= current["level"]:
                lessons.append(current)
                current = None
    if current is not None:
        lessons.append(current)
    for idx, lesson in enumerate(lessons, 1):
        lesson["id"] = f"{idx:03d}"
        lesson["slug"] = slugify(lesson["title"])
        lesson["source"] = "\n".join(lesson["content"]).strip()
        lesson["source_sha256"] = sha256_text(lesson["title"] + "\n" + lesson["source"])
    return lessons


def parse_script(script_text: str) -> list:
    beats = []
    for raw in script_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        m = BEAT_RE.match(line)
        if not m:
            continue
        text = m.group(1).strip()
        keywords = KEYWORD_RE.findall(text)
        vm = VISUAL_RE.search(text)
        visual = vm.group(1) if vm else "generic"
        nm = NOTE_RE.search(text)
        note = nm.group(1).strip() if nm else ""
        text = VISUAL_RE.sub("", text)
        text = NOTE_RE.sub("", text)
        text = KEYWORD_RE.sub("", text)
        text = re.sub(r"\s{2,}", " ", text).strip(" #")
        if not text:
            continue
        beats.append({"text": text, "keywords": keywords, "visual": visual, "note": note})
    return beats


def split_text(text: str, max_chars: int) -> list:
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r"(?<=[。！？!?；;])", text)
    chunks = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(current) + len(sentence) <= max_chars:
            current += sentence
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(sentence) > max_chars:
            chunks.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        current = sentence
    if current:
        chunks.append(current)
    return chunks


def tts_request(api_key: str, config: dict, voice: dict, text: str) -> bytes:
    url = config["api"]["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": config["api"]["model"],
        "messages": [
            {"role": "user", "content": voice.get("voice_design", "")},
            {"role": "assistant", "content": text},
        ],
        "audio": {"format": "mp3"},
    }
    curl = subprocess.run(["which", "curl"], capture_output=True, text=True).stdout.strip()
    if not curl:
        sys.exit("未找到 curl，无法调用小米 TTS")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ips = ["124.251.34.38", "124.251.34.64"]
    last_error = None
    clean_env = {key: value for key, value in os.environ.items() if "proxy" not in key.lower()}
    for ip in ips:
        for attempt in range(4):
            cmd = [
                curl, "-sS",
                "--connect-timeout", "10",
                "--max-time", "120",
                "--retry", "5",
                "--retry-all-errors",
                "--retry-delay", "2",
                "--resolve", f"api.xiaomimimo.com:443:{ip}",
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {api_key}",
                "--data-binary", "@-",
                url,
            ]
            try:
                result = subprocess.run(cmd, input=body, capture_output=True, timeout=140, env=clean_env)
            except subprocess.TimeoutExpired as exc:
                last_error = exc
                time.sleep(2 ** attempt)
                continue
            if result.returncode != 0:
                last_error = RuntimeError(result.stderr.decode("utf-8", "ignore")[:300])
                time.sleep(2 ** attempt)
                continue
            try:
                data = json.loads(result.stdout.decode("utf-8", "ignore"))
            except ValueError:
                last_error = RuntimeError("小米 TTS 返回的不是 JSON")
                time.sleep(2 ** attempt)
                continue
            if "choices" in data:
                try:
                    audio = data["choices"][0]["message"]["audio"]["data"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise RuntimeError(f"小米 TTS 响应中没有音频数据: {result.stdout[:300]}") from exc
                return base64.b64decode(audio)
            error = data.get("error", {})
            message = error.get("message", str(data)[:200])
            if any(token in message for token in ("429", "500", "502", "503", "暂时", "繁忙")):
                last_error = RuntimeError(f"小米 TTS 暂时不可用: {message}")
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"小米 TTS 请求失败: {message}")
    raise RuntimeError(f"小米 TTS 重试后仍然失败: {last_error}")


def probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def make_silence(path: Path, seconds: float) -> None:
    if path.exists():
        return
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
        "-t", f"{seconds:.2f}",
        "-c:a", "libmp3lame", "-b:a", "128k",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def run_ffmpeg(cmd: list) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.exit(f"ffmpeg 执行失败:\n{result.stderr[-2000:]}")


def lesson_dir(root: Path, lesson: dict) -> Path:
    return root / "video" / "lessons" / f"{lesson['id']}-{lesson['slug']}"


def script_hash(root: Path, lesson: dict) -> str:
    path = lesson_dir(root, lesson) / "script.md"
    if not path.exists():
        return ""
    return sha256_text(path.read_text(encoding="utf-8"))


def lesson_status(lesson: dict, existing: dict, cur_script_hash: str) -> str:
    if not existing:
        return "NEW"
    if existing.get("source_sha256") != lesson["source_sha256"]:
        return "CHANGED"
    if existing.get("script_sha256") != cur_script_hash:
        return "CHANGED"
    return "OK"


def select_lessons(args, lessons: list, state: dict) -> list:
    targets = []
    for lesson in lessons:
        if getattr(args, "episode", None):
            if args.episode not in lesson["id"] and args.episode not in lesson["slug"]:
                continue
        existing = state["lessons"].get(lesson["id"], {})
        if getattr(args, "all", False) or getattr(args, "force", False):
            targets.append(lesson)
            continue
        if existing.get("source_sha256") != lesson["source_sha256"]:
            targets.append(lesson)
            continue
        if existing.get("script_sha256") != script_hash(find_project_root(args), lesson):
            targets.append(lesson)
            continue
    return targets


def render_lesson_audio(
    lesson: dict,
    config: dict,
    state: dict,
    root: Path,
    api_key: str,
    force: bool,
) -> bool:
    ep_dir = lesson_dir(root, lesson)
    script_path = ep_dir / "script.md"
    if not script_path.exists():
        return False
    script_text = script_path.read_text(encoding="utf-8")
    beats = parse_script(script_text)
    if not beats:
        log(f"[{lesson['id']}] 跳过：script.md 没有台词")
        return False
    cur_script_hash = sha256_text(script_text)
    cur_voice_hash = voice_config_hash(config)
    audio_path = ep_dir / "narration.mp3"
    existing = state["lessons"].get(lesson["id"], {})
    if (
        not force
        and existing.get("source_sha256") == lesson["source_sha256"]
        and existing.get("script_sha256") == cur_script_hash
        and existing.get("voice_sha256") == cur_voice_hash
        and audio_path.exists()
    ):
        log(f"[{lesson['id']}] 旁白已生成，跳过：{lesson['title']}")
        return True

    seg_dir = ep_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    silence_path = ep_dir / "silence.mp3"
    make_silence(silence_path, config["silence_seconds"])

    voice = config["voice"]
    chunks = []
    for idx, beat in enumerate(beats):
        for chunk_idx, chunk in enumerate(split_text(beat["text"], config["max_chars_per_request"])):
            seg_name = f"seg_{idx:03d}_{chunk_idx:02d}.mp3"
            chunks.append((idx, chunk, seg_dir / seg_name, seg_name))

    log(f"[{lesson['id']}] 开始合成 {len(chunks)} 个分片：{lesson['title']}")
    for _, chunk, seg_path, seg_name in chunks:
        meta_path = seg_path.with_suffix(".json")
        chunk_hash = sha256_text(f"{voice.get('voice_design')}\n{chunk}")
        meta = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if seg_path.exists() and meta.get("chunk_hash") == chunk_hash:
            log(f"  复用 {seg_name}")
            continue
        log(f"  合成 {seg_name} ({len(chunk)} 字)")
        audio_bytes = tts_request(api_key, config, voice, chunk)
        seg_path.write_bytes(audio_bytes)
        meta_path.write_text(
            json.dumps({"chunk_hash": chunk_hash}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        time.sleep(0.2)

    filelist = ep_dir / "filelist.txt"
    lines = []
    for _, _, seg_path, _ in chunks:
        lines.append(f"file '{seg_path.as_posix()}'")
        lines.append(f"file '{silence_path.as_posix()}'")
    filelist.write_text("\n".join(lines) + "\n", encoding="utf-8")

    tmp_audio = ep_dir / "narration.tmp.mp3"
    run_ffmpeg([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(filelist),
        "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "24000", "-ac", "1",
        str(tmp_audio),
    ])
    tmp_audio.replace(audio_path)

    duration = probe_duration(audio_path)
    timing = {"total": round(duration, 3), "beats": []}
    cursor = 0.0
    sil = config["silence_seconds"]
    for idx, beat in enumerate(beats):
        seg_name = f"seg_{idx:03d}_00.mp3"
        seg_path = seg_dir / seg_name
        d = probe_duration(seg_path)
        timing["beats"].append({
            "index": idx,
            "text": beat["text"],
            "keywords": beat["keywords"],
            "visual": beat["visual"],
            "note": beat["note"],
            "start": round(cursor, 3),
            "end": round(cursor + d, 3),
            "duration": round(d, 3),
        })
        cursor += d + sil
    (ep_dir / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    transcript_words = generate_transcript(timing["beats"])
    (ep_dir / "transcript.json").write_text(
        json.dumps(transcript_words, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    state["lessons"][lesson["id"]] = {
        "id": lesson["id"],
        "title": lesson["title"],
        "slug": lesson["slug"],
        "part": lesson["part"],
        "source_sha256": lesson["source_sha256"],
        "script_sha256": cur_script_hash,
        "voice_sha256": cur_voice_hash,
        "audio_duration": round(duration, 1),
        "audio": str(audio_path.relative_to(root)),
    }
    state["voice_sha256"] = cur_voice_hash
    save_state(root, state)
    log(f"[{lesson['id']}] 旁白完成：{audio_path} ({duration:.1f}s)")
    return True


def transcribe_lesson(root: Path, lesson: dict, config: dict, force: bool = False) -> bool:
    ep_dir = lesson_dir(root, lesson)
    timing_path = ep_dir / "timing.json"
    transcript_path = ep_dir / "transcript.json"
    if not timing_path.exists():
        return False
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    words = generate_transcript(timing["beats"])
    transcript_path.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
    state = load_state(root)
    entry = state["lessons"].get(lesson["id"], {})
    entry["transcript_sha256"] = entry.get("script_sha256", "")
    state["lessons"][lesson["id"]] = entry
    save_state(root, state)
    log(f"[{lesson['id']}] 逐字时间轴生成完成：{len(words)} 个字符")
    return True


def generate_transcript(beats: list) -> list:
    """按句内字符等比例切分时间轴，生成确定性的逐字时间戳。"""
    words = []
    for beat in beats:
        text = beat["text"]
        span = max(beat["end"] - beat["start"] - 0.24, 0.5)
        start_offset = beat["start"] + 0.12
        total = max(len(text), 1)
        for idx, ch in enumerate(text):
            ch_start = start_offset + span * idx / total
            ch_end = start_offset + span * (idx + 1) / total
            words.append({"text": ch, "start": round(ch_start, 3), "end": round(ch_end, 3)})
    return words


def group_captions(words: list, beats: list) -> list:
    if not words:
        return [
            {"index": idx, "start": round(b["start"] + 0.12, 3), "end": round(b["end"] - 0.03, 3), "text": b["text"]}
            for idx, b in enumerate(beats)
        ]
    groups = []
    current = None

    def flush():
        nonlocal current
        if current and current["texts"]:
            groups.append({
                "index": len(groups),
                "start": round(current["start"], 3),
                "end": round(current["end"], 3),
                "text": "".join(current["texts"]),
            })
        current = None

    for word in words:
        text = word["text"].strip()
        if not text:
            continue
        start = word["start"]
        end = word["end"]
        if current is None:
            current = {"texts": [], "chars": 0, "start": start, "end": end}
        if current["chars"] + len(text) > 12 or (start - current["end"] > 0.45):
            flush()
            current = {"texts": [], "chars": 0, "start": start, "end": end}
        current["texts"].append(text)
        current["chars"] += len(text)
        current["end"] = max(current["end"], end)
    flush()
    return groups


COMPOSE_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<title>__TITLE__</title>
<style>
@font-face { font-family: "Kaiti SC"; src: local("Kaiti SC"); }
@font-face { font-family: "Songti SC"; src: local("Songti SC"); }
@font-face { font-family: "STSong"; src: local("STSong"); }
@font-face { font-family: "SimSun"; src: local("SimSun"); }
@font-face { font-family: "Menlo"; src: local("Menlo"); }
html, body { margin: 0; padding: 0; width: 1920px; height: 1080px; overflow: hidden; background: #F6F1E7; }
* { box-sizing: border-box; }
body { font-family: "Songti SC", "STSong", "SimSun", serif; color: #22242A; }
.scene { position: absolute; top: 0; left: 0; width: 1920px; height: 1080px; overflow: hidden; background: #F6F1E7; z-index: 1; }
#scene-000 { z-index: 2; }
.scene:not(#scene-000) { opacity: 0; }
.ghost { position: absolute; top: 70px; right: 70px; font-family: "Kaiti SC", "Songti SC", serif; font-size: 280px; font-weight: 900; color: #22242A; opacity: 0.05; line-height: 1; pointer-events: none; max-width: 720px; overflow: hidden; }
.bar-a { position: absolute; top: 0; left: 0; width: 1920px; height: 10px; background: #0E6E66; }
.bar-b { position: absolute; top: 178px; left: 96px; width: 84px; height: 8px; background: #E8871E; border-radius: 4px; }
.tag { position: absolute; top: 52px; left: 96px; font-family: "Menlo", "Songti SC", monospace; font-size: 28px; font-weight: 700; color: #0E6E66; }
.counter { position: absolute; top: 52px; right: 96px; font-family: "Menlo", monospace; font-size: 28px; font-weight: 700; color: #8A8272; }
.keyword { position: absolute; top: 214px; left: 96px; width: 920px; font-family: "Kaiti SC", "Songti SC", serif; font-size: 92px; font-weight: 900; line-height: 1.14; color: #22242A; }
.kw-accent { color: #0E6E66; }
.kw-plus { color: #E8871E; }
.note { position: absolute; top: 486px; left: 96px; width: 900px; font-size: 40px; line-height: 1.42; color: #3E4A52; }
.vpanel { position: absolute; top: 220px; right: 120px; width: 700px; height: 560px; background: #F7E4C8; border: 4px solid #E8871E; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 26px; }
.vpanel.q { background: #F6DDD7; border-color: #C75B45; }
.vpanel.final { background: #DDEAE4; border-color: #0E6E66; }
.v-emoji { font-size: 150px; line-height: 1; }
.v-label { font-family: "Kaiti SC", "Songti SC", serif; font-size: 40px; font-weight: 900; color: #22242A; }
.v-note { font-size: 30px; color: #7A5B28; }
.caption { position: absolute; left: 96px; right: 96px; bottom: 84px; min-height: 118px; padding: 22px 38px; background: #22242A; color: #F6F1E7; border-radius: 8px; display: flex; align-items: center; font-size: 34px; line-height: 1.5; z-index: 20; opacity: 0; }
#progress { position: absolute; left: 96px; right: 96px; bottom: 42px; height: 6px; background: #D9CDB8; border-radius: 3px; z-index: 21; }
#progress-fill { height: 6px; background: #0E6E66; border-radius: 3px; transform-origin: left center; transform: scaleX(0); }
#outro { position: absolute; top: 0; left: 0; width: 1920px; height: 1080px; background: #22242A; opacity: 0; z-index: 50; }
#outro-text { position: absolute; left: 96px; bottom: 160px; font-family: "Kaiti SC", "Songti SC", serif; font-size: 64px; color: #F6F1E7; opacity: 0; z-index: 51; }
</style>
</head>
<body>
<div id="root" data-composition-id="__COMP_ID__" data-width="1920" data-height="1080" data-start="0" data-duration="__TOTAL__">
<audio id="narration" data-start="0" data-duration="__AUDIO_DUR__" data-track-index="0" src="narration.mp3" data-volume="1"></audio>
__SCENES__
__CAPTIONS__
<div id="progress"><div id="progress-fill"></div></div>
<div id="outro"></div>
<div id="outro-text">这节课讲完啦，下次见</div>
</div>
<script src="vendor/gsap.min.js"></script>
<script>
window.__timelines = window.__timelines || {};
var tl = gsap.timeline({ paused: true });
var TOTAL = __TOTAL__;
__JS__
window.__timelines["__COMP_ID__"] = tl;
</script>
</body>
</html>
"""


def scene_html(idx: int, lesson: dict, beat: dict, total: int) -> str:
    esc = html.escape
    keywords = beat.get("keywords") or [lesson["title"][:6]]
    kw_parts = []
    for k_idx, k in enumerate(keywords[:2]):
        cls = "kw-accent" if k_idx > 0 else ""
        kw_parts.append(f'<span class="{cls}">{esc(k)}</span>')
        if k_idx == 0 and len(keywords) > 1:
            kw_parts.append('<span class="kw-plus"> ＋ </span>')
    kw_html = "".join(kw_parts)
    visual = beat.get("visual") or "generic"
    emoji, label, panel_cls = VISUALS.get(visual, VISUALS["generic"])
    panel_class = "vpanel" + ((" " + panel_cls) if panel_cls else "")
    note_text = beat.get("note") or label
    return f'''<div class="scene" id="scene-{idx:03d}">
  <div class="ghost">{esc(keywords[0][:6])}</div>
  <div class="bar-a"></div>
  <div class="bar-b"></div>
  <div class="tag">{esc(lesson['part'])} · {esc(lesson['title'])}</div>
  <div class="counter">{idx + 1:02d} / {total}</div>
  <div class="keyword">{kw_html}</div>
  <div class="note">{esc(note_text[:44])}</div>
  <div class="{panel_class}">
    <div class="v-emoji">{emoji}</div>
    <div class="v-label">{esc(label)}</div>
    <div class="v-note">{esc(note_text[:22])}</div>
  </div>
</div>'''


def compose_js(beats: list, captions: list, total: float) -> str:
    lines = []
    lines.append('tl.fromTo("#progress-fill", {scaleX:0}, {scaleX:1, duration:TOTAL, ease:"none"}, 0);')
    for idx, beat in enumerate(beats):
        start = beat["start"]
        window = max(1.2, beat["end"] - beat["start"] + 0.8)
        sel = f"#scene-{idx:03d}"
        lines.append(f'tl.fromTo("{sel} .tag", {{opacity:0, x:-26}}, {{opacity:1, x:0, duration:0.4, ease:"power2.out"}}, {start}+0.10);')
        lines.append(f'tl.fromTo("{sel} .counter", {{opacity:0, x:26}}, {{opacity:1, x:0, duration:0.4, ease:"power2.out"}}, {start}+0.12);')
        lines.append(f'tl.fromTo("{sel} .keyword", {{opacity:0, y:64, rotate:-1.2}}, {{opacity:1, y:0, rotate:0, duration:0.5, ease:"power3.out"}}, {start}+0.18);')
        lines.append(f'tl.fromTo("{sel} .vpanel", {{opacity:0, scale:0.9}}, {{opacity:1, scale:1, duration:0.5, ease:"back.out(1.5)"}}, {start}+0.24);')
        lines.append(f'tl.fromTo("{sel} .note", {{opacity:0, y:30}}, {{opacity:1, y:0, duration:0.44, ease:"power2.out"}}, {start}+0.34);')
        lines.append(f'tl.fromTo("{sel} .ghost", {{y:0}}, {{y:-16, duration:1.8, yoyo:true, repeat:Math.max(0, Math.ceil({window}/1.8)-1), ease:"sine.inOut"}}, {start});')
    for idx in range(len(beats) - 1):
        nxt = beats[idx + 1]["start"]
        cur = beats[idx]["start"]
        trans = max(nxt - 0.35, cur + 0.6)
        lines.append(f'tl.to("#scene-{idx:03d}", {{opacity:0, duration:0.35, ease:"power2.inOut"}}, {trans});')
        lines.append(f'tl.fromTo("#scene-{idx + 1:03d}", {{opacity:0}}, {{opacity:1, duration:0.35, ease:"power2.inOut"}}, {trans}+0.06);')
    for cap in captions:
        cap_id = f"#cap-{cap['index']:03d}"
        st = cap["start"]
        en = max(cap["end"], st + 0.4)
        lines.append(f'tl.fromTo("{cap_id}", {{opacity:0, y:16}}, {{opacity:1, y:0, duration:0.2, ease:"power2.out"}}, {st}+0.05);')
        lines.append(f'tl.to("{cap_id}", {{opacity:0, y:0, duration:0.14, ease:"power2.in"}}, {en}-0.14);')
        lines.append(f'tl.set("{cap_id}", {{opacity:0, visibility:"hidden"}}, {en});')
    last = len(beats) - 1
    lines.append(f'tl.to("#outro", {{opacity:1, duration:0.7, ease:"power1.in"}}, TOTAL-0.95);')
    lines.append(f'tl.fromTo("#outro-text", {{opacity:0, y:24}}, {{opacity:1, y:0, duration:0.5, ease:"power2.out"}}, TOTAL-0.7);')
    lines.append(f'tl.set("#scene-{last:03d}", {{opacity:0, visibility:"hidden"}}, TOTAL-0.2);')
    return "\n".join(lines)


def generate_composition(root: Path, lesson: dict, config: dict, force: bool = False) -> bool:
    ep_dir = lesson_dir(root, lesson)
    timing_path = ep_dir / "timing.json"
    if not timing_path.exists():
        return False
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    beats = timing["beats"]
    total_audio = timing["total"]
    total = round(total_audio + 1.25, 3)
    script_beats = parse_script((ep_dir / "script.md").read_text(encoding="utf-8"))
    if not script_beats:
        return False
    for idx, beat in enumerate(beats):
        if idx < len(script_beats):
            beat["keywords"] = script_beats[idx].get("keywords") or []
            beat["visual"] = script_beats[idx].get("visual") or "generic"
            beat["note"] = script_beats[idx].get("note") or ""
    words = []
    transcript_path = ep_dir / "transcript.json"
    if transcript_path.exists():
        try:
            words = json.loads(transcript_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            words = []
    captions = group_captions(words, beats)

    scenes = "\n".join(scene_html(idx, lesson, beat, len(beats)) for idx, beat in enumerate(beats))
    captions_html = "\n".join(
        f'<div class="caption" id="cap-{cap["index"]:03d}">{html.escape(cap["text"])}</div>'
        for cap in captions
    )
    js = compose_js(beats, captions, total)
    comp_id = f"lesson-{lesson['id']}"
    out = (
        COMPOSE_TPL
        .replace("__TITLE__", html.escape(f"第{lesson['num']}课 {lesson['title']}"))
        .replace("__COMP_ID__", comp_id)
        .replace("__TOTAL__", f"{total:.3f}")
        .replace("__AUDIO_DUR__", f"{total_audio:.3f}")
        .replace("__SCENES__", scenes)
        .replace("__CAPTIONS__", captions_html)
        .replace("__JS__", js)
    )
    (ep_dir / "index.html").write_text(out, encoding="utf-8")
    vendor_src = root / "video" / "vendor" / "gsap.min.js"
    vendor_dst = ep_dir / "vendor" / "gsap.min.js"
    if vendor_src.exists():
        vendor_dst.parent.mkdir(parents=True, exist_ok=True)
        if not vendor_dst.exists() or vendor_src.stat().st_size != vendor_dst.stat().st_size:
            vendor_dst.write_bytes(vendor_src.read_bytes())
    log(f"[{lesson['id']}] 合成 HTML 完成：{ep_dir / 'index.html'}")
    return True


def run_npx(cwd: Path, args_list: list, timeout: int = 3600) -> subprocess.CompletedProcess:
    cmd = ["npx", "-y", "hyperframes"] + args_list
    log(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


def render_lesson(root: Path, lesson: dict, config: dict, force: bool = False) -> bool:
    ep_dir = lesson_dir(root, lesson)
    html_path = ep_dir / "index.html"
    if not html_path.exists():
        log(f"[{lesson['id']}] 跳过：没有 index.html")
        return False
    output = ep_dir / "render" / f"lesson-{lesson['id']}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)

    lint = run_npx(ep_dir, ["lint"])
    if lint.returncode != 0:
        log(f"[{lesson['id']}] lint 失败：\n{lint.stdout}\n{lint.stderr}")
        return False
    log(f"[{lesson['id']}] lint 通过")

    validate = run_npx(ep_dir, ["validate"], timeout=600)
    if validate.returncode != 0:
        log(f"[{lesson['id']}] validate 有警告/错误：\n{validate.stdout}\n{validate.stderr}")
    else:
        log(f"[{lesson['id']}] validate 通过")

    render = run_npx(
        ep_dir,
        [
            "render",
            "--fps", str(config["fps"]),
            "--quality", config["render_quality"],
            "--output", str(output),
        ],
    )
    if render.returncode != 0:
        log(f"[{lesson['id']}] 渲染失败：\n{render.stdout}\n{render.stderr}")
        return False
    state = load_state(root)
    entry = state["lessons"].get(lesson["id"], {})
    entry["video"] = str(output.relative_to(root))
    state["lessons"][lesson["id"]] = entry
    save_state(root, state)
    duration = probe_duration(output)
    log(f"[{lesson['id']}] 渲染完成：{output} ({duration:.1f}s)")
    return True


def write_playlist(root: Path, config: dict) -> None:
    state = load_state(root)
    lessons = sorted(state["lessons"].values(), key=lambda x: x["id"])
    md_lines = ["# B 端硬件 PM 教学视频", ""]
    html_items = []
    for lesson in lessons:
        title = f"第{lesson['id']}课 {lesson['title']}"
        rel = str(lesson.get("video", "")).replace("video/", "", 1)
        md_lines.append(f"- {lesson['id']} {lesson['title']} ({lesson.get('audio_duration', 0):.1f}s) - [视频]({rel})")
        html_items.append(f'''<section class="item">
  <h2>{html.escape(title)}</h2>
  <video controls preload="metadata" src="{html.escape(rel)}"></video>
</section>''')
    md_path = root / "video" / "index.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>B 端硬件 PM 教学视频</title>
<style>
body {{ margin: 0; background: #F6F1E7; color: #22242A; font-family: "Songti SC", "STSong", serif; }}
header {{ padding: 48px 56px 24px; }}
h1 {{ font-family: "Kaiti SC", "Songti SC", serif; font-size: 44px; margin: 0 0 8px; }}
p {{ color: #3E4A52; margin: 0; }}
main {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 28px; padding: 24px 56px 64px; }}
.item {{ background: #FFFDF8; border: 1px solid #E4DAC7; border-radius: 8px; padding: 20px; }}
h2 {{ font-size: 22px; margin: 0 0 14px; }}
video {{ width: 100%; border-radius: 8px; background: #22242A; }}
</style>
</head>
<body>
<header><h1>B 端硬件 PM 教学视频</h1><p>MiMo 老师配音 · HyperFrames HTML 渲染 · 点击即可播放</p></header>
<main>
{''.join(html_items)}
</main>
</body>
</html>'''
    (root / "video" / "index.html").write_text(page, encoding="utf-8")
    log(f"播放列表已写入 video/index.md 和 video/index.html（共 {len(lessons)} 集）")


def cmd_scan(args) -> int:
    root = find_project_root(args)
    config = load_config(root)
    lessons = parse_lessons(root / config["source_md"])
    state = load_state(root)
    log(f"共发现 {len(lessons)} 个已完成课时\n")
    log(f"{'ID':<6}{'状态':<10}标题")
    for lesson in lessons:
        cur_hash = script_hash(root, lesson)
        status = lesson_status(lesson, state["lessons"].get(lesson["id"], {}), cur_hash)
        log(f"{lesson['id']:<6}{status:<10}{lesson['part']} · {lesson['title']}")
    return 0


def cmd_prepare(args) -> int:
    root = find_project_root(args)
    config = load_config(root)
    lessons = parse_lessons(root / config["source_md"])
    state = load_state(root)
    count = 0
    for lesson in lessons:
        ep_dir = lesson_dir(root, lesson)
        ep_dir.mkdir(parents=True, exist_ok=True)
        source_path = ep_dir / "source.md"
        existing = state["lessons"].get(lesson["id"], {})
        if not source_path.exists() or existing.get("source_sha256") != lesson["source_sha256"]:
            source_path.write_text(lesson["source"] + "\n", encoding="utf-8")
        script_path = ep_dir / "script.md"
        if not script_path.exists():
            script_path.write_text(
                f"# {lesson['part']} · {lesson['title']} 老师讲稿\n"
                "# 格式：老师: 一句话 #关键词 @visual:xxx @note:短说明\n"
                "老师: 请把这一课的台词写在这里。 #占位 @visual:generic @note:待写\n",
                encoding="utf-8",
            )
        count += 1
    state["voice_sha256"] = voice_config_hash(config)
    save_state(root, state)
    log(f"已准备 {count} 个课时目录")
    return 0


def cmd_tts(args) -> int:
    root = find_project_root(args)
    config = load_config(root)
    api_key = load_api_key(root)
    if not api_key:
        sys.exit("没有找到 MIMO_API_KEY，请写入 video/.env 或设置为环境变量")
    lessons = parse_lessons(root / config["source_md"])
    state = load_state(root)
    targets = select_lessons(args, lessons, state)
    if not targets:
        log("没有需要合成的课时")
        return 0
    for lesson in targets:
        ok = render_lesson_audio(lesson, config, state, root, api_key, force=args.force)
        if ok and not getattr(args, "no_transcribe", False):
            transcribe_lesson(root, lesson, config, force=args.force)
    return 0


def cmd_transcribe(args) -> int:
    root = find_project_root(args)
    config = load_config(root)
    lessons = parse_lessons(root / config["source_md"])
    targets = lessons if args.all else [
        lesson for lesson in lessons
        if not (lesson_dir(root, lesson) / "transcript.json").exists()
    ]
    for lesson in targets:
        transcribe_lesson(root, lesson, config, force=args.force)
    return 0


def cmd_compose(args) -> int:
    root = find_project_root(args)
    config = load_config(root)
    lessons = parse_lessons(root / config["source_md"])
    state = load_state(root)
    targets = select_lessons(args, lessons, state) if not args.all else lessons
    for lesson in targets:
        generate_composition(root, lesson, config, force=args.force)
    return 0


def cmd_render(args) -> int:
    root = find_project_root(args)
    config = load_config(root)
    lessons = parse_lessons(root / config["source_md"])
    state = load_state(root)
    targets = lessons if args.all else select_lessons(args, lessons, state)
    for lesson in targets:
        render_lesson(root, lesson, config, force=args.force)
    return 0


def cmd_list(args) -> int:
    root = find_project_root(args)
    config = load_config(root)
    lessons = parse_lessons(root / config["source_md"])
    state = load_state(root)
    log(f"{'ID':<6}{'时长':<9}{'视频':<8}标题")
    for lesson in lessons:
        entry = state["lessons"].get(lesson["id"], {})
        duration = f"{entry.get('audio_duration', 0):.1f}s" if entry.get("audio_duration") else "-"
        video = "已渲染" if entry.get("video") else "-"
        log(f"{lesson['id']:<6}{duration:<9}{video:<8}{lesson['title']}")
    return 0


def cmd_sample(args) -> int:
    root = find_project_root(args)
    config = load_config(root)
    api_key = load_api_key(root)
    if not api_key:
        sys.exit("没有找到 MIMO_API_KEY")
    lessons = parse_lessons(root / config["source_md"])
    if not lessons:
        sys.exit("没有课时")
    lesson = lessons[0]
    script_text = (lesson_dir(root, lesson) / "script.md").read_text(encoding="utf-8")
    beats = parse_script(script_text)
    timing_path = lesson_dir(root, lesson) / "timing.json"
    if timing_path.exists():
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        picked = []
        for beat in timing["beats"]:
            picked.append(beat)
            if beat["end"] >= 55:
                break
        beats = beats[: max(len(picked), 1)]
    else:
        beats = beats[:6]
    if not beats:
        sys.exit("第一课还没有台词")
    sample_dir = root / "video" / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)
    seg_dir = sample_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    silence = sample_dir / "silence.mp3"
    make_silence(silence, config["silence_seconds"])
    voice = config["voice"]
    chunks = []
    for idx, beat in enumerate(beats):
        seg_path = seg_dir / f"seg_{idx:03d}.mp3"
        chunks.append(seg_path)
        if seg_path.exists():
            continue
        log(f"  合成样音 {idx + 1}/{len(beats)}")
        seg_path.write_bytes(tts_request(api_key, config, voice, beat["text"]))
        time.sleep(0.2)
    filelist = sample_dir / "filelist.txt"
    lines = []
    for seg_path in chunks:
        lines.append(f"file '{seg_path.as_posix()}'")
        lines.append(f"file '{silence.as_posix()}'")
    filelist.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = sample_dir / "sample-teacher.mp3"
    run_ffmpeg([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(filelist),
        "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "24000", "-ac", "1",
        str(out),
    ])
    log(f"老师样音完成：{out}")
    return 0


def cmd_index(args) -> int:
    root = find_project_root(args)
    config = load_config(root)
    write_playlist(root, config)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="B端硬件PM教学视频管道")
    parser.add_argument("--project", help="项目根目录（默认当前目录）")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("scan", "prepare", "list", "sample", "index"):
        sub.add_parser(name)
    for name in ("tts", "compose", "render", "transcribe"):
        p = sub.add_parser(name)
        p.add_argument("--episode", help="只处理指定课时 id 或 slug")
        p.add_argument("--all", action="store_true", help="处理全部课时")
        p.add_argument("--force", action="store_true", help="忽略缓存强制重做")
    for name in ("tts",):
        sub.choices[name].add_argument("--no-transcribe", action="store_true", help="合成旁白后不立即转写")
    args = parser.parse_args()
    dispatch = {
        "scan": cmd_scan,
        "prepare": cmd_prepare,
        "tts": cmd_tts,
        "transcribe": cmd_transcribe,
        "compose": cmd_compose,
        "render": cmd_render,
        "list": cmd_list,
        "sample": cmd_sample,
        "index": cmd_index,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
