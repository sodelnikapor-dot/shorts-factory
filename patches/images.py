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
    "vintage historical storybook illustration, detailed ink line art with "
    "rich watercolor painting, warm golden light, bright clear colors, aged "
    "parchment background, clear readable composition, expressive "
    "characters, cinematic wide shot, highly detailed, masterpiece, vertical "
    "composition, no text, no letters, no watermark"
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


if __name__ == "__main__":
    print(generate_image(
        "ancient roman legionary standing on a battlefield at dusk",
        "test_image.jpg",
    ))
