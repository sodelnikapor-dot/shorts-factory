"""Генерация иллюстраций в нарисованном стиле через открытый API pollinations.ai (flux, без ключа)."""
import io
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image, ImageFilter

IMAGE_URL = "https://image.pollinations.ai/prompt/{prompt}"
STYLE = (
    "vintage historical illustration, detailed copperplate engraving line art "
    "with ink and watercolor wash, aged parchment texture, sepia and muted "
    "earth tones, dramatic chiaroscuro lighting, cinematic composition, "
    "painterly, highly detailed, masterpiece, vertical composition, no text, "
    "no letters, no watermark"
)


def _fallback_image(out_path: str, width: int, height: int) -> str:
    top, bottom = (224, 198, 158), (58, 42, 28)
    grad = np.zeros((height, width, 3), dtype=np.float32)
    for y in range(height):
        t = y / max(height - 1, 1)
        grad[y, :] = [t * b + (1 - t) * a for a, b in zip(top, bottom)]
    img = Image.fromarray(grad.astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(2))
    img.save(out_path, quality=92)
    return out_path


def generate_image(prompt: str, out_path: str, width: int = 1080, height: int = 1920,
                   retries: int = 9) -> str:
    full = f"{prompt}, {STYLE}"
    url = IMAGE_URL.format(prompt=urllib.parse.quote(full))
    url += (f"?width={width}&height={height}&model=flux&nologo=true"
            f"&referrer=shortsfactory&seed={random.randint(0, 10**9)}")
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
            if img.size != (width, height):
                img = img.resize((width, height), Image.LANCZOS)
                img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=2))
            img.save(out_path, quality=92)
            time.sleep(46)
            return out_path
        except urllib.error.HTTPError as err:
            last_err = err
            if err.code in (402, 429):
                time.sleep(70)
            else:
                time.sleep(5)
        except Exception as err:  # noqa: BLE001
            last_err = err
            time.sleep(5)
    print(f"!!! изображение не сгенерировано ({last_err}), использую фон-заглушку", flush=True)
    return _fallback_image(out_path, width, height)


if __name__ == "__main__":
    print(generate_image(
        "napoleon on horseback retreating from a swarm of rabbits in a field",
        "test_image.jpg",
    ))
