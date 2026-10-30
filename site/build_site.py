# -*- coding: utf-8 -*-
"""Build static HTML from content.py and credits.json."""

import json
from html import escape
from pathlib import Path
from urllib.parse import quote

import content

ROOT = Path(__file__).resolve().parent
CREDITS_PATH = ROOT / "credits.json"


def esc(value):
    return escape("" if value is None else str(value), quote=True)


def paras(items, cls):
    return "\n".join(f'<p class="{cls}">{esc(item)}</p>' for item in items)


def both(ru, zh, tag="p", cls=""):
    extra = f" {cls}" if cls else ""
    return (
        f'<{tag} class="ru{extra}">{esc(ru)}</{tag}>\n'
        f'<{tag} class="zh{extra}">{esc(zh)}</{tag}>'
    )


def bi_span(ru, zh):
    return f'<span class="ru">{esc(ru)}</span><span class="zh">{esc(zh)}</span>'


def load_credits():
    if not CREDITS_PATH.exists():
        return {"photos": {}, "coords": {}}
    return json.loads(CREDITS_PATH.read_text(encoding="utf-8"))


def coord_for(key, credits):
    row = (credits.get("coords") or {}).get(key) or {}
    lat, lon = row.get("lat"), row.get("lon")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        if 30.8 <= lat <= 31.6 and 121.0 <= lon <= 122.0:
            return lat, lon
    return content.FALLBACK_COORDS[key]


def place_by_file(filename):
    for place in content.PLACES:
        if place["file"] == filename:
            return place
    return None


def place_by_id(place_id):
    for place in content.PLACES:
        if place["id"] == place_id:
            return place
    return None


def facts_for(filename):
    return [fact for fact in content.FACTS if filename in fact["pages"]]


def page_url(filename):
    if filename == "index.html":
        return f"https://{content.DOMAIN}/"
    return f"https://{content.DOMAIN}/{filename}"


def json_ld(data):
    raw = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return f'<script type="application/ld+json">{raw}</script>'


def figure(key, credits):
    note = content.PHOTO_NOTES.get(key, {})
    alt_ru, alt_zh = content.PHOTO_ALT.get(key, ("", ""))
    kind, badge_ru, badge_zh = content.PHOTO_WHEN.get(key, ("today", "", ""))
    photo = (credits.get("photos") or {}).get(key) or {}
    src = photo.get("file") or f"img/{key}.jpg"
    path = ROOT / src
    if key == "vera":
        src = "img/vera.jpg"
        path = ROOT / src
    if not path.exists():
        return both(
            "Фото для этой страницы ещё не положили в папку.",
            "这一页的照片还没放进文件夹。",
        )
    credit_ru = ""
    credit_zh = ""
    if key != "vera":
        artist = esc(photo.get("artist") or "автор на странице файла")
        license_name = esc(photo.get("license") or "см. файл")
        page = photo.get("page") or ""
        link = f' <a href="{esc(page)}">файл</a>' if page else ""
        credit_ru = f"{artist}. {license_name}.{link}"
        credit_zh = f"{artist}。{license_name}。{link}"
    extra_ru = note.get("ru", "")
    extra_zh = note.get("zh", "")
    portrait = "portrait" if key == "vera" else ""
    badge = ""
    if badge_ru:
        badge = f'<span class="badge {esc(kind)}">{bi_span(badge_ru, badge_zh)}</span>'
    figure_cls = f' class="{portrait}"' if portrait else ""
    return f"""<figure{figure_cls}>
  {badge}
  <img src="{esc(src)}" alt="{esc(alt_ru)}" data-alt-ru="{esc(alt_ru)}" data-alt-zh="{esc(alt_zh)}">
  <figcaption>
    <span class="ru">{esc(extra_ru)} {credit_ru}</span>
    <span class="zh">{esc(extra_zh)} {credit_zh}</span>
  </figcaption>
</figure>"""


def nav(current):
    links = []
    for href, ru, zh in content.NAV:
        current_attr = ' aria-current="page"' if href == current else ""
        links.append(
            f'<a href="{href}"{current_attr}>{bi_span(ru, zh)}</a>'
        )
    return "\n".join(links)


def filter_buttons_attr(attr, items):
    buttons = []
    for key, ru, zh in items:
        pressed = "true" if key == "all" else "false"
        buttons.append(
            f'<button type="button" {attr}="{esc(key)}" aria-pressed="{pressed}">{bi_span(ru, zh)}</button>'
        )
    return '<div class="filters">\n' + "\n".join(buttons) + "\n</div>"


def breadcrumbs_ld(items):
    element = []
    for index, row in enumerate(items, start=1):
        if len(row) == 3:
            href, name, _zh = row
            element.append({
                "@type": "ListItem",
                "position": index,
                "name": name,
                "item": page_url(href),
            })
        else:
            element.append({
                "@type": "ListItem",
                "position": index,
                "name": row[0],
            })
    return json_ld({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": element,
    })


def breadcrumbs_html(items):
    parts = ['<nav class="crumbs" aria-label="Breadcrumb">']
    for index, row in enumerate(items):
        if len(row) == 3:
            href, ru, zh = row
            if index == len(items) - 1:
                parts.append(f'<span aria-current="page">{bi_span(ru, zh)}</span>')
            else:
                parts.append(f'<a href="{esc(href)}">{bi_span(ru, zh)}</a>')
        else:
            parts.append(f'<span aria-current="page">{bi_span(row[0], row[1])}</span>')
        if index < len(items) - 1:
            parts.append('<span class="crumb-sep" aria-hidden="true">→</span>')
    parts.append("</nav>")
    return "".join(parts)


def map_points(credits):
    points = []
    for pin in content.PINS:
        lat, lon = coord_for(pin["key"], credits)
        themes = pin.get("themes") or []
        points.append({
            "lat": lat,
            "lon": lon,
            "href": pin["href"],
            "title_ru": pin["title_ru"],
            "title_zh": pin["title_zh"],
            "addr_ru": pin["addr_ru"],
            "addr_zh": pin["addr_zh"],
            "themes": themes,
            "period": pin.get("period") or "emigration",
        })
    return points


