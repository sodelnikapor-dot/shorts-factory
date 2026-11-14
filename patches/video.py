"""
Сборка вертикального видео 1080x1920.
Сцены: сначала пытаемся взять реальный видеофрагмент из свободного архива
archive.org (Prelinger / Creative Commons), иначе — плавное движение камеры
по картинке. Субтитры: простой жирный шрифт без обводки, по центру экрана.
"""
import json
import os
import time
import urllib.parse
import urllib.request

import cv2
import numpy as np
from moviepy import (AudioFileClip, CompositeVideoClip, ImageClip, VideoClip,
                     VideoFileClip, concatenate_audioclips, vfx)
from PIL import Image, ImageDraw, ImageFont

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
FONT_PATH = os.path.join(ASSETS, "NotoSans-Bold.ttf")
FONT_URL = ("https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/"
            "fonts/NotoSans/hinted/ttf/NotoSans-Bold.ttf")
W, H = 1080, 1920
FPS = 24
STOCK_BUDGET = 420.0


def _ensure_font() -> str:
    if not os.path.exists(FONT_PATH):
        os.makedirs(ASSETS, exist_ok=True)
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
    return FONT_PATH


def _subtitle_png(text: str, width: int = 980, font_size: int = 92) -> str:
    """Простой жирный текст без обводки на прозрачном фоне, по центру строки."""
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

    line_h = font_size + 16
    img = Image.new("RGBA", (width + 60, line_h * len(lines) + 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y = 10
    for ln in lines:
        x = (img.width - font.getlength(ln)) / 2
        draw.text((x, y), ln, font=font, fill=(255, 255, 255, 255))
        y += line_h
    path = os.path.join(ASSETS, f"sub_{abs(hash(text)) % 10**10}.png")
    img.save(path)
    return path


def _pop_sub_clip(text: str, start: float, end: float) -> VideoClip:
    """Субтитр по центру экрана, мягкое появление масштабом."""
    base = Image.open(_subtitle_png(text)).convert("RGBA")
    canvas_h = H
    dur = max(0.12, end - start)

    def make(t):
        k = min(1.0, t / 0.14)
        scale = 0.88 + 0.12 * (1 - (1 - k) ** 3)
        w1 = max(1, int(base.width * scale))
        h1 = max(1, int(base.height * scale))
        img = base.resize((w1, h1), Image.BILINEAR)
        canvas = Image.new("RGBA", (W, canvas_h), (0, 0, 0, 0))
        canvas.alpha_composite(img, ((W - w1) // 2, (canvas_h - h1) // 2))
        return np.asarray(canvas)

    return (VideoClip(make, duration=dur)
            .with_fps(FPS)
            .with_start(start)
            .with_position((0, 0)))


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


def _kb_clip(plate: np.ndarray, duration: float, zoom_start: float,
             zoom_end: float, drift: float) -> VideoClip:
    """Кинематографичный кадр: движение камеры (наезд/панч-ин) с дрейфом."""
    ph, pw = plate.shape[:2]

    def make(t):
        p = t / max(duration, 0.01)
        ease = p * p * (3 - 2 * p)
        zoom = zoom_start + (zoom_end - zoom_start) * ease
        cw, ch = int(W / zoom), int(H / zoom)
        base_dx = pw / 2 - W / 2
        base_dy = ph / 2 - H / 2
        cx = int(base_dx + (ease - 0.5) * drift)
        cy = int(base_dy + (ease - 0.5) * drift * 0.6)
        cx = max(0, min(pw - cw, cx))
        cy = max(0, min(ph - ch, cy))
        frame = cv2.resize(plate[cy:cy + ch, cx:cx + cw], (W, H), interpolation=cv2.INTER_LINEAR)
        return np.clip(frame, 0, 255).astype(np.uint8)

    return VideoClip(make, duration=duration).with_fps(FPS)


def _stock_candidates(keywords: str) -> list[str]:
    q = urllib.parse.quote(
        f"{keywords} AND mediatype:(movies) AND (collection:(prelinger) OR licenseurl:*creativecommons*)")
    url = (f"https://archive.org/advancedsearch.php?q={q}&fl%5B%5D=identifier"
           f"&rows=6&page=1&output=json&sort%5B%5D=downloads+desc")
    with urllib.request.urlopen(url, timeout=25) as r:
        docs = json.load(r)["response"]["docs"]
    urls = []
    for doc in docs:
        ident = doc.get("identifier")
        if not ident:
            continue
        try:
            with urllib.request.urlopen(f"https://archive.org/metadata/{ident}", timeout=25) as r:
                files = json.load(r).get("files", [])
        except Exception:  # noqa: BLE001
            continue
        best = None
        for f in files:
            name = f.get("name", "")
            if not name.lower().endswith(".mp4"):
                continue
            try:
                size = int(f.get("size") or 0)
            except (TypeError, ValueError):
                size = 0
            if size and size > 80_000_000:
                continue
            score = (0 if "_512kb" in name else 1, size or 10 ** 9)
            if best is None or score < best[0]:
                best = (score, name)
        if best:
            urls.append(f"https://archive.org/download/{urllib.parse.quote(str(ident))}/"
                        f"{urllib.parse.quote(best[1])}")
    return urls


def _fit_vertical(clip: VideoFileClip, duration: float, offset_frac: float = 0.3) -> VideoClip:
    vdur = clip.duration or 0.0
    start = max(0.0, min(max(vdur - duration, 0.0), (vdur - duration) * offset_frac))
    end = min(vdur, start + duration)
    seg = clip.subclipped(start, end).with_fps(FPS).without_audio()
    vw, vh = seg.size
    k = max(W / vw, H / vh)
    seg = seg.resized((max(W, int(vw * k + 0.5)) // 2 * 2, max(H, int(vh * k + 0.5)) // 2 * 2))
    sw, sh = seg.size
    return seg.cropped(x_center=sw / 2, y_center=sh / 2, width=W, height=H)


def _stock_clip(keywords: str, duration: float, cache_path: str, deadline: float):
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 100_000:
        try:
            v = VideoFileClip(cache_path)
            if v.duration and v.duration >= 1.5:
                return v
            v.close()
        except Exception:  # noqa: BLE001
            pass
    if time.monotonic() > deadline:
        return None
    try:
        for url in _stock_candidates(keywords)[:2]:
            if time.monotonic() > deadline:
                return None
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "shorts-factory/1.0"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read(80_000_000)
                if len(data) < 100_000:
                    continue
                with open(cache_path, "wb") as f:
                    f.write(data)
                v = VideoFileClip(cache_path)
                if v.duration and v.duration >= 1.5:
                    print(f"      сток-видео: {urllib.parse.unquote(url.split('/download/')[1].split('/')[0])}",
                          flush=True)
                    return v
                v.close()
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass
    return None


def make_video(scenes: list[dict], audio_files: list[str], subtitle_tracks: list[list[dict]],
               out_path: str) -> str:
    """scenes: [{'image': путь, 'image_prompt': ...}], audio_files: mp3 по сценам,
    subtitle_tracks: тайминги относительно начала сцены."""
    scene_clips = []
    scene_starts = []
    cursor = 0.0
    deadline = time.monotonic() + STOCK_BUDGET
    for i, (scene, audio) in enumerate(zip(scenes, audio_files)):
        aclip = AudioFileClip(audio)
        duration = aclip.duration + 0.35
        d1 = duration * 0.5
        d2 = duration - d1
        zoom_dir = 1 if i % 2 == 0 else -1
        stock = None
        keywords = " ".join(str(scene.get("image_prompt", "")).split()[:6])
        if keywords:
            cache = os.path.join(os.path.dirname(scene["image"]), f"stock_{i}.mp4")
            try:
                stock = _stock_clip(keywords, duration, cache, deadline)
            except Exception:  # noqa: BLE001
                stock = None
        scene_start = cursor
        shots = []
        if stock is not None:
            vdur = stock.duration or 0.0
            if vdur >= d1 + d2 + 1.0:
                shots.append(_fit_vertical(stock, d1, 0.15))
                shots.append(_fit_vertical(stock, d2, 0.75))
            else:
                shots.append(_fit_vertical(stock, duration, 0.3))
            stock.close()
        else:
            plate = np.asarray(Image.open(scene["image"]).convert("RGB")).astype(np.float32)
            ph, pw = plate.shape[:2]
            pad = np.zeros((ph + 200, pw + 200, 3), dtype=np.float32)
            pad[100:100 + ph, 100:100 + pw] = plate
            shots.append(_kb_clip(pad, d1, 1.00, 1.05, 20 * zoom_dir))
            shots.append(_kb_clip(pad, d2, 1.09, 1.15, -18 * zoom_dir))
        for shot in shots:
            scene_clips.append(shot.with_start(cursor))
            cursor += shot.duration
        scene_starts.append(scene_start)
        aclip.close()

    video = CompositeVideoClip(scene_clips, size=(W, H)).with_duration(cursor)

    video = video.with_effects([vfx.FadeIn(0.4), vfx.FadeOut(0.6)])

    vignette = ImageClip(np.asarray(_vignette())).with_duration(cursor)
    video = CompositeVideoClip([video, vignette], size=(W, H)).with_duration(cursor)

    overlay_clips = []
    for i, track in enumerate(subtitle_tracks):
        for sub in track:
            overlay_clips.append(_pop_sub_clip(
                sub["text"],
                scene_starts[i] + sub["start"],
                scene_starts[i] + sub["end"],
            ))
    if overlay_clips:
        video = CompositeVideoClip([video, *overlay_clips], size=(W, H)).with_duration(cursor)

    voice = concatenate_audioclips([AudioFileClip(a) for a in audio_files])
    video = video.with_audio(voice)

    video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac",
                          preset="medium", ffmpeg_params=["-crf", "21"], logger=None)
    return out_path
