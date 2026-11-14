# syntax=docker/dockerfile:1
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY <<'EOF' /app/requirements.txt
edge-tts>=7.0
moviepy>=2.0
pillow>=10.0
numpy
requests
opencv-python-headless>=4.9
EOF
COPY <<'EOF' /app/shorts_factory/__init__.py
EOF
COPY <<'EOF' /app/shorts_factory/script_gen.py
"""Идея + сценарий для исторического шортса. LLM через открытый API pollinations (без ключа),
с опцией переключения на Mistral API, если задан MISTRAL_API_KEY."""
import json
import os
import random
import re
import urllib.request

POLLINATIONS_TEXT = "https://text.pollinations.ai/openai"

ERAS = [
    "Древний Египет", "Древний Рим", "Древняя Греция", "Средневековье",
    "Викинги", "Древняя Русь", "Российская империя", "Эпоха Наполеона",
    "Вторая мировая война", "Эпоха Возрождения", "Древний Китай",
    "Ацтеки и майя", "Золотая Орда", "Византия", "Эпоха великих географических открытий",
]

PROMPT_TMPL = """Ты — сценарист YouTube Shorts по истории. Придумай ОДИН удивительный, но реальный исторический факт из эпохи: {era}.

Требования к сценарию:
- Текст для озвучки на русском языке, 45-55 секунд при чтении (примерно 110-140 слов).
- Первая фраза — цепляющий хук (не более 10 слов), без приветствий.
- 3-5 смысловых битов, каждый — отдельная сцена.
- Финал — вывод или интрига.
- Никаких выдумок: только реальные факты. Если не уверен в точности — выбери другой факт.

Верни СТРОГО валидный JSON без markdown в формате:
{{
  "title": "название видео для YouTube (до 80 символов, с интригой)",
  "hook": "первая фраза",
  "scenes": [
    {{"text": "текст озвучки этой сцены", "image_prompt": "описание сцены на английском для генерации иллюстрации в стиле vintage historical illustration, engraving, ink and watercolor"}}
  ],
  "description": "описание видео для YouTube, 2-3 предложения на русском",
  "tags": ["#shorts", "история", "ещё 3-5 тегов"]
}}"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"JSON не найден в ответе модели: {text[:200]}")
    return json.loads(match.group(0))


def _ask_llm(prompt: str) -> str:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if api_key:
        req = urllib.request.Request(
            "https://api.mistral.ai/v1/chat/completions",
            data=json.dumps({
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
            }).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    body = json.dumps({
        "model": os.environ.get("SHORTS_TEXT_MODEL", "openai-fast"),
        "messages": [{"role": "user", "content": prompt}],
        "seed": random.randint(0, 10**9),
        "max_tokens": 3000,
        "reasoning_effort": "low",
    }).encode()
    req = urllib.request.Request(
        POLLINATIONS_TEXT, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "shorts-factory/1.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def generate_script(era: str | None = None) -> dict:
    era = era or random.choice(ERAS)
    prompt = PROMPT_TMPL.format(era=era)
    last_err = None
    for _ in range(3):
        try:
            script = _extract_json(_ask_llm(prompt))
            if script.get("scenes") and script.get("hook"):
                script["era"] = era
                return script
        except Exception as err:  # noqa: BLE001
            last_err = err
    raise RuntimeError(f"Не удалось получить сценарий: {last_err}")
EOF
COPY <<'EOF' /app/shorts_factory/tts.py
"""Озвучка через edge-tts (бесплатный русский нейроголос) + разметка по времени для субтитров."""
import asyncio
import json
import os
import re
import time

import edge_tts

VOICE = os.environ.get("SHORTS_VOICE", "ru-RU-DmitryNeural")
FALLBACK_VOICES = ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"]
RATE = os.environ.get("SHORTS_RATE", "+8%")


async def _tts(text: str, mp3_path: str) -> None:
    tts = edge_tts.Communicate(text, VOICE, rate=RATE)
    await tts.save(mp3_path)


async def _tts_with_offsets(text: str, mp3_path: str, voice: str = VOICE) -> list[dict]:
    tts = edge_tts.Communicate(text, voice, rate=RATE, boundary="WordBoundary")
    words = []
    with open(mp3_path, "wb") as f:
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 1e7,
                    "duration": chunk["duration"] / 1e7,
                })
    return words


def synthesize(text: str, mp3_path: str) -> list[dict]:
    """Озвучивает text, пишет mp3, возвращает пословные тайминги (сек)."""
    last_err = None
    for attempt in range(4):
        voice = VOICE if attempt < 2 else FALLBACK_VOICES[attempt % 2]
        try:
            return asyncio.run(_tts_with_offsets(text, mp3_path, voice))
        except Exception as err:  # noqa: BLE001
            last_err = err
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Озвучка не удалась: {last_err}")


def build_subtitles(word_timings: list[dict], max_chars: int = 26, pause: float = 0.45) -> list[dict]:
    """Группирует слова в короткие фразы-субтитры."""
    subs, current, start = [], [], None
    prev_end = None
    for w in word_timings:
        if start is None:
            start = w["start"]
        gap_broken = prev_end is not None and w["start"] - prev_end > pause
        current.append(w)
        line = " ".join(x["word"] for x in current)
        ends_sentence = bool(re.search(r"[.!?…]$", w["word"]))
        if len(line) >= max_chars or ends_sentence or gap_broken:
            subs.append({
                "text": line,
                "start": round(start, 2),
                "end": round(current[-1]["start"] + current[-1]["duration"], 2),
            })
            current, start = [], None
        prev_end = w["start"] + w["duration"]
    if current:
        subs.append({
            "text": " ".join(x["word"] for x in current),
            "start": round(start, 2),
            "end": round(current[-1]["start"] + current[-1]["duration"], 2),
        })
    merged = []
    for sub in subs:
        if merged and len(merged[-1]["text"]) < 8:
            merged[-1]["text"] += " " + sub["text"]
            merged[-1]["end"] = sub["end"]
        else:
            merged.append(dict(sub))
    return merged
EOF
COPY <<'EOF' /app/shorts_factory/images.py
"""Генерация иллюстраций в нарисованном стиле через открытый API pollinations.ai (flux, без ключа)."""
import io
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

IMAGE_URL = "https://image.pollinations.ai/prompt/{prompt}"
STYLE = (
    "vintage historical illustration, detailed engraving style with ink and "
    "watercolor, aged parchment tones, dramatic lighting, painterly, highly "
    "detailed, vertical composition, no text, no watermark"
)


def generate_image(prompt: str, out_path: str, width: int = 1080, height: int = 1920,
                   retries: int = 6) -> str:
    full = f"{prompt}, {STYLE}"
    url = IMAGE_URL.format(prompt=urllib.parse.quote(full))
    url += f"?width={width}&height={height}&model=flux&nologo=true&seed={random.randint(0, 10**9)}"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "shorts-factory/1.0"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = resp.read()
            if len(data) < 10_000:
                raise ValueError(f"подозрительно маленький файл: {len(data)} байт")
            img = Image.open(io.BytesIO(data)).convert("RGB")
            w, h = img.size
            img = img.crop((int(w * 0.04), int(h * 0.04), int(w * 0.96), int(h * 0.92)))
            img.save(out_path, quality=92)
            time.sleep(46)
            return out_path
        except urllib.error.HTTPError as err:
            last_err = err
            if err.code in (402, 429):
                time.sleep(50)
            else:
                time.sleep(5)
        except Exception as err:  # noqa: BLE001
            last_err = err
            time.sleep(5)
    raise RuntimeError(f"Не удалось сгенерировать изображение: {last_err}")
EOF
COPY <<'EOF' /app/shorts_factory/video.py
"""Сборка вертикального видео 1080x1920: сцены с эффектом Ken Burns, кроссфейды, субтитры, озвучка."""
import os
import urllib.request

import numpy as np
from moviepy import (AudioFileClip, CompositeAudioClip, CompositeVideoClip, ImageClip,
                     VideoClip, concatenate_audioclips)
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
FONT_PATH = os.path.join(ASSETS, "NotoSans-Bold.ttf")
FONT_URL = ("https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/"
            "fonts/NotoSans/hinted/ttf/NotoSans-Bold.ttf")
W, H = 1080, 1920
FPS = 24


def _ensure_font() -> str:
    if not os.path.exists(FONT_PATH):
        os.makedirs(ASSETS, exist_ok=True)
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
    return FONT_PATH


def _subtitle_png(text: str, width: int = 920, font_size: int = 64) -> str:
    """Рисует субтитры с обводкой на прозрачном фоне, возвращает путь к PNG."""
    font = ImageFont.truetype(_ensure_font(), font_size)
    words = text.split()
    lines, line = [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if font.getlength(candidate) <= width or not line:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)

    line_h = font_size + 14
    img = Image.new("RGBA", (width + 80, line_h * len(lines) + 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y = 20
    for ln in lines:
        x = (img.width - font.getlength(ln)) / 2
        for dx in (-3, 0, 3):
            for dy in (-3, 0, 3):
                if dx or dy:
                    draw.text((x + dx, y + dy), ln, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), ln, font=font, fill=(255, 255, 255, 255))
        y += line_h
    path = os.path.join(ASSETS, f"sub_{abs(hash(text)) % 10**10}.png")
    img.save(path)
    return path


def _vignette() -> Image.Image:
    grad = Image.new("L", (1, H))
    for y in range(H):
        if y < 250:
            v = int(160 * (1 - y / 250))
        elif y > H - 400:
            v = int(200 * min(1, (y - (H - 400)) / 400))
        else:
            v = 0
        grad.putpixel((0, y), v)
    alpha = grad.resize((W, H))
    black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    black.putalpha(alpha)
    return black


def _scene_clip(image_path: str, duration: float, zoom_dir: int) -> VideoClip:
    base = ImageClip(image_path)
    factor = 1.10 if zoom_dir > 0 else 0.94

    def make(t):
        scale = 1.0 + (factor - 1.0) * (t / max(duration, 0.01))
        new_w, new_h = int((W + 120) * scale), int((H + 120) * scale)
        frame = base.get_frame(0)
        img = Image.fromarray(frame).resize((new_w, new_h), Image.BILINEAR)
        x, y = (new_w - W) // 2, (new_h - H) // 2
        return np.asarray(img.crop((x, y, x + W, y + H)))

    return VideoClip(make, duration=duration).with_fps(FPS)


def make_video(scenes: list[dict], audio_files: list[str], subtitle_tracks: list[list[dict]],
               out_path: str) -> str:
    """scenes: [{'image': путь}], audio_files: mp3 по сценам, subtitle_tracks: тайминги относительно начала сцены."""
    scene_clips = []
    scene_starts = []
    cursor = 0.0
    for i, (scene, audio) in enumerate(zip(scenes, audio_files)):
        aclip = AudioFileClip(audio)
        duration = aclip.duration + 0.35
        img = Image.open(scene["image"]).convert("RGB").resize((W + 120, H + 120), Image.BILINEAR)
        img = img.filter(ImageFilter.GaussianBlur(0.6))
        tmp = scene["image"].rsplit(".", 1)[0] + "_prep.jpg"
        img.save(tmp, quality=90)
        clip = _scene_clip(tmp, duration, 1 if i % 2 == 0 else -1).with_start(cursor)
        scene_clips.append(clip)
        scene_starts.append(cursor)
        cursor += duration
        aclip.close()

    video = CompositeVideoClip(scene_clips, size=(W, H)).with_duration(cursor)

    vignette = ImageClip(np.asarray(_vignette())).with_duration(cursor)
    video = CompositeVideoClip([video, vignette], size=(W, H)).with_duration(cursor)

    overlay_clips = []
    for i, track in enumerate(subtitle_tracks):
        for sub in track:
            png = _subtitle_png(sub["text"])
            s = (ImageClip(png, transparent=True)
                 .with_start(scene_starts[i] + sub["start"])
                 .with_end(scene_starts[i] + sub["end"])
                 .with_position(("center", H - 480)))
            overlay_clips.append(s)
    if overlay_clips:
        video = CompositeVideoClip([video, *overlay_clips], size=(W, H)).with_duration(cursor)

    voice = concatenate_audioclips([AudioFileClip(a) for a in audio_files])
    video = video.with_audio(CompositeAudioClip([voice]))

    video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac",
                          preset="medium", ffmpeg_params=["-crf", "23"], logger=None)
    return out_path
EOF
COPY <<'EOF' /app/shorts_factory/pipeline.py
"""Полный конвейер: сценарий -> картинки -> озвучка -> видео."""
import json
import os
import time

from . import images, script_gen, tts


def run_pipeline(out_dir: str, era: str | None = None) -> dict:
    from .video import make_video

    os.makedirs(out_dir, exist_ok=True)
    work = os.path.join(out_dir, "work")
    os.makedirs(work, exist_ok=True)

    script_path = os.path.join(work, "script.json")
    if os.path.exists(script_path):
        with open(script_path, encoding="utf-8") as f:
            script = json.load(f)
        print("      сценарий найден, переиспользую")
    else:
        print("[1/5] Генерация сценария...")
        script = script_gen.generate_script(era)
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"      Тема: {script['title']} ({len(script['scenes'])} сцен)")

    print("[2/5] Генерация иллюстраций...")
    for i, scene in enumerate(script["scenes"]):
        img_path = os.path.join(work, f"scene_{i}.jpg")
        if not os.path.exists(img_path):
            images.generate_image(scene["image_prompt"], img_path)
        scene["image"] = img_path
        print(f"      сцена {i + 1}/{len(script['scenes'])} готова")

    print("[3/5] Озвучка...")
    audio_files, subtitle_tracks = [], []
    for i, scene in enumerate(script["scenes"]):
        mp3 = os.path.join(work, f"voice_{i}.mp3")
        if os.path.exists(mp3) and os.path.getsize(mp3) < 1000:
            os.remove(mp3)
        timings = tts.synthesize(scene["text"], mp3)
        audio_files.append(mp3)
        subtitle_tracks.append(tts.build_subtitles(timings))
        print(f"      сцена {i + 1}/{len(script['scenes'])} озвучена")

    print("[4/5] Сборка видео...")
    out_path = os.path.join(out_dir, "short.mp4")
    make_video(script["scenes"], audio_files, subtitle_tracks, out_path)

    print("[5/5] Готово.")
    meta = {
        "title": script["title"],
        "description": script.get("description", ""),
        "tags": script.get("tags", ["#shorts", "история"]),
        "video": out_path,
    }
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def output_dir() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "output", time.strftime("%Y%m%d_%H%M%S"))


if __name__ == "__main__":
    import sys

    start = time.time()
    out = sys.argv[1] if len(sys.argv) > 1 else output_dir()
    era = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(run_pipeline(out, era), ensure_ascii=False, indent=2))
    print(f"Время: {time.time() - start:.0f} с")
EOF
COPY <<'EOF' /app/shorts_factory/youtube.py
"""Автозагрузка на YouTube Shorts через YouTube Data API v3.