def dock(current):
    links = []
    for href, ru, zh in content.DOCK:
        current_attr = ' aria-current="page"' if href == current else ""
        links.append(f'<a href="{href}"{current_attr}>{bi_span(ru, zh)}</a>')
    return "\n".join(links)


def descriptions(filename, title_ru, title_zh):
    pair = content.DESCRIPTIONS.get(filename)
    if pair:
        return pair
    return title_ru, title_zh


def og_image(filename, credits, photos=None):
    for key in photos or []:
        photo = (credits.get("photos") or {}).get(key) or {}
        src = "img/vera.jpg" if key == "vera" else (photo.get("file") or f"img/{key}.jpg")
        if (ROOT / src).exists():
            return f"https://{content.DOMAIN}/{src}"
    if filename == "ya.html" and (ROOT / "img" / "vera.jpg").exists():
        return f"https://{content.DOMAIN}/img/vera.jpg"
    return f"https://{content.DOMAIN}/img/avatar.jpg"


def page_shell(filename, title_ru, title_zh, body, wide=False, leaflet=False, scripts="", ld="", image=None):
    desc_ru, desc_zh = descriptions(filename, title_ru, title_zh)
    title_full_ru = f"{title_ru} — {content.SITE_NAME_RU}"
    title_full_zh = f"{title_zh} — {content.SITE_NAME_ZH}"
    canonical = page_url(filename)
    leaflet_css = '\n  <link rel="stylesheet" href="vendor/leaflet/leaflet.css">' if leaflet else ""
    wide_cls = " wide" if wide else ""
    mark = ""
    if (ROOT / "img" / "avatar.jpg").exists():
        mark = '<img class="mark" src="img/avatar.jpg" alt="" width="48" height="48">'
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title_full_ru)}</title>
  <meta name="description" content="{esc(desc_ru)}">
  <meta name="title-ru" content="{esc(title_full_ru)}">
  <meta name="title-zh" content="{esc(title_full_zh)}">
  <meta name="desc-ru" content="{esc(desc_ru)}">
  <meta name="desc-zh" content="{esc(desc_zh)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="ru_RU">
  <meta property="og:locale:alternate" content="zh_CN">
  <meta property="og:site_name" content="{esc(content.SITE_NAME_RU)}">
  <meta property="og:title" content="{esc(title_full_ru)}">
  <meta property="og:description" content="{esc(desc_ru)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{esc(image or ('https://' + content.DOMAIN + '/img/avatar.jpg'))}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="img/avatar.jpg">
  <link rel="stylesheet" href="css/style.css">{leaflet_css}
  {ld}
</head>
<body data-lang="ru">
  <a class="skip ru" href="#content">К тексту</a>
  <a class="skip zh" href="#content">到正文</a>
  <header class="top">
    <div class="top-row">
      <a class="brand" href="index.html">
        {mark}
        <span>
          <strong>{bi_span(content.SITE_NAME_RU, content.SITE_NAME_ZH)}</strong>
          <small class="ru">Вера Курносенко, Шанхай</small>
          <small class="zh">薇拉·库尔诺先科，上海</small>
        </span>
      </a>
      <div class="tools">
        <p class="head-links">
          <a href="{esc(content.VK_COMMUNITY)}">ВК</a>
          <a href="{esc(content.TG_CHANNEL)}">Telegram</a>
        </p>
        <div class="langs">
          <button type="button" data-set-lang="ru">Русский</button>
          <button type="button" data-set-lang="zh">中文</button>
        </div>
      </div>
    </div>
    <button type="button" class="menu-toggle" data-menu-toggle aria-expanded="false" aria-controls="site-nav">{bi_span("Меню", "菜单")}</button>
    <nav id="site-nav" class="site-nav" aria-label="Разделы">{nav(filename)}</nav>
  </header>
  <main id="content" class="{wide_cls.strip()}">
{body}
  </main>
  <footer>
    <div>
      <p class="foot-links">
        <a href="{esc(content.VK_COMMUNITY)}">{bi_span("ВКонтакте", "VK")}</a>
        <a href="{esc(content.TG_CHANNEL)}">Telegram</a>
        <a href="karta.html">{bi_span("Карта", "地图")}</a>
        <a href="proekt.html">{bi_span("Проект", "项目")}</a>
        <a href="istochniki.html">{bi_span("Откуда", "出处")}</a>
      </p>
      <p class="follow">{bi_span(content.HOME_FOLLOW[0], content.HOME_FOLLOW[1])}</p>
      <span class="ru">Карта для класса, не путеводитель. Сайт: <a href="https://{esc(content.DOMAIN)}">{esc(content.DOMAIN)}</a>. Чужие фото подписаны. Домашний адрес и телефон здесь не публикуются.</span>
      <span class="zh">这是给班级的地图，不是旅游指南。网站：<a href="https://{esc(content.DOMAIN)}">{esc(content.DOMAIN)}</a>。别人的照片都写了拍摄者。家里的地址和电话不放在这里。</span>
    </div>
  </footer>
  <nav class="dock" aria-label="Короткие разделы">{dock(filename)}</nav>
  <script src="js/lang.js"></script>
  <script src="js/nav.js"></script>
  {scripts}
</body>
</html>
"""


def write_page(filename, title_ru, title_zh, body, credits=None, photos=None, **kwargs):
    kwargs.setdefault("image", og_image(filename, credits or {}, photos))
    html = page_shell(filename, title_ru, title_zh, body, **kwargs)
    (ROOT / filename).write_text(html, encoding="utf-8")
    print(filename)


def cards_html():
    blocks = []
    for card in content.CARDS:
        meta_ru = " · ".join([card.get("period_ru", ""), card.get("kind_ru", ""), card.get("where_ru", "")]).strip(" ·")
        meta_zh = " · ".join([card.get("period_zh", ""), card.get("kind_zh", ""), card.get("where_zh", "")]).strip(" ·")
        blocks.append(
            f"""<a class="card card-bilingual" href="{card['href']}">
  <p class="meta">{bi_span(meta_ru, meta_zh)}</p>
  <p class="card-title-zh">{esc(card['title_zh'])}</p>
  <p class="card-title-ru">{esc(card['title_ru'])}</p>
  <p class="card-text ru">{esc(card['text_ru'])}</p>
  <p class="card-text zh">{esc(card['text_zh'])}</p>
  <span class="card-cta">{bi_span("Смотреть историю", "阅读故事")}</span>
