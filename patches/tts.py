"""
Озвучка через edge-tts: динамическая «живая» подача — фразы с разным темпом и тоном,
драматические паузы. Возвращает пословные тайминги для субтитров.
"""
import asyncio
import json
import os
import re
import time

import edge_tts
from moviepy import AudioFileClip, concatenate_audioclips

VOICE = os.environ.get("SHORTS_VOICE", "ru-RU-DmitryNeural")
FALLBACK_VOICES = ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"]


class _EdgeDown(RuntimeError):
    """edge-tts недоступен целиком (блокировки/пустой звук) — нужен резервный движок."""


def _gtts_one(text: str, mp3_path: str) -> None:
    from gtts import gTTS
    gTTS(text, lang="ru").save(mp3_path)


def _estimate_words(text: str, dur: float) -> list[dict]:
    """Резервный движок не отдаёт тайминги — распределяем слова по длине фразы."""
    words = [w for w in text.split() if re.search(r"[\w\u0400-\u04FF]", w)]
    if not words:
        return []
    weights = [len(w) + 1.5 for w in words]
    total = sum(weights)
    out, cursor = [], 0.0
    for i, (w, wt) in enumerate(zip(words, weights)):
        d = dur * wt / total
        out.append({"word": w, "start": cursor, "duration": d,
                    "break_after": i == len(words) - 1})
        cursor += d
    return out


def _plan_delivery(sentences: list[str]) -> list[tuple[str, str, float]]:
    """Для каждой фразы: (rate, pitch, пауза после неё)."""
    plan = []
    n = len(sentences)
    for i, s in enumerate(sentences):
        low = s.lower()
        words = len(s.split())
        if i == 0:
            rate, pitch, gap = "+12%", "+3Hz", 0.35
        elif i == n - 1 and "подпишись" in low:
            rate, pitch, gap = "+8%", "+2Hz", 0.0
        elif i >= n - 2:
            rate, pitch, gap = "+2%", "-2Hz", 0.55
        elif s.endswith(("?", "!")):
            rate, pitch, gap = "+10%", "+2Hz", 0.30
        elif words <= 4:
            rate, pitch, gap = "+14%", "+1Hz", 0.40
        else:
            rate, pitch, gap = "+7%", "+0Hz", 0.30
        plan.append((rate, pitch, gap))
    return plan


async def _tts_one(text: str, mp3_path: str, voice: str, rate: str, pitch: str) -> list[dict]:
    tts = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
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


def _split_sentence(s: str) -> list[str] | None:
    """Делит упрямую фразу на две части: по знакам препинания, иначе пополам по словам."""
    parts = [p.strip() for p in re.split(r"(?<=[,;:—])\s+", s) if p.strip()]
    if len(parts) > 1:
        half = len(parts) // 2
        return [" ".join(parts[:half]), " ".join(parts[half:])]
    words = s.split()
    if len(words) < 2:
        return None
    mid = len(words) // 2
    return [" ".join(words[:mid]), " ".join(words[mid:])]


def _tts_sentence(sentence: str, base_path: str, rate: str, pitch: str,
                  gap: float, depth: int = 0) -> list[tuple[str, float, list, float]]:
    """Озвучивает одну фразу; если сервис отдаёт пустой звук — дробит её на части.
    Возвращает список (path, duration, words, gap_after)."""
    last_err = None
    for attempt in range(4):
        voice = VOICE if attempt < 2 else FALLBACK_VOICES[attempt % 2]
        tmp = base_path + f".a{attempt}.mp3"
        try:
            words = asyncio.run(_tts_one(sentence, tmp, voice, rate, pitch))
            dur = AudioFileClip(tmp).duration
            if dur <= 0.05:
                raise RuntimeError("пустой звук от сервиса")
            return [(tmp, dur, words, gap)]
        except Exception as err:  # noqa: BLE001
            last_err = err
            time.sleep(4 * (attempt + 1))
    if depth < 2:
        halves = _split_sentence(sentence)
        if halves:
            print(f"[tts] фраза не озвучилась ({last_err}); дроблю на {len(halves)} части", flush=True)
            try:
                out = []
                for k, half in enumerate(halves):
                    out.extend(_tts_sentence(half, f"{base_path}.s{k}", rate, pitch,
                                             0.15 if k == 0 else gap, depth + 1))
                return out
            except RuntimeError as err:
                if isinstance(err, _EdgeDown):
                    raise
    raise _EdgeDown(str(last_err))


def synthesize(text: str, mp3_path: str) -> list[dict]:
    """Озвучивает text живой подачей, пишет mp3, возвращает пословные тайминги (сек)."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s.strip()]
    if not sentences:
        sentences = [text.strip()]
    plan = _plan_delivery(sentences)

    pieces = []  # (path, dur, words, gap_after)
    edge_ok = True
    for (rate, pitch, gap), sentence in zip(plan, sentences):
        if edge_ok:
            try:
                pieces.extend(_tts_sentence(sentence, mp3_path + f".part{len(pieces)}", rate, pitch, gap))
                continue
            except _EdgeDown as err:
                edge_ok = False
                print(f"[tts] edge-tts недоступен ({err}); сцена — резервным движком gTTS", flush=True)
        tmp = mp3_path + f".part{len(pieces)}.mp3"
        for attempt in range(3):
            try:
                _gtts_one(sentence, tmp)
                dur = AudioFileClip(tmp).duration
                break
            except Exception as err:  # noqa: BLE001
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
        pieces.append((tmp, dur, _estimate_words(sentence, dur), gap))

    clips = [AudioFileClip(p) for p, _d, _w, _g in pieces]
    final = concatenate_audioclips(clips)
    final.write_audiofile(mp3_path, logger=None)
    for c in clips:
        c.close()
    final.close()

    timings = []
    cursor = 0.0
    for path, dur, words, gap in pieces:
        for j, w in enumerate(words):
            timings.append({
                "word": w["word"],
                "start": round(cursor + w["start"], 2),
                "duration": w["duration"],
                "break_after": j == len(words) - 1,
            })
        cursor += dur + gap
        try:
            os.remove(path)
        except OSError:
            pass
    return timings


def build_subtitles(word_timings: list[dict], max_chars: int = 18, pause: float = 0.45) -> list[dict]:
    """Группирует слова в короткие фразы для pop-субтитров (1-3 слова)."""
    subs, current, start = [], [], None
    prev_end = None
    for w in word_timings:
        if start is None:
            start = w["start"]
        gap_broken = prev_end is not None and w["start"] - prev_end > pause
        force_break = w.get("break_after", False)
        current.append(w)
        line = " ".join(x["word"] for x in current)
        ends_sentence = bool(re.search(r"[.!?…]$", w["word"]))
        if len(line) >= max_chars or ends_sentence or gap_broken or force_break:
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
        prev = merged[-1]["text"] if merged else ""
        crosses_sentence = prev.endswith((".", "!", "?", "…"))
        if merged and len(prev) < 6 and not crosses_sentence:
            merged[-1]["text"] += " " + sub["text"]
            merged[-1]["end"] = sub["end"]
        else:
            merged.append(dict(sub))
    return merged


if __name__ == "__main__":
    timings = synthesize("Привет! Это тест озвучки. Слушай, как звучит.", "test.mp3")
    print(json.dumps(build_subtitles(timings), ensure_ascii=False, indent=2))
