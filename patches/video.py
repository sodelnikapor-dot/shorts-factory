"""
Сборка вертикального видео 1080x1920: живые анимированные сцены (параллакс слоёв,
дыхание персонажа, мерцание света, туман, пыль, дождь), pop-субтитры, озвучка.
"""
import os
import random
import urllib.request

import cv2
import numpy as np
from moviepy import (AudioFileClip, CompositeVideoClip, ImageClip,
                     VideoClip, concatenate_audioclips)
from PIL import Image, ImageDraw, ImageFont

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


def _subtitle_png(text: str, width: int = 860, font_size: int = 84) -> str:
    """Рисует субтитры с толстой обводкой на прозрачном фоне, возвращает путь к PNG."""
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

    line_h = font_size + 18
    img = Image.new("RGBA", (width + 80, line_h * len(lines) + 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y = 20
    for ln in lines:
        x = (img.width - font.getlength(ln)) / 2
        for dx in (-5, 0, 5):
            for dy in (-5, 0, 5):
                if dx or dy:
                    draw.text((x + dx, y + dy), ln, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), ln, font=font, fill=(255, 255, 255, 255))
        y += line_h
    path = os.path.join(ASSETS, f"sub_{abs(hash(text)) % 10**10}.png")
    img.save(path)
    return path


def _pop_sub_clip(text: str, start: float, end: float) -> VideoClip:
    """Pop-субтитр: масштаб 0.82 -> 1.0 за 0.14с (ease-out), по центру экрана."""
    base = Image.open(_subtitle_png(text)).convert("RGBA")
    canvas_h = base.height + 60
    dur = max(0.12, end - start)

    def make(t):
        k = min(1.0, t / 0.14)
        scale = 0.82 + 0.18 * (1 - (1 - k) ** 3)
        w1 = max(1, int(base.width * scale))
        h1 = max(1, int(base.height * scale))
        img = base.resize((w1, h1), Image.BILINEAR)
        canvas = Image.new("RGBA", (W, canvas_h), (0, 0, 0, 0))
        canvas.alpha_composite(img, ((W - w1) // 2, (canvas_h - h1) // 2))
        return np.asarray(canvas)

    return (VideoClip(make, duration=dur)
            .with_fps(FPS)
            .with_start(start)
            .with_position((0, int(H * 0.40))))


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


def _shift_layer(layer: np.ndarray, dx: float, dy: float) -> np.ndarray:
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(layer, m, (layer.shape[1], layer.shape[0]),
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def _fog_tiles(seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    tiles = []
    for k in range(2):
        small = rng.random((H // 6, W // 6)).astype(np.float32)
        small = cv2.GaussianBlur(small, (0, 0), 9)
        small = (small - small.min()) / max(small.max() - small.min(), 1e-6)
        tiles.append(small)
    return tiles


def _scene_clip(image_path: str, duration: float, zoom_dir: int, seed: int) -> VideoClip:
    """Живая сцена: параллакс фона и персонажа, дыхание, мерцание света, туман, пыль, дождь."""
    rng = random.Random(seed)
    plate = np.asarray(Image.open(image_path).convert("RGB")).astype(np.float32)
    ph, pw = plate.shape[:2]

    mask = np.zeros((ph, pw), dtype=np.float32)
    cv2.ellipse(mask, (pw // 2, int(ph * 0.56)), (int(pw * 0.36), int(ph * 0.34)),
                0, 0, 360, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), 41)[..., None]
    fg_plate = plate * mask
    bg_plate = plate * (1.0 - mask)

    fog = _fog_tiles(seed + 5)
    fog_strength = 0.09 if zoom_dir > 0 else 0.06
    n_drops = 46 if zoom_dir < 0 else 0
    drops = [(rng.uniform(0, W), rng.uniform(240, 640), rng.uniform(14, 30),
              rng.uniform(0.6, 1.0)) for _ in range(n_drops)]
    dust = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(12, 40),
             rng.uniform(0.4, 1.0)) for _ in range(22)]
    flicker_times = sorted(rng.uniform(0.15, 0.95) for _ in range(rng.randint(2, 4)))

    def make(t):
        p = t / max(duration, 0.01)
        base_dx = pw / 2 - W / 2
        base_dy = ph / 2 - H / 2

        bg_dx = (p - 0.5) * 26 * (1 if zoom_dir > 0 else -1)
        fg_dx = -(p - 0.5) * 14 * (1 if zoom_dir > 0 else -1)
        fg_dy = np.sin(t * 1.15) * 7.0
        angle = np.degrees(np.sin(t * 0.45)) * 0.9

        shake_k = max(0.0, 1.0 - t / 0.5)
        frame_rng = np.random.default_rng(int(t * 60))
        sh_x = frame_rng.uniform(-3, 3) * shake_k if shake_k > 0 else 0.0
        sh_y = frame_rng.uniform(-3, 3) * shake_k if shake_k > 0 else 0.0

        m = cv2.getRotationMatrix2D((pw / 2, ph / 2), angle, 1.0)
        m[0, 2] += 0
        fg = _shift_layer(fg_plate, fg_dx + sh_x, fg_dy + sh_y)
        fg = cv2.warpAffine(fg, m, (pw, ph), borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        bg = _shift_layer(bg_plate, bg_dx + sh_x, sh_y)

        comp = np.clip(bg + fg, 0, 255)

        zoom = 1.02 + 0.06 * p
        cw, ch = int(W / zoom), int(H / zoom)
        cx = int(base_dx + (p - 0.5) * 18 * (1 if zoom_dir > 0 else -1))
        cy = int(base_dy + (p - 0.5) * 10)
        cx = max(0, min(pw - cw, cx))
        cy = max(0, min(ph - ch, cy))
        frame = cv2.resize(comp[cy:cy + ch, cx:cx + cw], (W, H), interpolation=cv2.INTER_LINEAR)

        flick = 1.0 + 0.035 * np.sin(2 * np.pi * 0.7 * t)
        for ft in flicker_times:
            d = abs(p - ft)
            if d < 0.02:
                flick *= 0.82 + 9.0 * d
        frame = frame * flick

        off1 = int((t * 10) % fog[0].shape[0])
        off2 = int((t * 16) % fog[1].shape[0])
        f1 = np.roll(fog[0], off1, axis=0)
        f2 = np.roll(fog[1], -off2, axis=0)
        fog_img = ((f1 + f2) / 2)
        fog_img = cv2.resize(fog_img, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
        frame = frame + fog_img * fog_strength * 255 * 0.35

        for (x0, y0, speed, alpha) in dust:
            x = int((x0 + speed * t * 6) % W)
            y = int((y0 - speed * t * 14) % H)
            frame[max(0, y - 2):y + 3, max(0, x - 2):x + 3] += 60 * alpha

        for (x0, y0, speed, alpha) in drops:
            x = int(x0) % W
            y = int((y0 + speed * t * 260) % (H + 60)) - 30
            ln = int(speed * 22)
            frame[max(0, y - ln):y, x:x + 2] += 110 * alpha

        return np.clip(frame, 0, 255).astype(np.uint8)

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
        img = Image.open(scene["image"]).convert("RGB").resize((W + 160, H + 160), Image.LANCZOS)
        tmp = scene["image"].rsplit(".", 1)[0] + "_prep.jpg"
        img.save(tmp, quality=92)
        clip = _scene_clip(tmp, duration, 1 if i % 2 == 0 else -1,
                           seed=1000 + i * 77).with_start(cursor)
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