</a>"""
        )
    return '<div class="cards">\n' + "\n".join(blocks) + "\n</div>"


def actions_html(compact=False):
    extra = ""
    if not compact:
        extra = '\n  <a class="ghost" href="urok.html"><span class="ru">Для урока</span><span class="zh">给课堂</span></a>'
    return f"""<div class="actions">
  <a class="primary" href="karta.html"><span class="ru">Открыть карту</span><span class="zh">打开地图</span></a>
  <a class="ghost" href="marshruty.html"><span class="ru">Начать маршрут</span><span class="zh">开始路线</span></a>{extra}
</div>"""


def value_grid():
    items = "\n".join(f"<li>{bi_span(ru, zh)}</li>" for ru, zh in content.HOME_VALUE)
    return f"""<section class="value-block">
  <h2>{bi_span("Почему этот проект важен", "为什么这个项目重要")}</h2>
  <ul class="value-list">{items}</ul>
</section>"""


def use_grid():
    items = "\n".join(f"<li>{bi_span(ru, zh)}</li>" for ru, zh in content.HOME_USE)
    return f"""<section class="value-block">
  <h2>{bi_span("Как проект используется", "项目怎么用")}</h2>
  <ul class="value-list">{items}</ul>
</section>"""


def author_section(page):
    return "\n".join([
        '<section class="author-block" id="author">',
        f'<h2>{bi_span("Почему я создала этот проект", "我为什么做这张地图")}</h2>',
        f'<blockquote class="hero-quote">{bi_span(page["quote_ru"], page["quote_zh"])}</blockquote>',
        '<div class="author-card">',
        f'<p><strong>{bi_span("Вера Курносенко", "薇拉·库尔诺先科")}</strong></p>',
        f'<p class="meta">{bi_span("Шанхай · школьный исследовательский проект · с 2023 года", "上海 · 学校研究项目 · 从2023年")}</p>',
        f'<p class="meta">{bi_span("Языки: русский и китайский", "语言：俄文和中文")}</p>',
        "</div>",
        both(page["who_ru"], page["who_zh"], "p", "who"),
        both(page["class_ru"], page["class_zh"]),
        paras(page.get("paras_ru") or [], "ru"),
        paras(page.get("paras_zh") or [], "zh"),
        f'<p><a href="ya.html">{bi_span("Подробнее об авторе", "更多关于作者")}</a> · '
        f'<a href="proekt.html">{bi_span("Страница для жюри", "给评委的项目页")}</a></p>',
        "</section>",
    ])


def mini_map_html(credits):
    data = escape(json.dumps(map_points(credits), ensure_ascii=False), quote=True)
    return f"""<section class="map-preview wide-inner" aria-labelledby="map-preview-title">
  <h2 id="map-preview-title">{bi_span("На карте Шанхая", "在上海地图上")}</h2>
  <p class="meta">{bi_span("Пять булавок — дома с тротуара. Остальные истории в каталоге «Места».", "五个钉子——从人行道看得见。别的故事在「地点」目录里。")}</p>
  <div class="map-wrap map-wrap--preview"><div id="map-home" data-points="{data}" role="region" aria-label="Превью карты"></div></div>
  <p class="map-legend">{bi_span("Красные маркеры — 1930–40-е и эмиграция. Синий — 1950-е.", "红钉：1930–40年代和侨民。蓝钉：1950年代。")}</p>
  <p class="map-preview-links"><a href="karta.html">{bi_span("Открыть полную карту", "打开完整地图")}</a> · <a href="mesta.html">{bi_span("Все места и фильтры", "全部地点和筛选")}</a> · <a href="marshruty.html">{bi_span("Проложить маршрут", "选一条路线")}</a></p>
</section>
<script src="vendor/leaflet/leaflet.js"></script>
<script src="js/map.js"></script>"""


def steps_html():
    items = "\n".join(f"<li>{bi_span(ru, zh)}</li>" for ru, zh in content.HOW)
    return f'<ol class="steps">\n{items}\n</ol>'


def stats_html():
    blocks = []
    for label_ru, label_zh, note_ru, note_zh in content.STATS:
        blocks.append(
            f"""<article class="stat">
  <b>{bi_span(label_ru, label_zh)}</b>
  <p>{bi_span(note_ru, note_zh)}</p>
</article>"""
        )
    return '<div class="stats">\n' + "\n".join(blocks) + "\n</div>"


def pubs_html():
    items = []
    for pub in content.PUBLICATIONS:
        items.append(
            f"""<li>
  <a href="{esc(pub['url'])}">{bi_span(pub['title_ru'], pub['title_zh'])}</a>
  <div class="ru">{esc(pub['note_ru'])}</div>
  <div class="zh">{esc(pub['note_zh'])}</div>
