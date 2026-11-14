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
import urllib.request

POLLINATIONS_TEXT = "https://text.pollinations.ai/openai"

ERAS = [
    "Древний Египет", "Древний Рим", "Древняя Греция", "Средневековье",
    "Викинги", "Древняя Русь", "Российская империя", "Эпоха Наполеона",
    "Вторая мировая война", "Эпоха Возрождения", "Древний Китай",
    "Ацтеки и майя", "Золотая Орда", "Византия", "Эпоха великих географических открытий",
]

FACTS = [
    {"era": "Древний Китай", "fact": "В 132 году китайский астроном Чжан Хэн изобрёл первый в мире сейсмоскоп — бронзовый сосуд с восемью драконами, который определял направление землетрясения за сотни километров."},
    {"era": "Древний Китай", "fact": "Терракотовую армию — более 8000 глиняных воинов императора Цинь Шихуанди — случайно нашли крестьяне в 1974 году, копая колодец."},
    {"era": "Древний Китай", "fact": "Бумагу изобрёл придворный сановник Цай Лунь в 105 году, сделав её из древесной коры и тряпья."},
    {"era": "Древний Египет", "fact": "Пирамиду Хеопса сложили из 2,3 миллиона каменных блоков примерно за 20 лет — это по 12 блоков в час, днём и ночью, без перерыва."},
    {"era": "Древний Египет", "fact": "Фараон Рамсес II правил 66 лет, дожил до 90 лет и пережил почти всех своих сотню детей."},
    {"era": "Древний Египет", "fact": "Тутанхамон стал фараоном в 9 лет, а умер в 19 — его нетронутую гробницу нашли только в 1922 году."},
    {"era": "Древний Рим", "fact": "Пантеон в Риме стоит почти 1900 лет, и его бетонный купол диаметром 43 метра до сих пор самый большой в мире из неармированного бетона."},
    {"era": "Древний Рим", "fact": "В 79 году за один день Везувий погреб Помпеи под 6-метровым слоем пепла."},
    {"era": "Древний Рим", "fact": "Колизей вмещал 50 000 зрителей и мог опустеть за 10 минут — через 80 выходов по всему амфитеатру."},
    {"era": "Древняя Греция", "fact": "В I веке н.э. греческий инженер Герон Александрийский создал эолипил — первую паровую машину, но считал её просто игрушкой."},
    {"era": "Древняя Греция", "fact": "В 490 году до н.э. воин Фидиппид пробежал около 40 км от Марафона до Афин, сообщил о победе и упал замертво — так появился марафон."},
    {"era": "Древняя Греция", "fact": "Антикитерский механизм, поднятый со дна моря в 1901 году, оказался астрономическим калькулятором, созданным за 100 лет до н.э."},
    {"era": "Средневековье", "fact": "В 1518 году в Страсбурге началась танцевальная чума: одна женщина не могла перестать танцевать, и через месяц танцевали уже около 400 человек."},
    {"era": "Средневековье", "fact": "Кёльнский собор строили 632 года — с 1248 по 1880 год."},
    {"era": "Средневековье", "fact": "В 1348 году в Европу пришла «Чёрная смерть»: за пять лет чума унесла почти треть населения континента."},
    {"era": "Викинги", "fact": "Около 1000 года викинг Лейф Эриксон доплыл до Северной Америки почти за 500 лет до Колумба — его поселение в Л'Анс-о-Медоуз нашли археологи."},
    {"era": "Викинги", "fact": "В 865 году «Великая языческая армия» викингов высадилась в Англии и за десять лет захватила почти все англосаксонские королевства."},
    {"era": "Древняя Русь", "fact": "Новгородский мальчик Онфим в XIII веке процарапывал на бересте буквы и рисунки — его «шпаргалки» сохранились до сих пор."},
    {"era": "Древняя Русь", "fact": "В 1147 году Москва впервые упомянута в летописи: Юрий Долгорукий пригласил союзника «погостить в Москов»."},
    {"era": "Российская империя", "fact": "В 1834 году отец и сын Черепановы построили первый в Российской империи паровоз, но железные дороги признали невыгодными — дешевле оказался труд крепостных."},
    {"era": "Российская империя", "fact": "В 1730 году 19-летний Михайло Ломоносов тайно ушёл с рыбным обозом из северной деревни в Москву — и через несколько лет стал первым русским академиком."},
    {"era": "Эпоха Наполеона", "fact": "Наполеон не был низким: около 169 см — нормальный рост для его эпохи. «Маленьким» его сделала британская пропаганда."},
    {"era": "Эпоха Наполеона", "fact": "В 1812 году Великая армия Наполеона вошла в Россию числом около 600 000 солдат, а назад вернулось меньше 30 000."},
    {"era": "Вторая мировая война", "fact": "В 1943 году математик Абрахам Вальд спас тысячи бомбардировщиков: он понял, что бронировать надо те места, где у вернувшихся самолётов пробоин НЕТ — туда попадали те, кто не вернулся."},
    {"era": "Вторая мировая война", "fact": "Женщины 46-го гвардейского ночного бомбардировочного полка летали на фанерных самолётах У-2 только по ночам — немцы прозвали их «ночными ведьмами»."},
    {"era": "Вторая мировая война", "fact": "Снайпер Василий Зайцев за пять месяцев Сталинградской битвы уничтожил 225 солдат и офицеров противника."},
    {"era": "Эпоха Возрождения", "fact": "В 1493 году Леонардо да Винчи нарисовал «воздушный винт» — эскиз предка вертолёта. Сам аппарат так и не взлетел."},
    {"era": "Эпоха Возрождения", "fact": "«Мона Лиза» несколько лет висела в спальне Наполеона во дворце Тюильри, прежде чем попасть в Лувр."},
    {"era": "Византия", "fact": "Собор Святой Софии построили всего за 5 лет (532-537). Его купол диаметром 31 метр современники считали «созданным не людьми»."},
    {"era": "Византия", "fact": "Греческий огонь — жидкость, горевшую даже на воде, — был строжайшей государственной тайной Византии. Рецепт утерян навсегда."},
    {"era": "Ацтеки и майя", "fact": "Ацтеки платили какао-бобами: за 10 бобов можно было купить кролика, а за 100 — раба."},
    {"era": "Ацтеки и майя", "fact": "В 1519 году ацтекская столица Теночтитлан с 200 000 жителями была больше любого европейского города того времени."},
    {"era": "Ацтеки и майя", "fact": "Дрезденский кодекс майя содержит таблицы солнечных затмений, позволявшие предсказывать их на десятилетия вперёд — без телескопов."},
    {"era": "Золотая Орда", "fact": "В 1382 году хан Тохтамыш взял Москву обманом: обещал мир, а когда горожане открыли ворота — штурмом разграбил город."},
    {"era": "Золотая Орда", "fact": "В Монгольской империи работала почтовая служба «ям»: гонец проезжал до 300 км в сутки, меняя лошадей на станциях."},
    {"era": "Эпоха великих географических открытий", "fact": "Из примерно 250 моряков Магеллана домой вернулись только 18 — но их плавание 1519-1522 годов впервые доказало, что Земля круглая."},
    {"era": "Эпоха великих географических открытий", "fact": "Колумб до конца жизни был уверен, что открыл путь в Азию, и называл новые земли «Вест-Индией»."},
]
PROMPT_TMPL = """Ты — сценарист YouTube Shorts по истории. Вот РЕАЛЬНЫЙ проверенный исторический факт из эпохи «{era}»:

«{fact}»

Напиши захватывающий сценарий шортса СТРОГО на основе этого факта.
Правила жёсткие:
- Не выдумывай ничего сверх факта: никаких других событий, имён и цифр, которых нет в факте.
- Все имена, даты и числа — точно как в факте.
- Добавлять можно только атмосферу, эмоции и связки между сценами.

Требования к сценарию:
- Текст для озвучки на русском языке, 60-80 секунд при чтении (примерно 150-190 слов).
- Первая фраза (hook) — не более 10 слов, без приветствий, ОТ ПЕРВОГО ЛИЦА: «Меня зовут...», «Я — единственный, кто...», «Мне сказали, что...».
- ГЛАВНОЕ: веди рассказ ОТ ПЕРВОГО ЛИЦА — от лица героя факта. Зритель находится в голове героя: его страх, надежда, решения.
- Рассказывай в настоящем времени, короткими предложениями (максимум 12 слов), просто, как для друга.
- Тон — как у каналов-миллионников: живо, интригующе, зритель не может оторваться. Пример тона: «Представь: ты солдат, и твой самолёт дырявят со всех сторон. Куда ставить броню? Ошибёшься — погибнешь.»
- Обязательна конкретика: имена, цифры, даты, места. Цифры в начале фраз захватывают внимание.
- 4-5 смысловых битов, каждый — отдельная сцена, с нарастающим напряжением от сцены к сцене.
- Финал — мощный вывод или неожиданный поворот, который хочется пересказать другу.
- Никаких выдумок: только реальные факты. Если не уверен в точности — выбери другой факт.
- Запрещены штампы: «интересно, что», «в истории было», «как известно», «давайте узнаем».

Требования к title:
- Вирусный стиль: часть слов КАПСОМ, многоточие для интриги, один эмодзи в конце. Примеры: «Я ЕДИНСТВЕННЫЙ ЗРЯЧИЙ в городе слепых… и монстр это ПОНЯЛ 👁️», «МЕНЯ ПРЕДАЛ лучший друг… но я всё ЗНАЛ 😱», «В ЭТОМ ГОРОДЕ НЕЛЬЗЯ ИЗДАВАТЬ НИ ЗВУКА… ИНАЧЕ ОНИ ПРИДУТ 🔇»
- От первого лица или про героя, 60-90 символов, интрига + конкретика (цифра или имя), без обмана зрителя.

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
    data = json.loads(match.group(0))
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        raise ValueError(f"неожиданный тип ответа: {type(data).__name__}")
    return data


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
    token = os.environ.get("POLLINATIONS_TOKEN")
    model = os.environ.get("SHORTS_TEXT_MODEL", "openai" if token else "openai-fast")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "seed": random.randint(0, 10**9),
        "max_tokens": 16000 if token else 3000,
        "reasoning_effort": "low",
    }).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "shorts-factory/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_err = None
    for _ in range(8):
        req = urllib.request.Request(POLLINATIONS_TEXT, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as err:
            last_err = err
            if err.code in (402, 429):
                retry_after = (err.headers or {}).get("Retry-After", "")
                delay = int(retry_after) + 3 if retry_after.isdigit() else 48
                time.sleep(delay)
            else:
                time.sleep(8)
        except Exception as err:  # noqa: BLE001
            last_err = err
            time.sleep(8)
    raise last_err


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
    texts = [sc.get("text", "") if isinstance(sc, dict) else str(sc)
             for sc in script.get("scenes", [])]
    if not texts:
        return 0.0
    words = _words(" ".join(texts))
    if len(words) < 80:
        return 0.0
    stop_ratio = sum(w in STOPWORDS for w in words) / len(words)
    fluency = min(stop_ratio / 0.32, 1.0)
    concrete = sum(1 for t in texts if re.search(r"\d", t)) / len(texts)
    title = str(script.get("title") or "")
    caps = 1.0 if title and title == title.upper() and len(title) <= 90 else 0.0
    length_fit = 1.0 if 130 <= len(words) <= 200 else 0.5
    return 0.4 * fluency + 0.25 * concrete + 0.15 * caps + 0.2 * length_fit


def _normalize(script: dict) -> dict:
    topic = str(script.get("topic") or script.get("title") or "historical scene")
    scenes = []
    for sc in script.get("scenes", []):
        if isinstance(sc, str):
            sc = {"text": sc, "image_prompt": ""}
        if isinstance(sc, dict):
            sc = dict(sc)
            for key in ("text", "image_prompt"):
                if not isinstance(sc.get(key), str):
                    sc[key] = str(sc.get(key) or "")
            if not sc["image_prompt"].strip():
                base = sc["text"].strip() or topic
                sc["image_prompt"] = " ".join(base.split()[:12]) or topic
            scenes.append(sc)
    script["scenes"] = scenes
    if not isinstance(script.get("hook"), str):
        first = scenes[0]["text"] if scenes else ""
        script["hook"] = first
    for key in ("title", "hook", "description"):
        if isinstance(script.get(key), str):
            script[key] = script[key].replace("\u202f", " ").replace("\u00a0", " ").strip()
    for sc in script.get("scenes", []):
        for key in ("text", "image_prompt"):
            if isinstance(sc.get(key), str):
                sc[key] = sc[key].replace("\u202f", " ").replace("\u00a0", " ").strip()
    return script


EDIT_TMPL = """Вот сценарий YouTube Shorts на русском в формате JSON:
{json}