Требуются переменные окружения (из секретов workspace):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Если их нет — видео остаётся в очереди output/ для ручной публикации.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
QUEUE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "output", "upload_queue.jsonl")


def _access_token() -> str:
    data = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["access_token"]


def upload(video_path: str, title: str, description: str, tags: list[str],
           privacy: str = "public", made_for_kids: bool = False) -> dict:
    token = _access_token()
    meta = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": [t.lstrip("#") for t in tags][:30],
            "categoryId": "27",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }
    boundary = "shortsfactory7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(meta)}\r\n"
        f"--{boundary}\r\nContent-Type: video/mp4\r\n\r\n"
    ).encode()
    with open(video_path, "rb") as f:
        body += f.read()
    body += f"\r\n--{boundary}--\r\n".encode()

    url = f"{UPLOAD_URL}?uploadType=multipart&part=snippet,status"
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/related; boundary={boundary}",
    })
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        # Показываем настоящую причину отказа YouTube API вместо голого кода.
        err_body = e.read().decode("utf-8", "replace")
        print(f"[upload] HTTP {e.code}: {err_body[:2000]}", flush=True)
        if e.code in (500, 503):
            time.sleep(20)
            with urllib.request.urlopen(req, timeout=600) as resp:
                result = json.loads(resp.read())
        else:
            raise
    return {"video_id": result["id"], "url": f"https://youtube.com/shorts/{result['id']}"}