</li>"""
        )
    return '<ul class="pubs">\n' + "\n".join(items) + "\n</ul>"


def home_html(page, credits):
    parts = [
        '<section class="hero">',
        f"<h1>{bi_span(page['h1_ru'], page['h1_zh'])}</h1>",
        both(page["deck_ru"], page["deck_zh"], "p", "deck"),
        both(page["pitch_ru"], page["pitch_zh"], "p", "pitch"),
        f'<p class="audience">{bi_span(page["audience_ru"], page["audience_zh"])}</p>',
        actions_html(compact=True),
        "</section>",
    ]
    if page.get("mini_map"):
        parts.append(mini_map_html(credits))
    parts.extend([
        value_grid(),
        '<section class="routes-teaser">',
        f'<h2>{bi_span("Четыре истории на главной", "首页四个故事")}</h2>',
        f'<p class="meta">{bi_span("Ещё Старк, Иоанн и другие темы — в каталоге «Места» с фильтрами.", "斯塔克、圣伊望等题目——在「地点」目录里，可以筛选。")}</p>',
        cards_html(),
        f'<p><a href="mesta.html">{bi_span("Все места и поиск", "全部地点和搜索")}</a></p>',
        "</section>",
        use_grid(),
        author_section(page),
        '<div class="measure">',
        f'<h2>{bi_span("Как читать этот проект", "怎样读这个项目")}</h2>',
        steps_html(),
        "</div>",
        f'<h2>{bi_span("Проект в цифрах", "项目里的数字")}</h2>',
        stats_html(),
        '<div class="measure">',
        f'<h2>{bi_span("Следить за проектом", "关注项目")}</h2>',
        both(
            content.HOME_FOLLOW[0] + " " + content.VK_COMMUNITY,
            content.HOME_FOLLOW[1],
        ),
        "</div>",
        pubs_html(),
        '<div class="measure">',
        f'<h2>{bi_span("Источники и честность", "出处和诚实")}</h2>',
        paras(page.get("tail_ru") or [], "ru"),
        paras(page.get("tail_zh") or [], "zh"),
        f'<p><a href="istochniki.html">{bi_span("Откуда даты и чьи фото", "日期从哪儿来，照片是谁的")}</a></p>',
        "</div>",
    ])
    return "\n".join(parts)


def filter_buttons(attr):
    buttons = []
    for key, ru, zh in content.THEMES:
        pressed = "true" if key == "all" else "false"
        buttons.append(
            f'<button type="button" {attr}="{esc(key)}" aria-pressed="{pressed}">{bi_span(ru, zh)}</button>'
        )
    return '<div class="filters">\n' + "\n".join(buttons) + "\n</div>"


def map_html(credits):
    points = map_points(credits)
    items = []
    for pin in content.PINS:
        themes = pin.get("themes") or []
        items.append(
            f"""<li data-themes="{' '.join(themes)}">
  <a href="{pin['href']}">{bi_span(pin['title_ru'], pin['title_zh'])}</a>
  <div class="ru">{esc(pin['addr_ru'])}</div>
  <div class="zh">{esc(pin['addr_zh'])}</div>
</li>"""
        )
    for place in content.PLACES:
        if place.get("on_map"):
            continue
        items.append(
            f"""<li data-themes="{' '.join(place['themes'])}">
  <a href="{place['file']}">{bi_span(place['title_ru'], place['title_zh'])}</a>
  <div class="ru">{esc(place['where_ru'])}. Булавки нет.</div>
  <div class="zh">{esc(place['where_zh'])}。没有钉子。</div>
</li>"""
        )
    data = escape(json.dumps(points, ensure_ascii=False), quote=True)
    return f"""{filter_buttons("data-map-theme")}
<div class="view-toggle">
  <button type="button" data-view="map" aria-pressed="true">{bi_span("Карта", "地图")}</button>
  <button type="button" data-view="list" aria-pressed="false">{bi_span("Список", "名单")}</button>
</div>
<div class="map-layout is-map">
  <div class="map-wrap"><div id="map" data-points="{data}" role="region" aria-label="Карта мест"></div></div>
  <p id="map-empty" hidden>{bi_span("На карте для этой темы булавки нет. История может быть в списке ниже.", "这个题目在地图上没有钉子。故事可能在下面的名单里。")}</p>
  <ul class="places" data-map-list>
{''.join(items)}
  </ul>
</div>
<aside class="map-note">
  <p class="ru">1950 год на эту карту булавкой не ставится. Лётчики защищали небо города, отдельного памятника на тротуаре нет. Страница истории всё равно есть.</p>
  <p class="zh">1950年不在这张图上钉钉子。飞行员保护的是城市的天空，人行道上没有单独的纪念碑。故事页面还是有的。</p>
  <p><a href="nebo.html">{bi_span("Открыть 1950", "打开1950")}</a></p>
</aside>
<script src="vendor/leaflet/leaflet.js"></script>
<script src="js/map.js"></script>"""


def facts_html(items):
    if not items:
        return both(
            "Отдельной ссылки для этой страницы в списке сверки пока нет.",
            "核对名单里还没有这一页的单独链接。",
        )
    rows = []
    for fact in items:
        rows.append(
            f'<li><a href="{esc(fact["url"])}">{esc(fact["title"])}</a>. '
            f'{bi_span(fact["note"], fact.get("note_zh") or fact["note"])}</li>'
        )
    return '<ol class="facts">\n' + "\n".join(rows) + "\n</ol>"


def photo_list(credits):
    rows = []
    for key, note in content.PHOTO_NOTES.items():
        if key == "vera":
            rows.append(
                f'<li>{bi_span("Портрет Веры. " + note["ru"], "薇拉的照片。" + note["zh"])}</li>'
            )
            continue
        photo = (credits.get("photos") or {}).get(key) or {}
        if not photo:
            continue
        artist = photo.get("artist") or ""
        license_name = photo.get("license") or ""
        page = photo.get("page") or ""
        title = photo.get("title") or key
        kind, badge_ru, badge_zh = content.PHOTO_WHEN.get(key, ("today", "", ""))
        rows.append(
            f'<li>{esc(title)}. {esc(artist)}. {esc(license_name)}. '
            f'<a href="{esc(page)}">{bi_span("Викисклад", "维基共享")}</a>. '
            f'{bi_span(badge_ru + ". " + note["ru"], badge_zh + "。" + note["zh"])}</li>'
        )
    return '<ul class="facts">\n' + "\n".join(rows) + "\n</ul>"


def share_html(filename, title_ru):
    url = quote(page_url(filename), safe="")
    text = quote(title_ru, safe="")
    vk = f"https://vk.com/share.php?url={url}"
    tg = f"https://t.me/share/url?url={url}&text={text}"
    return f"""<p class="share">
  {bi_span("Поделиться страницей:", "把这一页发给别人：")}
  <a href="{esc(vk)}">ВК</a>
  <a href="{esc(tg)}">Telegram</a>
  {bi_span("Дневник проекта:", "项目日记：")}
  <a href="{esc(content.VK_COMMUNITY)}">{bi_span("сообщество", "社区")}</a>
  <a href="{esc(content.TG_CHANNEL)}">{bi_span("канал", "频道")}</a>
