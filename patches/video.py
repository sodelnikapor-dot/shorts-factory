"""
Сборка вертикального видео 1080x1920 в стиле Кубыча: сильная Ken Burns анимация,
pop-субтитры по центру, процедурная кинематографичная фоновая музыка, озвучка.
"""
import os
import urllib.request
import wave

import numpy as np
from moviepy import (AudioFileClip, CompositeAudioClip, CompositeVideoClip, ImageClip,
                     VideoClip, concatenate_audioclips)
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
FONT_PATH = os.path.join(ASSETS, "NotoSans-Bold.ttf")
FONT_URL = ("https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/"
            "fonts/NotoSans/hinted/ttf/NotoSans-Bold.ttf")


def _ensure_font() -> str:
    if not os.path.exists(FONT_PATH):
        os.makedirs(ASSETS, exist_ok=True)
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
    return FONT_PATH
W, H = 1080, 1920
FPS = 24


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


def _scene_clip(image_path: str, duration: float, zoom_dir: int) -> VideoClip:
    """Ken Burns: сильный зум + горизонтальный дрейф, живая анимация кадра."""
    base = ImageClip(image_path)
    factor = 1.16 if zoom_dir > 0 else 0.90
    drift = 40 * (1 if zoom_dir > 0 else -1)

    def make(t):
        p = t / max(duration, 0.01)
        scale = 1.0 + (factor - 1.0) * p
        new_w, new_h = int((W + 160) * scale), int((H + 160) * scale)
        frame = base.get_frame(0)
        img = Image.fromarray(frame).resize((new_w, new_h), Image.BILINEAR)
        x = (new_w - W) // 2 + int(drift * (p - 0.5))
        y = (new_h - H) // 2
        x = max(0, min(new_w - W, x))
        y = max(0, min(new_h - H, y))
        return np.asarray(img.crop((x, y, x + W, y + H)))

    return VideoClip(make, duration=duration).with_fps(FPS)


def _make_music(duration: float, wav_path: str) -> str:
    """Процедурный напряжённый кинематографичный эмбиент: низкий дрон + пульс + воздух."""
    sr = 22050
    n = int(duration * sr) + sr
    t = np.arange(n) / sr
    rng = np.random.default_rng(42)

    drone = (0.50 * np.sin(2 * np.pi * 55.0 * t)
             + 0.30 * np.sin(2 * np.pi * 82.5 * t + 0.5)
             + 0.22 * np.sin(2 * np.pi * 110.0 * t + 1.1))
    lfo = 0.65 + 0.35 * np.sin(2 * np.pi * t / 17.0)
    audio = drone * lfo

    pulse_phase = (t / 2.4) % 1.0
    thump = np.exp(-pulse_phase * 8) * np.sin(2 * np.pi * 48.0 * t) * 0.55
    audio += thump

    noise = rng.normal(0, 1, n)
    kernel = np.hanning(201)
    kernel /= kernel.sum()
    audio += np.convolve(noise, kernel, mode="same") * 0.05

    fade = int(2.0 * sr)
    env = np.ones(n)
    env[:fade] = np.linspace(0, 1, fade)
    env[-fade:] = np.linspace(1, 0, fade)
    audio *= env
    audio = np.clip(audio, -1, 1)
    pcm = (audio * 32767 * 0.9).astype(np.int16)
    with wave.open(wav_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(pcm.tobytes())
    return wav_path


def make_video(scenes: list[dict], audio_files: list[str], subtitle_tracks: list[list[dict]],
               out_path: str) -> str:
    """scenes: [{'image': путь}], audio_files: mp3 по сценам, subtitle_tracks: тайминги относительно начала сцены."""
    scene_clips = []
    scene_starts = []
    cursor = 0.0
    for i, (scene, audio) in enumerate(zip(scenes, audio_files)):
        aclip = AudioFileClip(audio)
        duration = aclip.duration + 0.35
        img = Image.open(scene["image"]).convert("RGB").resize((W + 160, H + 160), Image.BILINEAR)
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
            overlay_clips.append(_pop_sub_clip(
                sub["text"],
                scene_starts[i] + sub["start"],
                scene_starts[i] + sub["end"],
            ))
    if overlay_clips:
        video = CompositeVideoClip([video, *overlay_clips], size=(W, H)).with_duration(cursor)

    voice = concatenate_audioclips([AudioFileClip(a) for a in audio_files])
    work_dir = os.path.dirname(os.path.abspath(out_path))
    music = AudioFileClip(_make_music(cursor, os.path.join(work_dir, "ambient.wav")))
    music = music.with_duration(cursor).with_volume_scaled(0.10)
    video = video.with_audio(CompositeAudioClip([voice, music]))

    video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac",
                          preset="medium", ffmpeg_params=["-crf", "21"], logger=None)
    return out_path
