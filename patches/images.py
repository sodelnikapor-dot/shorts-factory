"""Генерация иллюстраций в нарисованном стиле через открытый API pollinations.ai (flux, без ключа)."""
import io
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request

import cv2
import numpy as np
from PIL import Image, ImageFilter

IMAGE_URL = "https://image.pollinations.ai/prompt/{prompt}"
STYLE = (
    "flat 2D cartoon animation still frame, cel-shaded, thick black outlines, "
    "simple bold shapes, flat saturated colors, stylized cartoon characters "
    "with big expressive eyes and exaggerated features, cartoon background "
    "art, western animated TV series style, vertical composition, no text, no "
    "letters, no watermark"
)


def _cartoonize(img: Image.Image) -> Image.Image:
    bgr = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
    bgr = cv2.edgePreservingFilter(bgr, flags=1, sigma_s=60, sigma_r=0.4)
    styl = cv2.stylization(bgr, sigma_s=50, sigma_r=0.4)
    quant = (np.round(styl / 36) * 36).astype(np.uint8)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, 60, 140)
    edges = cv2.dilate(edges, np.ones((2, 2), np.uint8), iterations=1)
    edges = cv2.medianBlur(edges, 3)
    dark = np.clip((255 - edges.astype(np.float32)) / 255.0, 0.15, 1.0)[..., None]
    out = (quant.astype(np.float32) * dark).clip(0, 255).astype(np.uint8)
    out = cv2.bilateralFilter(out, 7, 100, 100)
    return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))


def generate_image(prompt: str, out_path: str, width: int = 1080, height: int = 1920,
                   retries: int = 6) -> str:
    full = f"{STYLE}, {prompt}"
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
            img = _cartoonize(img)
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


if __name__ == "__main__":
    print(generate_image(
        "cartoon boy peeking out from under a blanket in a dark bedroom, "
        "shadowy figure in the doorway",
        "test_image.jpg",
    ))