</p>"""


def place_extra(filename):
    place = place_by_file(filename)
    if not place:
        return ""
    route = next((item for item in content.ROUTES if item["id"] == place["route"]), None)
    related = []
    for href in place.get("related") or []:
        other = place_by_file(href)
        if other:
            related.append(f'<a href="{esc(href)}">{bi_span(other["title_ru"], other["title_zh"])}</a>')
    route_bit = ""
    if route:
        route_bit = f'<p><a href="{esc(route["file"])}">{bi_span("Учебный маршрут: " + route["title_ru"], "课堂路线：" + route["title_zh"])}</a></p>'
    related_bit = ""
    if related:
        related_bit = f'<p>{bi_span("Рядом по смыслу:", "意思上相邻的：")} {" ".join(related)}</p>'
    return "\n".join([
        f'<h2>{bi_span("Важно не перепутать", "别弄混")}</h2>',
        both(place["confuse_ru"], place["confuse_zh"]),
        f'<h2>{bi_span("Вопрос для школьника", "给同学的问题")}</h2>',
        both(place["ask_ru"], place["ask_zh"]),
        f'<h2>{bi_span("Что установлено точно", "已经核对过的")}</h2>',
        both(place["sure_ru"], place["sure_zh"]),
        f'<h2>{bi_span("Что пока требует проверки", "还要再核对的")}</h2>',
        both(place["open_ru"], place["open_zh"]),
        f'<h2>{bi_span("Источники этой страницы", "这一页的出处")}</h2>',
        facts_html(facts_for(filename)),
        route_bit,
        related_bit,
        share_html(filename, place["title_ru"]),
        f'<p class="updated">{bi_span(content.UPDATED_RU, content.UPDATED_ZH)}</p>',
    ])


def article_ld(filename, title_ru, desc_ru, credits):
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title_ru,
        "description": desc_ru,
        "inLanguage": ["ru", "zh"],
        "url": page_url(filename),
        "dateModified": "2026-10-30",
        "author": {"@type": "Person", "name": "Вера Курносенко"},
    }
    geos = []
    for pin in content.PINS:
        if pin["href"] != filename:
            continue
        lat, lon = coord_for(pin["key"], credits)
        geos.append({
            "@type": "Place",
            "name": pin["title_ru"],
            "address": pin["addr_ru"],
            "geo": {"@type": "GeoCoordinates", "latitude": lat, "longitude": lon},
        })
    if len(geos) == 1:
        data["about"] = geos[0]
    elif geos:
        data["about"] = geos
    return json_ld(data)


def read_tiers_html(page):
    ru = page.get("paras_ru") or []
    zh = page.get("paras_zh") or []
    if not ru:
        return ""
    chunks = [
        f'<h2>{bi_span("Прочитать за минуту", "一分钟读完")}</h2>',
        paras(ru[:1], "ru"),
        paras(zh[:1], "zh"),
    ]
    if len(ru) > 1:
        chunks.extend([
            f'<h2>{bi_span("Узнать подробнее", "了解更多")}</h2>',
            paras(ru[1:], "ru"),
            paras(zh[1:], "zh"),
        ])
    return "\n".join(chunks)


def place_spot_map(filename, credits):
    points = [p for p in map_points(credits) if p["href"] == filename]
    if not points:
        return "", False
    data = escape(json.dumps(points, ensure_ascii=False), quote=True)
    html = f"""<h2>{bi_span("На карте", "在地图上")}</h2>
