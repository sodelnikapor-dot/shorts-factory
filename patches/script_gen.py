"""
Сценарии для шортсов: реальные исторические факты и загадки истории.
Каждый сценарий — 8 коротких сцен: картинка меняется почти под каждую фразу,
чтобы зритель всегда видел то, о чём говорит диктор. Тексты написаны вручную —
бесплатная LLM даёт ломаный русский, поэтому не используется.
"""
import copy
import os
import random
import time

SCRIPTS = [
    {
        "era": "Загадки истории",
        "title": "КОРАБЛЬ НАШЛИ ПУСТЫМ: ЕДА НА СТОЛЕ, ВЕЩИ НА МЕСТЕ… А ЛЮДЕЙ НЕТ ⚓",
        "description": "Реальная история 1872 года: «Мэри Селест» нашли в океане без единого человека. 150 лет никто не знает, что произошло.",
        "scenes": [
            {"text": "4 декабря 1872 года капитан Морехаус увидел в Атлантике знакомый корабль — «Мэри Селест». Месяц назад он обедал на нём с её капитаном. Но корабль плыл странно: НИКТО им не управлял.",
             "image_prompt": "two 19th century sailing ships on the open Atlantic, calm eerie sea, one ship drifting with empty deck, view from the helm"},
            {"text": "Морехаус поднялся на борт. И увидел то, что до сих пор будоражит моряков.",
             "image_prompt": "a sailor climbing over the railing onto an empty ship deck, rope ladder, fog, tense mood"},
            {"text": "Еда стояла на столе. Груз промышленного спирта был цел. Вещи экипажа — на местах.",
             "image_prompt": "ship cabin interior with untouched food on the table, cargo crates intact, lantern light"},
            {"text": "Но спасательной шлюпки НЕ БЫЛО. И людей не было. Совсем.",
             "image_prompt": "empty ship deck with missing lifeboat davits, fog creeping across the planks, eerie stillness"},
            {"text": "Исчезли десять человек: капитан Бриггс, его жена, двухлетняя дочь и семеро моряков. Посреди океана. Просто ИСЧЕЗЛИ.",
             "image_prompt": "old sepia portraits of a captain, his wife and child and sailors fading into mist"},
            {"text": "Последняя запись в судовом журнале — обычная, за девять дней до находки. Дальше — пустота.",
             "image_prompt": "open ship logbook with a quill pen, last handwritten entry, candlelight, dust"},
            {"text": "Ураган? Но вещи целы. Пираты? Груз не тронут. Самая жуткая версия: они увидели ЧТО-ТО в воде и спустились посмотреть. Шлюпка не вернулась.",
             "image_prompt": "dark ocean surface at night seen from a ship railing, something enormous shadowy underwater, tiny lifeboat descending"},
            {"text": "«Мэри Селест» проплыла дальше сама. 150 лет прошло — а ответа НЕТ. Подпишись.",
             "image_prompt": "a ghostly sailing ship drifting into thick fog at sunset, melancholic mystery"},
        ],
    },
    {
        "era": "Средневековье",
        "title": "В 1518 ГОДУ ЛЮДИ ТАНЦЕВАЛИ БЕЗ ОСТАНОВКИ… НЕКОТОРЫЕ ДО СМЕРТИ 💃",
        "description": "Реальная история: танцевальная чума в Страсбурге. 400 человек не могли остановиться. Учёные до сих пор спорят, почему.",
        "scenes": [
            {"text": "Июль 1518 года, Страсбург. Женщина по имени Труча вышла на улицу и начала танцевать. Без музыки. Без причины.",
             "image_prompt": "medieval woman dancing alone in a narrow cobblestone street, confused onlookers at windows, summer day"},
            {"text": "Она танцевала ШЕСТЬ ДНЕЙ БЕЗ ОСТАНОВКИ. Её не могли остановить.",
             "image_prompt": "exhausted medieval woman still dancing at night, torchlight, desperate faces around her"},
            {"text": "Через месяц за ней потянулись ещё сто человек. Потом — четыреста.",
             "image_prompt": "medieval town square filled with dozens of dancing people, chaos, guards watching in horror"},
            {"text": "Люди танцевали до крови на ногах. Некоторые — ДО СМЕРТИ. Город был в панике.",
             "image_prompt": "collapsed dancers on medieval street, torn shoes, frightened crowd, dramatic sky"},
            {"text": "Врачи того времени поставили диагноз: «горячая кровь». Их лекарство? Танцевать ЕЩЁ БОЛЬШЕ. Для них построили сцену и наняли музыкантов.",
             "image_prompt": "medieval physicians watching from a balcony as musicians play on a wooden stage for the dancers"},
            {"text": "Это сделало только хуже: танцевать стало «можно» — и эпидемия вышла из-под контроля.",
             "image_prompt": "huge crowd dancing wildly around a medieval stage, banners, overwhelming movement"},
            {"text": "Учёные до сих пор спорят: массовая истерия? отравление спорыньёй в хлебе? религиозный стресс? Точного ответа НЕТ.",
             "image_prompt": "old library with scholars studying medieval manuscripts, rye bread on the table, question mood"},
            {"text": "500 лет прошло — а загадка не разгадана. Подпишись.",
             "image_prompt": "moonlit empty medieval square, single pair of worn dancing shoes left on the cobblestones, fog"},
        ],
    },
    {
        "era": "Загадки истории",
        "title": "ВЗРЫВ, ВЫВАЛИВШИЙ 80 МИЛЛИОНОВ ДЕРЕВЬЕВ… И НИКТО НЕ ЗНАЕТ, ЧТО ЭТО БЫЛО 💥",
        "description": "30 июня 1908 года над Сибирью взорвался неизвестный объект. Ударная волна трижды обогнула Землю. Кратера НЕТ.",
        "scenes": [
            {"text": "30 июня 1908 года, Сибирь. В семь утра небо на юге вспыхнуло ЯРЧЕ СОЛНЦА.",
             "image_prompt": "taiga landscape at dawn with a blinding fireball streaking across the sky, trees silhouetted"},
            {"text": "Столб света ударил вниз. Грохот услышали за тысячу километров.",
             "image_prompt": "massive vertical pillar of light and smoke rising above the taiga, birds scattering"},
            {"text": "Взрыв повалил 80 МИЛЛИОНОВ деревьев на площади две тысячи квадратных километров. Это как сотни Хиросим разом.",
             "image_prompt": "vast forest with millions of trees flattened radially outward from a central point, aerial view"},
            {"text": "В ту ночь в Лондоне можно было читать газету в полночь. Небо над Европой светилось.",
             "image_prompt": "London street at midnight glowing with strange bright sky, people reading newspapers outdoors"},
            {"text": "Ударная волна ТРИЖДЫ обогнула Землю. Сейсмографы всего мира её записали.",
             "image_prompt": "old seismograph in a laboratory drawing jagged lines, scientists astonished, globe on the desk"},
            {"text": "А теперь главное: на месте взрыва КРАТЕРА НЕТ.",
             "image_prompt": "expedition of scientists standing in a flattened forest clearing, no crater, confused mood, swampy ground"},
            {"text": "Сотни экспедиций, больше ста гипотез: метеорит, комета, взрыв болотного газа… Даже инопланетяне. Ни одного обломка не нашли.",
             "image_prompt": "researchers with magnifying glasses and shovels searching the taiga soil, scattered expedition camp"},
            {"text": "Самый большой взрыв в истории человечества — и мы не знаем, ЧТО это было. Подпишись.",
             "image_prompt": "night sky over the taiga with a mysterious glow on the horizon, lone explorer looking up"},
        ],
    },
    {
        "era": "Новое время",
        "title": "САМАЯ КОРОТКАЯ ВОЙНА В ИСТОРИИ… ДЛИЛАСЬ 38 МИНУТ ⏱️",
        "description": "27 августа 1896 года Британия и Занзибар начали войну. Она закончилась быстрее, чем урок в школе.",
        "scenes": [
            {"text": "27 августа 1896 года. Британия предъявила Занзибару ультиматум: сменить султана до девяти утра.",
             "image_prompt": "British warships anchored off a tropical island palace, admiral with pocket watch, tense morning"},
            {"text": "Султан отказался. В 9:02 британский флот открыл огонь.",
             "image_prompt": "warships firing broadsides at a coastal palace, smoke and muzzle flashes, morning light"},
            {"text": "Дворец султана разваливался на глазах. Три тысячи защитников против пяти военных кораблей.",
             "image_prompt": "crumbling wooden palace under bombardment, defenders scrambling in the ruins, palm trees burning"},
            {"text": "В 9:40 занзибарский флаг сбили — и война закончилась.",
             "image_prompt": "a flag falling from a broken mast onto the sand, sailors cheering on ships"},
            {"text": "Итого: 38 МИНУТ. Самая короткая война в истории человечества.",
             "image_prompt": "pocket watch showing 9:40 lying on a ship deck, idle cannons, calm sea"},
            {"text": "Потери: около пятисот человек у Занзибара. У британцев — один раненый моряк.",
             "image_prompt": "damaged palace courtyard with survivors tending the wounded, British sailors barely scratched"},
            {"text": "Султан сбежал в немецкое консульство на яхте. С одним чемоданом.",
             "image_prompt": "lonely sultan on a small yacht at dusk, single suitcase beside him, distant coastline"},
            {"text": "Война, короче твоей дороги в школу. Подпишись.",
             "image_prompt": "old school bell and a history book with a warship illustration, playful vintage mood"},
        ],
    },
    {
        "era": "Новое время",
        "title": "ПО ЛОНДОНУ ПРОНЕСЛАСЬ ВОЛНА ПИВА ВЫСОТОЙ С 2-ЭТАЖНЫЙ ДОМ 🍺",
        "description": "17 октября 1814 года в Лондоне лопнул гигантский чан с пивом. Волна снесла дома и убила восемь человек.",
        "scenes": [
            {"text": "17 октября 1814 года, Лондон. На пивоварне «Хорс Шу» лопнул огромный чан: больше МИЛЛИОНА литров портера.",
             "image_prompt": "giant wooden brewery vat bursting, torrent of dark beer exploding through brick walls, workers fleeing"},
            {"text": "Волна пива высотой четыре метра прорвала стену и хлынула в трущобы Сент-Джайлс.",
             "image_prompt": "brown beer wave flooding a narrow London slum street, people running, houses shaking"},
            {"text": "Поток снёс два дома и врезался в паб. Ещё два чана сорвались следом — пива стало ЕЩЁ БОЛЬШЕ.",
             "image_prompt": "collapsing tenement houses and a tavern overwhelmed by a flood of beer, barrels bobbing in the torrent"},
            {"text": "Пиво затопило подвалы, где жили люди. Восемь человек погибли.",
             "image_prompt": "flooded dark cellar with furniture floating in beer, rescuers with lanterns, somber mood"},
            {"text": "Пятеро погибших были на поминках по умершему накануне мальчику. Трагедия на трагедии.",
             "image_prompt": "candlelit wake room in a cellar, mourners' portraits, dark floodwater rising, grief"},
            {"text": "А толпы снаружи… собирали пиво с улицы кружками и чайниками. Пока шла спасательная операция.",
             "image_prompt": "crowd scooping beer from the street with mugs and kettles, chaos mixed with absurdity"},
            {"text": "Суд решил: это «акт Божий». Компания чуть не обанкротилась. Компенсации собирали всем городом.",
             "image_prompt": "old courtroom with a judge in a powdered wig, brewery owners anxious, ledger book open"},
            {"text": "Через год пивоварню снесли. Сегодня на этом месте театр «Доминион». Подпишись.",
             "image_prompt": "grand theatre facade on a busy London street at dusk, ghostly overlay of the old brewery"},
        ],
    },
    {
        "era": "Новое время",
        "title": "ВОЛНА ПАТОКИ 8 МЕТРОВ ВЫСОТОЙ… УБЕЖАТЬ БЫЛО НЕВОЗМОЖНО 🍯",
        "description": "15 января 1919 года по Бостону пронеслась волна из 9 миллионов литров патоки. 21 человек погиб.",
        "scenes": [
            {"text": "15 января 1919 года, Бостон. В половине первого дня по Северному Энду пронёсся грохот — и улицу накрыла волна ПАТОКИ.",
             "image_prompt": "enormous dark molasses wave surging through a Boston street, buildings and a train in its path"},
            {"text": "Резервуар с девятью миллионами литров патоки взорвался в тёплый день после недели морозов.",
             "image_prompt": "bursting industrial steel tank in a rail yard, steel plates flying, molasses gushing out"},
            {"text": "Волна высотой до восьми метров неслась со скоростью 56 км/ч. Бежать было бесполезно.",
             "image_prompt": "people sprinting from a towering sticky brown wave between brick houses, desperate motion"},
            {"text": "Патока снесла дома, вагоны поезда и пожарную часть. Двадцать один человек погиб.",
             "image_prompt": "crushed houses and derailed train cars half-buried in molasses, rescue workers searching"},
            {"text": "Люди вязли в липкой массе, как мухи в паутине. Спасатели шли по колено в патоке.",
             "image_prompt": "rescuers wading knee-deep in dark molasses pulling a trapped man out, exhausting effort"},
            {"text": "Свидетели вспоминали: месяцами в жаркие дни весь район пах патокой.",
             "image_prompt": "summer street corner with people fanning themselves, faint sticky sheen on the pavement"},
            {"text": "Компания выплатила 600 тысяч долларов — гигантские деньги по тем временам. Это был один из первых массовых исков в истории США.",
             "image_prompt": "courtroom with lawyers and stacks of documents, judge's gavel, early 20th century Boston"},
            {"text": "Город чистили неделями. Легенда гласит: в жаркие дни старые кварталы Бостона пахнут патокой ДО СИХ ПОР. Подпишись.",
             "image_prompt": "vintage Boston street at sunset, subtle golden-brown haze, nostalgic mood"},
        ],
    },
    {
        "era": "Новое время",
        "title": "НАПОЛЕОНА ПОБЕДИЛИ… КРОЛИКИ 🐇",
        "description": "Реальная история 1807 года: император Франции, гроза Европы, устроил охоту на кроликов — и был разгромлен.",
        "scenes": [
            {"text": "Июль 1807 года. После победы над Россией и Пруссией Наполеон решил отдохнуть: охота на кроликов. Заготовили ТЫСЯЧУ штук.",
             "image_prompt": "Napoleon in his green hunting uniform on horseback in a summer field, hunting party behind him"},
            {"text": "Кроликов накануне поймали и держали в клетках. Но когда их выпустили… они не разбежались.",
             "image_prompt": "hunters releasing hundreds of rabbits from wooden cages into a meadow, expectant faces"},
            {"text": "Они ПОБЕЖАЛИ К НАПОЛЕОНУ. Сотни кроликов прыгали прямо к императору.",
             "image_prompt": "massive wave of rabbits charging across a field toward Napoleon on horseback, chaos"},
            {"text": "Разгадка: кроликов купили у фермеров — ДОМАШНИХ. Они не боялись людей. Они думали, их несут КОРМИТЬ.",
             "image_prompt": "plump domestic rabbits swarming around riders' boots, peasants laughing in the distance"},
            {"text": "Кролики облепили императора, лезли на одежду. Пришлось отступать к карете.",
             "image_prompt": "Napoleon retreating to his carriage covered in rabbits, officers swatting them away, absurd scene"},
            {"text": "Император Франции, гроза Европы — отброшен кроликами.",
             "image_prompt": "carriage driving away from a field swarming with rabbits, Napoleon looking back furious"},
            {"text": "Историки долго считали эту историю шуткой. Но она записана в мемуарах его генерала Бертьена.",
             "image_prompt": "old memoir book with quill and inkwell on a writing desk, candlelight, illustration of rabbits"},
            {"text": "Иногда история смешнее любого мультика. Подпишись.",
             "image_prompt": "one rabbit sitting proudly on a battlefield cannon, smoke clearing, comic vintage mood"},
        ],
    },
    {
        "era": "Средневековье",
        "title": "СУД НАД МЁРТВЫМ ПАПОЙ: ТРУП ПОСАДИЛИ НА ТРОН И ПРИГОВОРИЛИ ⚖️",
        "description": "897 год, Рим. Папа Стефан VI выкопал труп своего предшественника, чтобы судить его. Самый безумный суд в истории.",
        "scenes": [
            {"text": "Январь 897 года, Рим. Папа Стефан VI приказал выкопать труп своего предшественника — папы Формоза.",
             "image_prompt": "crypt beneath an old basilica, workers lifting a coffin by torchlight, ominous shadows"},
            {"text": "Мёртвого папу ОДЕЛИ в папские одежды и посадили на трон. Судить.",
             "image_prompt": "decomposed body in papal robes seated on an ornate throne in a candlelit hall, horrified clerics"},
            {"text": "За трупом стоял юный дьякон. Он склонялся к гробу и отвечал за покойного: «Да, виновен».",
             "image_prompt": "young deacon leaning toward the throne whispering answers, judges in vestments staring"},
            {"text": "Формоза был признан виновным. Три пальца, которыми он благословлял, отрубили.",
             "image_prompt": "dramatic close-up of a papal hand with severed fingers, dark courtroom, candle flames"},
            {"text": "Труп бросили в Тибр. Позже его тайно выловил монах.",
             "image_prompt": "river Tiber at night, body in white robes floating past Rome's banks, a monk with a boat hook"},
            {"text": "Рим взорвался: суд над мёртвым — кощунство. Через несколько месяцев Стефана VI свергли.",
             "image_prompt": "angry Roman crowd with torches storming a palace gate, guards overwhelmed, night"},
            {"text": "Стефана арестовали и задушили в тюрьме. Церковный собор отменил все приговоры того суда.",
             "image_prompt": "dark prison cell with a fallen crown and broken chains, council of bishops in the background"},
            {"text": "Самый безумный суд в истории человечества. Подпишись.",
             "image_prompt": "empty papal throne in a vast dark basilica, single candle burning, dust in the light"},
        ],
    },
    {
        "era": "Загадки истории",
        "title": "КЛЕОПАТРА ЖИЛА БЛИЖЕ К IPHONE, ЧЕМ К ПИРАМИДЕ… ВРЕМЯ — ЛОЖЬ 🤯",
        "description": "Факты, которые ломают чувство времени: пирамиды, мамонты, Оксфорд и первый полёт — всё перепутано местами.",
        "scenes": [
            {"text": "Клеопатра жила ближе к запуску айфона, чем к строительству пирамиды Хеопса. Пирамида — за 2560 лет до нашей эры. Клеопатра — за 30. Айфон — 2007 год.",
             "image_prompt": "Cleopatra's silhouette between a pyramid on one side and a glowing smartphone on the other, timeline effect"},
            {"text": "Оксфордский университет СТАРШЕ империи ацтеков. В Оксфорде учились с 1096 года. Столицу ацтеков основали только в 1325.",
             "image_prompt": "gothic Oxford college building on one side, Aztec temple city on the other, split scene"},
            {"text": "Мамонты ещё бродили по Земле, КОГДА СТРОИЛИ ПИРАМИДЫ. Последняя популяция дожила до 2000 года до нашей эры.",
             "image_prompt": "woolly mammoth herd in the distance behind Egyptian workers dragging a stone block, mixed era scene"},
            {"text": "Между стегозавром и тираннозавром времени БОЛЬШЕ, чем между тираннозавром и тобой. Стегозавр — 150 миллионов лет назад. Тираннозавр — 68.",
             "image_prompt": "stegosaurus and tyrannosaurus separated by a vast glowing chasm of time, human silhouette at the edge"},
            {"text": "Для Клеопатры пирамиды были такой же древностью, как Клеопатра для нас.",
             "image_prompt": "Cleopatra gazing at weathered ancient pyramids in a golden haze, contemplative mood"},
            {"text": "В 1903 году братья Райт совершили первый полёт — 36 метров. Через 66 лет человек уже ХОДИЛ ПО ЛУНЕ.",
             "image_prompt": "fragile first airplane over dunes transitioning to an astronaut on the Moon, timeline blend"},
            {"text": "Бабушка нынешнего школьника могла в детстве увидеть первый самолёт — а в старости лунную высадку в прямом эфире.",
             "image_prompt": "elderly woman watching a Moon landing on an old television by a window, photo of a biplane on the wall"},
            {"text": "История ближе, чем кажется. Подпишись.",
             "image_prompt": "long winding road through historical eras from pyramids to rockets, tiny human figure walking"},
        ],
    },
]