Исходный реальный факт, на котором он основан:
«{fact}»

Отредактируй сценарий:
- Исправь ВСЕ грамматические ошибки и бессмысленные или искажённые слова — текст должен звучать как грамотная живая русская речь.
- Стиль: простой рассказ для друга, настоящее время, короткие предложения, интрига с первых слов, рассказ ОТ ПЕРВОГО ЛИЦА.
- Сохрани факты ТОЧНО: имена, даты и цифры не менять и ничего нового не добавлять.
- Верни ТОЛЬКО исправленный JSON в том же формате, без markdown и пояснений."""


def _edit_pass(script: dict, fact: str) -> dict:
    try:
        raw = _ask_llm(EDIT_TMPL.format(json=json.dumps(script, ensure_ascii=False), fact=fact))
        edited = _normalize(_extract_json(raw))
        if edited.get("scenes") and edited.get("hook"):
            edited["era"] = script.get("era")
            return edited
    except Exception:  # noqa: BLE001
        pass
    return script


TITLE_TMPL = """Вот заголовок YouTube Shorts на русском: \"{title}\"
О чём видео: {context}
Если в заголовке есть бессмысленные, выдуманные или искажённые слова — замени их на правильные.
Верни ОДНУ строку: вирусный заголовок (часть слов КАПСОМ, многоточие, один эмодзи в конце), 60-90 символов, в стиле «Я ЕДИНСТВЕННЫЙ ЗРЯЧИЙ в городе слепых… и монстр это ПОНЯЛ 👁️». Без пояснений и кавычек."""


def _fix_title(script: dict) -> dict:
    scenes = script.get("scenes") or []
    first = str(scenes[0].get("text", "")) if scenes and isinstance(scenes[0], dict) else ""
    prompt = TITLE_TMPL.format(title=str(script.get("title", "")), context=first[:300])
    try:
        fixed = _ask_llm(prompt).strip().strip('"')
        fixed = fixed.splitlines()[0].strip()
    except Exception:  # noqa: BLE001
        return script
    if 15 <= len(fixed) <= 95 and re.search(r"[А-ЯЁ]", fixed) and re.search(r"[а-яё\w]", fixed.lower()):
        script["title"] = fixed
    return script


def generate_script(era: str | None = None) -> dict:
    pool = [f for f in FACTS if f["era"] == era] if era else FACTS
    chosen = random.choice(pool or FACTS)
    era, fact = chosen["era"], chosen["fact"]
    prompt = PROMPT_TMPL.format(era=era, fact=fact)
    best: dict | None = None
    best_score = 0.0
    last_valid: dict | None = None
    last_err = None
    started = time.time()
    for _ in range(5):
        try:
            script = _normalize(_extract_json(_ask_llm(prompt)))
            if script.get("scenes") and script.get("hook"):
                script["era"] = era
                last_valid = script
                score = _score(script)
                if score > best_score:
                    best, best_score = script, score
                if best_score >= 0.75:
                    break
        except Exception as err:  # noqa: BLE001
            last_err = err
        if time.time() - started > 900:
            break
    if best is None:
        best, best_score = last_valid, 0.0
    if best is None:
        raise RuntimeError(f"Не удалось получить сценарий: {last_err}")
    print(f"      качество сценария: {best_score:.0%}")
    best = _edit_pass(best, fact)
    best = _fix_title(best)
    print(f"      финальный title: {best.get('title', '')}")
    return best


if __name__ == "__main__":
    import pprint
    pprint.pprint(generate_script())