<div class="map-wrap map-wrap--spot"><div id="map-spot" data-points="{data}" role="region"></div></div>
<p><a href="karta.html">{bi_span("Открыть полную карту", "打开完整地图")}</a></p>"""
    return html, True


def route_neighbors(filename):
    place = place_by_file(filename)
    if not place:
        return ""
    route = next((item for item in content.ROUTES if item["id"] == place.get("route")), None)
    if not route:
        return ""
    ids = route["stops"]
    if place["id"] not in ids:
        return ""
    idx = ids.index(place["id"])
    links = []
    if idx > 0:
        prev = place_by_id(ids[idx - 1])
        links.append(
            f'<a class="route-nei" href="{esc(prev["file"])}">{bi_span("← " + prev["title_ru"], "← " + prev["title_zh"])}</a>'
        )
    if idx < len(ids) - 1:
        nxt = place_by_id(ids[idx + 1])
        links.append(
            f'<a class="route-nei" href="{esc(nxt["file"])}">{bi_span(nxt["title_ru"] + " →", nxt["title_zh"] + " →")}</a>'
        )
    if not links:
        return ""
    return f'<nav class="route-neighbors">{bi_span("По маршруту:", "按路线：")} {" · ".join(links)}</nav>'


def render(page, credits):
    chunks = []
    extra_ld = ""
    spot_leaflet = False
    if page.get("kicker_ru"):
        chunks.append(both(page["kicker_ru"], page["kicker_zh"], "p", "kicker"))
    if page.get("home"):
        chunks.append(home_html(page, credits))
    else:
        place = place_by_file(page["file"])
        if place:
            chunks.append(breadcrumbs_html([
                ("index.html", "Главная", "首页"),
                ("mesta.html", "Места", "地点"),
                (page["h1_ru"], page["h1_zh"]),
            ]))
            extra_ld = breadcrumbs_ld([
                ("index.html", "Главная", "首页"),
                ("mesta.html", "Места", "地点"),
                (page["h1_ru"], page["h1_zh"]),
            ])
        chunks.append(f"<h1>{bi_span(page['h1_ru'], page['h1_zh'])}</h1>")
        if page.get("deck_ru"):
            chunks.append(both(page["deck_ru"], page["deck_zh"], "p", "deck"))
        if page.get("addr_ru"):
            chunks.append(both(page["addr_ru"], page["addr_zh"], "p", "addr"))
        for key in page.get("photos") or []:
            chunks.append(figure(key, credits))
        if place:
            chunks.append(read_tiers_html(page))
        else:
            chunks.append(paras(page.get("paras_ru") or [], "ru"))
            chunks.append(paras(page.get("paras_zh") or [], "zh"))
        if page.get("cards"):
            chunks.append(cards_html())
        if page.get("map"):
            chunks.append(map_html(credits))
        if place:
            spot_html, spot_leaflet = place_spot_map(page["file"], credits)
            if spot_html:
                chunks.append(spot_html)
        if page.get("tail_ru"):
            chunks.append(paras(page["tail_ru"], "ru"))
            chunks.append(paras(page["tail_zh"], "zh"))
        if page.get("check_ru"):
            chunks.append(f'<h2 id="proverka">{bi_span("Как я проверяю", "我怎么核对")}</h2>')
            chunks.append(paras(page["check_ru"], "ru"))
            chunks.append(paras(page["check_zh"], "zh"))
        if page.get("sources"):
            chunks.append(f'<h2>{bi_span("Страницы, с которых я сверяла даты", "我对过日期的页面")}</h2>')
            chunks.append(facts_html(content.FACTS))
            chunks.append(f'<h2>{bi_span("Фотографии", "照片")}</h2>')
            chunks.append(photo_list(credits))
        if place:
            chunks.append(route_neighbors(page["file"]))
        chunks.append(place_extra(page["file"]))
    desc_ru, _desc_zh = descriptions(page["file"], page["h1_ru"], page["h1_zh"])
    if page.get("home"):
        ld = json_ld({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": content.SITE_NAME_RU,
            "alternateName": content.SITE_NAME_ZH,
            "url": page_url("index.html"),
            "inLanguage": ["ru", "zh"],
            "description": desc_ru,
            "author": {"@type": "Person", "name": "Вера Курносенко"},
        })
    else:
        ld = article_ld(page["file"], page["h1_ru"], desc_ru, credits) + extra_ld
    wide = bool(page.get("map") or page.get("cards") or page.get("home"))
    leaflet = bool(page.get("map") or page.get("mini_map") or spot_leaflet)
    scripts = ""
    if spot_leaflet and not page.get("map") and not page.get("mini_map"):
        scripts = '<script src="vendor/leaflet/leaflet.js"></script>\n<script src="js/map.js"></script>'
    write_page(
        page["file"], page["h1_ru"], page["h1_zh"], "\n".join(chunks),
        credits=credits, photos=page.get("photos"),
        wide=wide, leaflet=leaflet, scripts=scripts, ld=ld,
    )


def route_page(route):
    stops = []
    facts = []
    seen = set()
    for index, place_id in enumerate(route["stops"], start=1):
        place = place_by_id(place_id)
        stops.append(
            f"""<li>
  <a href="{esc(place['file'])}">{bi_span(str(index) + ". " + place["title_ru"], str(index) + ". " + place["title_zh"])}</a>
  <div class="ru">{esc(place["where_ru"])}</div>
  <div class="zh">{esc(place["where_zh"])}</div>
  <p class="ru">{esc(place["hook_ru"])}</p>
  <p class="zh">{esc(place["hook_zh"])}</p>
</li>"""
        )
        for fact in facts_for(place["file"]):
            if fact["url"] not in seen:
                facts.append(fact)
                seen.add(fact["url"])
    body = "\n".join([
        f"<h1>{bi_span(route['title_ru'], route['title_zh'])}</h1>",
        both(route["question_ru"], route["question_zh"], "p", "deck"),
        '<ul class="sheet-meta">',
        f"<li>{bi_span('Возраст: ' + route['age_ru'], '年龄：' + route['age_zh'])}</li>",
        f"<li>{bi_span(route['level_ru'], route['level_zh'])}</li>",
        f"<li>{bi_span(route['walk_ru'], route['walk_zh'])}</li>",
        f"<li>{bi_span('Остановок в листе: ' + str(len(route['stops'])), '这张纸上的站数：' + str(len(route['stops'])))}</li>",
        "</ul>",
        f'<p class="note">{bi_span("Китайский текст этой страницы включается кнопкой «中文» наверху. Отдельного адреса я не делаю, чтобы два языка не разъехались.", "这一页的中文用上面的「中文」按钮打开。我不另做网址，免得两种语言各走各的。")}</p>',
        f'<h2>{bi_span("Остановки", "站点")}</h2>',
        '<ol class="stops">\n' + "\n".join(stops) + "\n</ol>",
        f'<h2>{bi_span("Вопрос до маршрута", "出发前的问题")}</h2>',
        both(route["before_ru"], route["before_zh"]),
        f'<h2>{bi_span("Задание на месте", "现场任务")}</h2>',
        both(route["there_ru"], route["there_zh"]),
        f'<h2>{bi_span("Вопрос после", "结束后的问题")}</h2>',
        both(route["after_ru"], route["after_zh"]),
        f'<h2>{bi_span("Источники", "出处")}</h2>',
        facts_html(facts),
        both(
            "Учителю: те же ссылки, что и мне. Отдельной методички нет. Если печатать, на листе останутся вопросы и адреса страниц.",
            "给老师：链接和我用的是同一批。没有单独的教案。打印出来会留下问题和页面地址。",
        ),
        f'<p class="noprint"><button type="button" data-print>{bi_span("Распечатать маршрут", "打印路线")}</button></p>',
        f'<p><a href="marshruty.html">{bi_span("Все маршруты", "全部路线")}</a> · <a href="urok.html">{bi_span("Лист для урока", "课堂纸")}</a></p>',
        f'<p class="updated">{bi_span(content.UPDATED_RU, content.UPDATED_ZH)}</p>',
    ])
    desc_ru, _desc_zh = descriptions(route["file"], route["title_ru"], route["title_zh"])
    ld = json_ld({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": route["title_ru"],
        "description": desc_ru,
        "inLanguage": ["ru", "zh"],
        "url": page_url(route["file"]),
        "dateModified": "2026-10-30",
        "author": {"@type": "Person", "name": "Вера Курносенко"},
    })
    first = place_by_id(route["stops"][0])
    page = next((item for item in content.PAGES if item["file"] == first["file"]), {})
    write_page(route["file"], route["title_ru"], route["title_zh"], body, credits=load_credits(), photos=page.get("photos"), ld=ld)


def routes_index():
    cards = []
    for route in content.ROUTES:
        cards.append(
            f"""<a class="card" href="{esc(route['file'])}">
  <h2>{bi_span(route['title_ru'], route['title_zh'])}</h2>
  <p class="meta">{bi_span(route['age_ru'] + " · остановок: " + str(len(route['stops'])), route['age_zh'] + " · 站数：" + str(len(route['stops'])))}</p>
  <p class="ru">{esc(route['question_ru'])}</p>
  <p class="zh">{esc(route['question_zh'])}</p>