EXTRA_SCRIPTS = [
    {
        "era": "Новое время",
        "title": "ЛОНДОН ВОНЯЛ ТАК, ЧТО ПАРЛАМЕНТ СБЕЖАЛ… И ПОСТРОИЛ КАНАЛИЗАЦИЮ 🤢",
        "description": "Реальная история 1858 года: «Великий смрад». Температура 30+ градусов, Темза — открытая канализация.",
        "scenes": [
            {"text": "Лето 1858 года, Лондон. Жара под тридцать. И Темза пахнет так, что город стоит на коленях.",
             "image_prompt": "Victorian London bridge over the Thames in summer haze, crowds covering faces with handkerchiefs"},
            {"text": "Дело в том, что канализации в городе НЕ БЫЛО. Сотни тысяч туалетов сливались прямо в реку.",
             "image_prompt": "cross-section of Victorian houses with pipes draining straight into a murky river"},
            {"text": "В жару река превратилась в чёрную вонючую жижу. Смерть от болезней в трущобах — массовая.",
             "image_prompt": "dark green-black river water, industrial barges, sickly poor families at the embankment"},
            {"text": "Запах дошёл до Парламента. Заседания сорвались: депутаты завешивали окна пропитанными хлором шторами.",
             "image_prompt": "grand parliament chamber with MPs holding handkerchiefs to faces, curtains soaked in disinfectant"},
            {"text": "Газеты писали: ещё неделя такой жары — и классы бегут из города. А потом пришла идея.",
             "image_prompt": "Victorian newspaper office with bold headlines, editors in panic"},
            {"text": "Построить канализацию. Настоящую. Инженер Джозеф Базалгетт спроектировал 1300 километров туннелей.",
             "image_prompt": "engineers with blueprints and brick tunnels under construction, Victorian machinery"},
            {"text": "Строили шесть лет. С тех пор холера в Лондоне практически исчезла.",
             "image_prompt": "finished brick sewer tunnels stretching into the distance, proud workers with lanterns"},
            {"text": "Смрад убил никого — но спас миллионы. Подпишись.",
             "image_prompt": "clean Thames at sunset with modern London skyline, vintage map overlay"},
        ],
    },
    {
        "era": "Средневековье",
        "title": "ГОРОДА ВОЕВАЛИ 12 ЛЕТ… ИЗ-ЗА ДЕРЕВЯННОГО ВЕДРА 🪣",
        "description": "Реальная история 1325 года: война из-за ведра между Моденой и Болоньей. Тысячи погибших.",
        "scenes": [
            {"text": "1325 год, Италия. Два города — Модена и Болонья — ненавидели друг друга как никто.",
             "image_prompt": "two medieval Italian walled cities facing each other across plains, banners of different colors"},
            {"text": "И вот группа моденцев пробралась в Болонью… и украла из колодца ДЕРЕВЯННОЕ ВЕДРО.",
             "image_prompt": "medieval soldiers sneaking away at night with a large wooden bucket from a stone well"},
            {"text": "Зачем? Просто унизить врага. Символ победы. Болонья взбесилась.",
             "image_prompt": "angry medieval town council pointing at an empty well, furious citizens in the square"},
            {"text": "Болонья выставила армию: 32 тысячи человек. У Модены было в три раза меньше.",
             "image_prompt": "huge medieval army marching with banners versus a small defenders formation"},
            {"text": "Состоялось сражение при Заполино. Болонья ПОТЕРПЕЛА разгромное поражение: тысячи убитых и пленных.",
             "image_prompt": "chaotic medieval battle with routed army fleeing, captured soldiers, dust and banners fallen"},
            {"text": "Модена оставила себе трофей. То самое ведро. Оно у них ДО СИХ ПОР.",
             "image_prompt": "ancient wooden oak bucket displayed in a museum glass case under warm light"},
            {"text": "Война тянулась двенадцать лет. Оценки погибших — до двух тысяч только в главном сражении.",
             "image_prompt": "burnt farmland between two cities, smoke columns, exhausted soldiers"},
            {"text": "Из-за ведра. Настоящее деревянное ведро. Подпишись.",
             "image_prompt": "close-up of the weathered oak bucket in the museum, dramatic spotlight"},
        ],
    },
    {
        "era": "Новое время",
        "title": "ЭЙФЕЛЕВУ БАШНЮ ХОТЕЛИ СНЕСТИ… А ОНА ВЫРОСЛА НА 15 МЕТРОВ 🗼",
        "description": "Реальная история: башню собирались разобрать через 20 лет. Сегодня она на 15 метров выше, чем при открытии.",
        "scenes": [
            {"text": "1889 год. Эйфелеву башню открыли ко Всемирной выставке. И половина Парижа была ПРОТИВ.",
             "image_prompt": "1889 Paris World's Fair with the new iron tower, elegant crowds, mixed reactions"},
            {"text": "Триста деятелей культуры подписали протест: «бесполезная и чудовищная» башня-монстр.",
             "image_prompt": "Victorian artists and writers signing an angry petition in a candlelit salon"},
            {"text": "Договор аренды был на 20 лет. Потом башню планировали РАЗОБРАТЬ.",
             "image_prompt": "blueprint of the tower stamped with a date, workers with wrenches waiting nearby"},
            {"text": "Башню спасла… радиосвязь. Она оказалась идеальной антенной для военных и телеграфа.",
             "image_prompt": "early radio operators with spark transmitters on the tower's top platform, wires everywhere"},
            {"text": "В 1914 году её передатчики глушить немецкую радиосвязь. Башня воевала.",
             "image_prompt": "World War I radio jamming station on the tower, operators with headphones, maps"},
            {"text": "А теперь факт: летом башня ВЫРАСТАЕТ на 15 сантиметров. Металл расширяется на жаре.",
             "image_prompt": "the Eiffel Tower in blazing summer sun with subtle heat shimmer, measurement arrows"},
            {"text": "И отклоняется от солнца: верхушка уходит в тень на 18 сантиметров.",
             "image_prompt": "the tower leaning slightly away from the sun, exaggerated diagram style"},
            {"text": "«Чудовище» стало символом Франции. Подпишись.",
             "image_prompt": "the Eiffel Tower glowing at night over Paris, celebratory lights"},
        ],
    },
    {
        "era": "Новое время",
        "title": "ПЕРВЫЙ БАГ В ИСТОРИИ КОМПЬЮТЕРОВ… БЫЛ НАСТОЯЩИМ ЖУКОМ 🦋",
        "description": "9 сентября 1947 года инженеры Гарварда нашли мотылька внутри компьютера и вклеили его в журнал.",
        "scenes": [
            {"text": "1947 год. Компьютер Марк II размером с комнату вдруг начинает выдавать ошибки.",
             "image_prompt": "room-sized 1940s computer with relays and panels, engineers scratching heads"},
            {"text": "Грейс Хоппер и её команда проверяют реле — и находят причину.",
             "image_prompt": "female engineer in 1940s attire inspecting relay panels with a flashlight"},
            {"text": "Внутри реле сидел НАСТОЯЩИЙ МОТЫЛЁК. Он замыкал контакты.",
             "image_prompt": "macro view of a moth trapped between relay contacts, dramatic lighting"},
            {"text": "Мотылька достали и вклеили в журнал с припиской: «первый найденный настоящий баг».",
             "image_prompt": "logbook page with a taped moth and handwritten caption, vintage desk"},
            {"text": "Шутка стала термином. С тех пор ошибку в программе называют БАГОМ.",
             "image_prompt": "vintage typewriter and modern laptop side by side with the word bug glowing"},
            {"text": "Кстати, слово «баг» использовал ещё Эдисон — за 70 лет до этого.",
             "image_prompt": "Thomas Edison at his workbench with notebooks, lightbulbs around"},
            {"text": "А «отладку» — дебаггингом. Всё из-за одного мотылька. Подпишись.",
             "image_prompt": "the famous moth page in a museum display case, soft spotlight"},
        ],
    },
    {
        "era": "Новое время",
        "title": "В 1816 ГОДУ НЕ БЫЛО ЛЕТА… ВО ВСЁМ МИРЕ ❄️",
        "description": "Реальная история: год без лета. Снег в июле, голод по всей планете. Виноват вулкан в Индонезии.",
        "scenes": [
            {"text": "Апрель 1815 года. Вулкан Тамбора в Индонезии взрывается с силой в 800 раз мощнее Хиросимы.",
             "image_prompt": "colossal volcanic eruption at night, lightning inside the ash column, ships fleeing"},
            {"text": "Миллионы тонн пепла улетели в стратосферу и накрыли планету как одеялом.",
             "image_prompt": "vast ash cloud spreading around the globe seen from high altitude, sun dimmed"},
            {"text": "И в 1816 году лето НЕ ПРИШЛО. В июне в Новой Англии выпал снег.",
             "image_prompt": "colonial village in June covered in snow, frozen crops, people in heavy coats"},
            {"text": "В июле и августе — лёд на реках. Фермеры теряли урожай по два раза за сезон.",
             "image_prompt": "farmer standing in a ruined frozen field in summer, dead corn stalks"},
            {"text": "Начался голод. Цены на зерно взлетели в разы. Беженцы двигались целыми деревнями.",
             "image_prompt": "long line of farmers with carts leaving a village, empty markets, grey sky"},
            {"text": "Побочный эффект: из-за дождей в Швейцарии заперся 18-летний Мэри Шелли. Она написала «Франкенштейна».",
             "image_prompt": "young woman writing by candlelight in a storm-lashed villa on Lake Geneva"},
            {"text": "Ещё побочный: изобрели велосипед. Лошади подорожали — нужен был транспорт без овса.",
             "image_prompt": "early wooden draisine bicycle prototype on a muddy road, inventor pushing it"},
            {"text": "Один вулкан изменил литературу, транспорт и судьбы миллионов. Подпишись.",
             "image_prompt": "distant smoking volcano over a peaceful sunset landscape with a road and bicycle tracks"},
        ],
    },
    {
        "era": "Новое время",
        "title": "СМОГ УБИВАЛ ЛОНДОН ЗА 5 ДНЕЙ… И ЭТО БЫЛО В 1952 ГОДУ 🌫️",
        "description": "Реальная история: Великий смог. Тысячи погибших в самом сердце XX века — и это изменило экологию навсегда.",
        "scenes": [
            {"text": "Декабрь 1952 года, Лондон. Над городом повисла антициклонная тишь. И весь дым от угля остался ВНУТРИ.",
             "image_prompt": "1950s London street swallowed by thick yellow-grey smog, buses barely visible"},
            {"text": "Видимость упала до метра. Автобусы шли за кондуктором с фонарём.",
             "image_prompt": "conductor walking ahead of a double-decker bus with a lantern in dense smog"},
            {"text": "Смог пробирался даже в дома. Концерты отменяли: зрители не видели сцену.",
             "image_prompt": "theatre hall with audience barely seeing the stage through haze, empty seats"},
            {"text": "За пять дней погибли около ЧЕТЫРЁХ ТЫСЯЧ человек. Позже счёт пошёл на десятки тысяч.",
             "image_prompt": "hospital corridors crowded with patients on beds, nurses with masks, somber tones"},
            {"text": "Врачи сначала не верили: жертв больше, чем от эпидемии. Причина — копоть в лёгких.",
             "image_prompt": "doctor examining X-ray photographs under a light board, shocked expression"},
            {"text": "Через четыре года приняли Закон о чистом воздухе. Уголь в городах запретили.",
             "image_prompt": "parliament voting with hands raised, clean chimneys and electric heaters in homes"},
            {"text": "Лондонский смог стал поводом для первых экологических законов Европы.",
             "image_prompt": "modern clean London skyline at dawn, archival smog photo ghosted in the corner"},
            {"text": "Один месяц зимы изменил законы всего мира. Подпишись.",
             "image_prompt": "sunrise clearing over the Thames, city waking up, hopeful mood"},
        ],
    },
]