def _channel_info() -> dict:
    """Диагностика: какой канал используется для публикаций."""
    try:
        token = _access_token()
        req = urllib.request.Request(
            "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            items = json.loads(resp.read()).get("items", [])
        if not items:
            return {"channel": "NOT FOUND (токен без канала)"}
        ch = items[0]
        return {"channel_id": ch["id"], "channel_title": ch["snippet"]["title"]}
    except Exception as e:  # диагностика не должна ломать публикацию
        return {"channel_check_error": str(e)[:200]}


def enqueue(meta: dict) -> None:
    """Добавляет видео в очередь публикации (fallback, если ключей YouTube нет)."""
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
    with open(QUEUE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({**meta, "queued_at": time.strftime("%Y-%m-%d %H:%M:%S")},
                           ensure_ascii=False) + "\n")


def publish(meta: dict) -> dict:
    """Публикует видео; без ключей YouTube кладёт в очередь."""
    if not os.environ.get("YT_REFRESH_TOKEN"):
        enqueue(meta)
        return {"status": "queued", "reason": "YouTube credentials не настроены"}
    info = _channel_info()
    print(f"[publish] target channel: {info}", flush=True)
    try:
        result = upload(meta["video"], meta["title"], meta["description"], meta["tags"])
        return {"status": "published", **info, **result}
    except urllib.error.HTTPError as e:
        if e.code != 400:
            raise
        # Запасной путь: возможно, часть метаданных не нравится API.
        # Пробуем минимальный набор: короткое описание без хэштегов, 3 базовых тега.
        print("[publish] HTTP 400 — повтор с упрощёнными метаданными", flush=True)
        clean_desc = meta["description"].split("\n#")[0].split("\n\n#")[0]
        result = upload(meta["video"], meta["title"], clean_desc,
                        ["shorts", "история", "факты"])
        return {"status": "published_fallback", **result}
EOF
COPY <<'EOF' /app/apps/worker/src/worker/__init__.py
EOF
COPY <<'EOF' /app/apps/worker/src/worker/entrypoints/__init__.py
EOF
COPY <<'EOF' /app/apps/worker/src/worker/entrypoints/worker.py
import asyncio

import mistralai.workflows as workflows


async def main() -> None:
    classes = workflows.discover_all_workflows_in_package("worker.workflows")
    await workflows.run_worker(classes)


if __name__ == "__main__":
    asyncio.run(main())
EOF
COPY <<'EOF' /app/apps/worker/src/worker/workflows/__init__.py
EOF
COPY <<'EOF' /app/apps/worker/src/worker/workflows/shorts.py
"""Оркестрация: генерация шортса и публикация по расписанию."""
import os
from datetime import datetime, timedelta, timezone

import mistralai.workflows as workflows
from pydantic import BaseModel


class ShortsParams(BaseModel):
    era: str | None = None
    dry_run: bool = False
    privacy: str = "public"


class ShortsResult(BaseModel):
    status: str
    title: str
    video_path: str | None = None
    youtube_url: str | None = None
    detail: str = ""


@workflows.activity(start_to_close_timeout=timedelta(minutes=25), retry_policy_max_attempts=2)
async def generate_short(era: str | None = None) -> dict:
    from shorts_factory.pipeline import run_pipeline

    out_dir = os.path.join("/tmp/shorts", datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    return run_pipeline(out_dir, era)


@workflows.activity(start_to_close_timeout=timedelta(minutes=10), retry_policy_max_attempts=3)
async def publish_short(meta: dict, privacy: str = "public", dry_run: bool = False) -> dict:
    if dry_run:
        return {"status": "dry_run", "title": meta["title"]}
    from shorts_factory import youtube

    result = youtube.publish({**meta, "privacy": privacy})
    return result


@workflows.workflow.define(name="shorts_factory")
class ShortsFactory:
    @workflows.workflow.entrypoint
    async def run(self, params: ShortsParams) -> ShortsResult:
        meta = await generate_short(params.era)
        pub = await publish_short(meta, params.privacy, params.dry_run)
        return ShortsResult(
            status=pub["status"],
            title=meta["title"],
            video_path=meta["video"],
            youtube_url=pub.get("url"),
            detail=pub.get("reason", ""),
        )
EOF
RUN pip install --no-cache-dir -r requirements.txt "mistralai-workflows[mistralai]>=3.17.1"
ENV PYTHONPATH=/app/apps/worker/src:/app
CMD ["python", "-m", "worker.entrypoints.worker"]