</a>"""
        )
    body = "\n".join([
        f"<h1>{bi_span('Маршруты', '路线')}</h1>",
        both(
            "Пять листов из историй, которые уже написаны. Это не отчёт о пройденных километрах: шаги я ещё не мерила.",
            "五张纸来自已经写好的故事。这不是走过多少公里的报告：步数我还没量。",
            "p",
            "deck",
        ),
        '<div class="cards">\n' + "\n".join(cards) + "\n</div>",
        f'<p><a href="urok.html">{bi_span("Общий лист для урока", "总的课堂纸")}</a></p>',
    ])
    write_page("marshruty.html", "Маршруты", "路线", body, wide=True)


def catalog_page():
    cards = []
    for place in content.PLACES:
        themes = " ".join(place["themes"])
        period_key = place.get("period_key") or "emigration"
        kind_key = place.get("kind_key") or "story"
        cards.append(
            f"""<a class="card card-bilingual" href="{esc(place['file'])}" data-themes="{esc(themes)}" data-period="{esc(period_key)}" data-kind="{esc(kind_key)}">
  <p class="meta">{bi_span(place['period_ru'] + " · " + place['kind_ru'] + " · " + place['where_ru'], place['period_zh'] + " · " + place['kind_zh'] + " · " + place['where_zh'])}</p>
  <p class="card-title-zh">{esc(place['title_zh'])}</p>
  <p class="card-title-ru">{esc(place['title_ru'])}</p>
  <p class="card-text ru">{esc(place['hook_ru'])}</p>
  <p class="card-text zh">{esc(place['hook_zh'])}</p>
  <span class="card-cta">{bi_span("Смотреть историю", "阅读故事")}</span>
