"""
Идея + сценарий для исторического шортса. Приоритет провайдеров:
GEMINI_API_KEY (бесплатный Gemini API, лучшее качество) -> MISTRAL_API_KEY ->
открытый API pollinations (без ключа). Каждый кандидат оценивается на связность,
конкретику и структуру; из нескольких попыток берётся лучший."""
import json
import os
import random
import re
import time
import urllib.parse
import urllib.request

POLLINATIONS_TEXT = "https://text.pollinations.ai/openai"
POLLINATIONS_GET = "https://text.pollinations.ai/{prompt}?model=openai-fast"

ERAS = [
    "Древний Египет", "Древний Рим", "Древняя Греция", "Средневековье",
    "Викинги", "Древняя Русь", "Российская империя", "Эпоха Наполеона",
    "Вторая мировая война", "Эпоха Возрождения", "Древний Китай",
    "Ацтеки и майя", "Золотая Орда", "Византия", "Эпоха великих географических открытий",
]

PROMPT_TMPL = """Ты — сценарист YouTube Shorts по истории. Придумай ОДИН удивительный, но РЕАЛЬНЫЙ исторический факт из эпохи: {era}.

Требования к сценарию:
- Текст для озвучки на русском языке, 45-55 секунд при чтении (примерно 110-140 слов).
- Первая фраза (hook) — не более 10 слов, без приветствий. Начни с интриги, шока или парадокса: «Этот человек...», «В 1943 году...», «Никто не знал, что...».
- Рассказывай в настоящем времени, короткими предложениями (максимум 12 слов), просто, как для друга.
- Обязательна конкретика: имена, цифры, даты, места. Цифры в начале фраз захватывают внимание.
- 3-5 смысловых битов, каждый — отдельная сцена, с нарастающим напряжением от сцены к сцене.
- Финал — мощный вывод или неожиданный поворот, который хочется пересказать другу.
- Никаких выдумок: только реальные факты. Если не уверен в точности — выбери другой факт.
- Запрещены штампы: «интересно, что», «в истории было», «как известно», «давайте узнаем».

Требования к title:
- КАПСОМ, до 80 символов, в стиле: «ЭТОТ МАТЕМАТИК СПАС ТЫСЯЧИ САМОЛЕТОВ ВО ВРЕМЯ ВОЙНЫ!»
- Интрига плюс конкретика (цифра или имя), без обмана зрителя.

Требования к image_prompt (на английском):
- Опиши конкретную драматичную сцену: кто, что делает, где, эмоции, детали эпохи.
- Главный объект в центре кадра, вертикальная композиция.

Верни СТРОГО валидный JSON без markdown в формате:
{{
  "title": "...",
  "hook": "...",
  "scenes": [
    {{"text": "текст озвучки этой сцены", "image_prompt": "описание сцены на английском в стиле vintage historical illustration, engraving, ink and watercolor"}}
  ],
  "description": "описание видео для YouTube, 2-3 предложения на русском",
  "tags": ["#shorts", "история", "ещё 3-5 тегов"]
}}"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"JSON не найден в ответе модели: {text[:200]}")
    return json.loads(match.group(0))


def _ask_gemini(prompt: str) -> str:
    key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={key}")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 8192},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _ask_mistral(prompt: str, api_key: str) -> str:
    req = urllib.request.Request(
        "https://api.mistral.ai/v1/chat/completions",
        data=json.dumps({
            "model": os.environ.get("MISTRAL_MODEL", "mistral-small-latest"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9,
            "max_tokens": 4096,
        }).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def _ask_pollinations(prompt: str) -> str:
    body = json.dumps({
        "model": os.environ.get("SHORTS_TEXT_MODEL", "openai-fast"),
        "messages": [{"role": "user", "content": prompt}],
        "seed": random.randint(0, 10**9),
        "max_tokens": 3000,
        "reasoning_effort": "low",
    }).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "shorts-factory/1.0"}
    token = os.environ.get("POLLINATIONS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_err = None
    for _ in range(4):
        req = urllib.request.Request(POLLINATIONS_TEXT, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as err:
            last_err = err
            if err.code in (402, 429):
                retry_after = (err.headers or {}).get("Retry-After", "")
                delay = int(retry_after) + 3 if retry_after.isdigit() else 35
                time.sleep(delay)
            else:
                break
    url = POLLINATIONS_GET.format(prompt=urllib.parse.quote(prompt))
    with urllib.request.urlopen(url, timeout=180) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _ask_llm(prompt: str) -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return _ask_gemini(prompt)
    if os.environ.get("MISTRAL_API_KEY"):
        return _ask_mistral(prompt, os.environ["MISTRAL_API_KEY"])
    return _ask_pollinations(prompt)


STOPWORDS = frozenset(
    """
    и в не на я быть он с что а по это как но его к у же вы за бы из её о да
    только мне было вот от меня ещё нет ему теперь когда даже ну вдруг ли если
    уже или ни до там потом себя ничего может тут где есть надо для мы их чем
    была сам без раз тоже себе под будет тогда кто потому этого какой совсем
    здесь один почти мой тем чтобы сейчас были куда зачем всех можно при об
    хорошо свою этой перед иногда лучше чуть том нельзя такой им более всегда
    конечно всю между этот эта они то так ведь очень весь вся все свой свои над
    через после про них нас вас тебя ей твой наш ваш который которые которая
    которое оно она ты хотя поэтому просто вместе сегодня вчера никогда давно
    год года годы лет время куда откуда почему зачем
    """.split()
)


def _words(text: str) -> list[str]:
    return re.findall(r"[а-яёa-z]+", text.lower())


def _score(script: dict) -> float:
    """0..1: связность (доля служебных слов), конкретика, КАПС-title, длина."""
    texts = [sc.get("text", "") for sc in script.get("scenes", [])]
    if not texts:
        return 0.0
    words = _words(" ".join(texts))
    if len(words) < 80:
        return 0.0
    stop_ratio = sum(w in STOPWORDS for w in words) / len(words)
    fluency = min(stop_ratio / 0.32, 1.0)
    concrete = sum(1 for t in texts if re.search(r"\d", t)) / len(texts)
    title = script.get("title", "")
    caps = 1.0 if title and title == title.upper() and len(title) <= 90 else 0.0
    length_fit = 1.0 if 100 <= len(words) <= 170 else 0.5
    return 0.4 * fluency + 0.25 * concrete + 0.15 * caps + 0.2 * length_fit


def _normalize(script: dict) -> dict:
    for key in ("title", "hook", "description"):
        if isinstance(script.get(key), str):
            script[key] = script[key].replace("\u202f", " ").replace("\u00a0", " ").strip()
    for sc in script.get("scenes", []):
        for key in ("text", "image_prompt"):
            if isinstance(sc.get(key), str):
                sc[key] = sc[key].replace("\u202f", " ").replace("\u00a0", " ").strip()
    return script


def generate_script(era: str | None = None) -> dict:
    era = era or random.choice(ERAS)
    prompt = PROMPT_TMPL.format(era=era)
    best: dict | None = None
    best_score = 0.0
    last_err = None
    for _ in range(5):
        try:
            script = _normalize(_extract_json(_ask_llm(prompt)))
            if script.get("scenes") and script.get("hook"):
                script["era"] = era
                score = _score(script)
                if score > best_score:
                    best, best_score = script, score
                if best_score >= 0.75:
                    break
        except Exception as err:  # noqa: BLE001
            last_err = err
            time.sleep(15 + 15 * random.random())
    if best is None:
        raise RuntimeError(f"Не удалось получить сценарий: {last_err}")
    print(f"      качество сценария: {best_score:.0%}")
    return best


if __name__ == "__main__":
    import pprint
    pprint.pprint(generate_script())
