"""Озвучка через edge-tts (бесплатный русский нейроголос) + разметка по времени для субтитров."""
import asyncio
import json
import os
import re
import time

import edge_tts

VOICE = os.environ.get("SHORTS_VOICE", "ru-RU-DmitryNeural")
FALLBACK_VOICES = ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"]
RATE = os.environ.get("SHORTS_RATE", "+6%")
PITCH = os.environ.get("SHORTS_PITCH", "+1Hz")


async def _tts(text: str, mp3_path: str) -> None:
    tts = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await tts.save(mp3_path)


async def _tts_with_offsets(text: str, mp3_path: str, voice: str = VOICE) -> list[dict]:
    tts = edge_tts.Communicate(text, voice, rate=RATE, pitch=PITCH, boundary="WordBoundary")
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
    import edge_tts.exceptions

    last_err = None
    for attempt in range(4):
        voice = VOICE if attempt < 2 else FALLBACK_VOICES[attempt % 2]
        try:
            return asyncio.run(_tts_with_offsets(text, mp3_path, voice))
        except (edge_tts.exceptions.NoAudioReceived, Exception) as err:  # noqa: BLE001
            last_err = err
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Озвучка не удалась: {last_err}")


def build_subtitles(word_timings: list[dict], max_chars: int = 18, pause: float = 0.45) -> list[dict]:
    """Группирует слова в короткие фразы для pop-субтитров (1-3 слова)."""
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
        if merged and len(merged[-1]["text"]) < 6:
            merged[-1]["text"] += " " + sub["text"]
            merged[-1]["end"] = sub["end"]
        else:
            merged.append(dict(sub))
    return merged


if __name__ == "__main__":
    timings = synthesize("Привет! Это тест озвучки исторического шортса.", "test.mp3")
    print(json.dumps(build_subtitles(timings), ensure_ascii=False, indent=2))