SCRIPTS.extend(EXTRA_SCRIPTS)

ERAS = sorted({s["era"] for s in SCRIPTS})


def generate_script(era: str | None = None) -> dict:
    pool = [s for s in SCRIPTS if s["era"] == era] if era else SCRIPTS
    slot = os.environ.get("SHORTS_SLOT")
    if slot is not None and not era:
        day = int(time.strftime("%Y%m%d"))
        # Шаг 7 (взаимно простой с 15) — соседние дни не пересекаются по сюжетам,
        # даже со слотами 5-6: полный цикл банка сценариев — 15 дней.
        script = copy.deepcopy(SCRIPTS[(day * 7 + int(slot)) % len(SCRIPTS)])
    else:
        script = copy.deepcopy(random.choice(pool or SCRIPTS))
    script.setdefault("tags", [
        "#shorts", "#shortsfeed", "#shortsyoutube", "#рекомендации",
        "#история", "#факты", "#историческиефакты", "#интересныефакты",
        "#знания", "#интересное", "#топ", "#фактыистории",
        "#наука", "#образование", "#подпишись",
        script["era"].lower(),
    ])
    # Видимые хэштеги — в описании (первые 3 YouTube показывает над заголовком).
    # Не больше 15, иначе YouTube игнорирует их все.
    hashtags = [
        "#shorts", "#факты", "#история", "#рекомендации", "#интересное",
        "#историческиефакты", "#знания", "#интересныефакты", "#топ",
        "#shortsfeed", "#фактыистории", "#подпишись",
    ]
    desc = script.get("description", "").strip()
    if "#shorts" not in desc:
        desc = (desc + "\n\n" + " ".join(hashtags)).strip()
        script["description"] = desc
    return script


if __name__ == "__main__":
    s = generate_script()
    print(s["title"])
    print(len(s["scenes"]), "сцен")

# внеочередной выпуск по запросу