</a>"""
        )
    body = "\n".join([
        f"<h1>{bi_span('Места', '地点')}</h1>",
        both(
            "Фильтры по периоду, типу места и школьной теме. Поиск — по названию, улице или слову в тексте.",
            "按年代、地点类型和课堂题目筛选。搜索名称、街名或正文里的词。",
            "p",
            "deck",
        ),
        '<div data-catalog>',
        '<form class="search" action="mesta.html" method="get" role="search">',
        '<label for="q">' + bi_span("Найти место", "找地点") + '</label>',
        '<input id="q" name="q" type="search" data-filter-text>',
        "</form>",
        f'<p class="filter-label">{bi_span("Период", "年代")}</p>',
        filter_buttons_attr("data-period-filter", content.PERIOD_FILTERS),
        f'<p class="filter-label">{bi_span("Тип места", "地点类型")}</p>',
        filter_buttons_attr("data-kind-filter", content.KIND_FILTERS),
        f'<p class="filter-label">{bi_span("Школьная тема", "课堂题目")}</p>',
        filter_buttons("data-theme"),
        f'<p data-empty hidden>{bi_span("Такого места в каталоге нет.", "目录里没有这个地点。")}</p>',
        '<div class="cards">\n' + "\n".join(cards) + "\n</div>",
        "</div>",
    ])
    write_page("mesta.html", "Места", "地点", body, wide=True, scripts='<script src="js/catalog.js"></script>')


def lesson_page():
    lesson = content.LESSON
    facts = "\n".join(
        f"<li>{bi_span(ru, zh)}</li>" for ru, zh in zip(lesson["facts_ru"], lesson["facts_zh"])
    )
    links = "\n".join(
        f'<li><a href="{esc(route["file"])}">{bi_span(route["title_ru"], route["title_zh"])}</a></li>'
        for route in content.ROUTES
    )
    body = "\n".join([
        f"<h1>{bi_span(lesson['h1_ru'], lesson['h1_zh'])}</h1>",
        both(lesson["deck_ru"], lesson["deck_zh"], "p", "deck"),
        f'<h2>{bi_span("Возраст", "年龄")}</h2>',
        both(lesson["age_ru"], lesson["age_zh"]),
        f'<h2>{bi_span("Тема", "题目")}</h2>',
        both(lesson["topic_ru"], lesson["topic_zh"]),
        f'<h2>{bi_span("Цель", "目标")}</h2>',
        both(lesson["goal_ru"], lesson["goal_zh"]),
        f'<h2>{bi_span("Пять фактов", "五个事实")}</h2>',
        f"<ol class=\"facts\">\n{facts}\n</ol>",
        f'<h2>{bi_span("Вопрос до маршрута", "出发前的问题")}</h2>',
        both(lesson["before_ru"], lesson["before_zh"]),
        f'<h2>{bi_span("Задание", "任务")}</h2>',
        both(lesson["there_ru"], lesson["there_zh"]),
        f'<h2>{bi_span("Вопрос после", "结束后的问题")}</h2>',
        both(lesson["after_ru"], lesson["after_zh"]),
        f'<h2>{bi_span("Ученику", "给学生")}</h2>',
        both(lesson["pupil_ru"], lesson["pupil_zh"]),
        f"<ul>\n{links}\n</ul>",
        f'<h2>{bi_span("Учителю", "给老师")}</h2>',
        both(lesson["teacher_ru"], lesson["teacher_zh"]),
        f'<p><a href="istochniki.html">{bi_span("Список источников", "出处名单")}</a></p>',
        f'<p class="noprint"><button type="button" data-print>{bi_span("Распечатать лист", "打印这一页")}</button></p>',
    ])
    write_page("urok.html", lesson["h1_ru"], lesson["h1_zh"], body)


def project_page():
    parts = [
        f"<h1>{bi_span('Проект', '项目')}</h1>",
        both(
            "Эта страница для жюри, учителя и СМИ: что сделано, чего нет, и как проверяются факты.",
            "这一页给评委、老师和媒体：已经做了什么、还没有什么、事实怎么核对。",
            "p",
            "deck",
        ),
        value_grid(),
        use_grid(),
    ]
    for title_ru, title_zh, paras_ru, paras_zh in content.PROJECT:
        parts.append(f"<h2>{bi_span(title_ru, title_zh)}</h2>")
        parts.append(paras(paras_ru, "ru"))
        parts.append(paras(paras_zh, "zh"))
    parts.append(f'<h2>{bi_span("Где это лежит", "这些东西在哪儿")}</h2>')
    parts.append(
        "<ul class=\"facts\">\n"
        f'<li><a href="karta.html">{bi_span("Карта", "地图")}</a></li>\n'
        f'<li><a href="mesta.html">{bi_span("Места", "地点")}</a></li>\n'
        f'<li><a href="marshruty.html">{bi_span("Маршруты", "路线")}</a></li>\n'
        f'<li><a href="urok.html">{bi_span("Для урока", "课堂")}</a></li>\n'
        f'<li><a href="istochniki.html#proverka">{bi_span("Как я проверяю", "我怎么核对")}</a></li>\n'
        f'<li><a href="{esc(content.VK_COMMUNITY)}">VK</a></li>\n'
        f'<li><a href="{esc(content.TG_CHANNEL)}">Telegram</a></li>\n'
        "</ul>"
    )
    parts.append(f'<h2>{bi_span("Написать проекту", "给项目写信")}</h2>')
    parts.append(both(
        "Письмо — в сообщество ВК или в Telegram. Телефон и домашний адрес я не оставляю.",
        "写信请到VK社区或Telegram。电话和家里的地址我不留。",
    ))
    parts.append(f'<p class="updated">{bi_span(content.UPDATED_RU, content.UPDATED_ZH)}</p>')
    write_page("proekt.html", "Проект", "项目", "\n".join(parts))


def missing_page():
    body = "\n".join([
        f"<h1>{bi_span('Такой страницы нет', '没有这一页')}</h1>",
        both(
            "Адрес не совпал ни с одним местом. Карта и каталог на месте.",
            "这个地址对不上任何地点。地图和目录还在。",
            "p",
            "deck",
        ),
        '<form class="search" action="mesta.html" method="get" role="search">',
        '<label for="q">' + bi_span("Найти место", "找地点") + '</label>',
        '<input id="q" name="q" type="search">',
        f'<button type="submit">{bi_span("Искать", "查找")}</button>',
        "</form>",
        '<div class="actions">',
        f'<a href="index.html">{bi_span("Начало", "首页")}</a>',
        f'<a class="ghost" href="karta.html">{bi_span("Карта", "地图")}</a>',
        f'<a class="ghost" href="mesta.html">{bi_span("Места", "地点")}</a>',
        "</div>",
    ])
    write_page("404.html", "Страница не найдена", "没有这一页", body)


def write_seo_files():
    pages = [page["file"] for page in content.PAGES]
    pages += [route["file"] for route in content.ROUTES]
    pages += ["marshruty.html", "mesta.html", "urok.html", "proekt.html"]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for filename in pages:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(page_url(filename))}</loc>")
        lines.append("    <lastmod>2026-10-30</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    robots = (
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: https://{content.DOMAIN}/sitemap.xml\n"
    )
    (ROOT / "robots.txt").write_text(robots, encoding="utf-8")
    print("sitemap.xml")
    print("robots.txt")


def write_text_bundle():
    lines = []
    for page in content.PAGES:
        lines.append("## " + page["h1_ru"])
        for key in ("deck_ru", "who_ru", "quote_ru", "class_ru"):
            if page.get(key):
                lines.append(page[key])
        lines.extend(page.get("paras_ru") or [])
        lines.extend(page.get("tail_ru") or [])
        lines.extend(page.get("check_ru") or [])
        if page.get("cards"):
            for card in content.CARDS:
                lines.append(card["title_ru"] + ". " + card["text_ru"])
    for route in content.ROUTES:
        lines.append("## " + route["title_ru"])
        lines.append(route["question_ru"])
        lines.append(route["before_ru"])
        lines.append(route["there_ru"])
        lines.append(route["after_ru"])
    lines.append("## " + content.LESSON["h1_ru"])
    lines.append(content.LESSON["goal_ru"])
    for title_ru, _title_zh, paras_ru, _paras_zh in content.PROJECT:
        lines.append("## " + title_ru)
        lines.extend(paras_ru)
    bundle = ROOT.parent / "texts"
    bundle.mkdir(exist_ok=True)
    (bundle / "site-ru.txt").write_text("\n\n".join(lines), encoding="utf-8")


def main():
    credits = load_credits()
    for page in content.PAGES:
        render(page, credits)
    routes_index()
    for route in content.ROUTES:
        route_page(route)
    catalog_page()
    lesson_page()
    project_page()
    missing_page()
    write_seo_files()
    write_text_bundle()


if __name__ == "__main__":
    main()
