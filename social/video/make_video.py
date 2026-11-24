"""Вертикальный ролик 9:16 прогулки по маршруту сайта: карта Яндекса, линия, остановки с фото.

    python social/video/make_video.py zhoffr social/progulka-1-pushkin-gaolan-9x16.mp4
    python social/video/make_video.py sobor  social/progulka-2-sobor-paramount-9x16.mp4
    python social/video/make_video.py bund   social/progulka-3-ippodrom-konsulstvo-9x16.mp4
    python social/video/make_video.py zhoffr x.mp4 --preview   # кадр каждые 4 с в social/video/preview

Нужны Python с Pillow и ffmpeg в PATH. Маршрут, тексты и фото берутся из site/content.py,
site/_walks_geo.json и site/img: после правки прогулки на сайте ролик просто пересобирается.
Плитки карты кэшируются в social/video/tiles. Шрифты Georgia, Segoe UI, Microsoft YaHei — из Windows.
"""
import json, math, pathlib, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent.parent / "site"
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(HERE))
import content, build_site as B  # noqa: E402
from tiles import world_px, mosaic  # noqa: E402

W, H, FPS = 1080, 1920, 30
SS = 2  # суперсэмплинг слоя с линией
PAPER = (247, 242, 233)
INK = (33, 28, 24)
MUTED = (110, 100, 92)
FONTS = pathlib.Path(r"C:\Windows\Fonts")


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


F_KICK = font("segoeuib.ttf", 30)
F_TITLE = font("georgiab.ttf", 60)
F_META = font("segoeui.ttf", 32)
F_CARD_T = font("georgiab.ttf", 50)
F_BODY = font("segoeui.ttf", 36)
F_CREDIT = font("segoeui.ttf", 23)
F_NUM = font("segoeuib.ttf", 34)
F_LABEL = font("segoeuib.ttf", 28)
F_BIG = font("georgiab.ttf", 76)
F_SMALL = font("segoeui.ttf", 22)


SHORT = {"st_changshu": "Улица Чаншу", "st_xintiandi": "Синьтяньди", "st_shaanxi": "Южная улица Шэньси",
         "st_jingan": "Храм Цзинъань", "st_peoples": "Народная площадь", "st_nanjing_e": "Восточная Нанкинская"}


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


import re
CJK = re.compile(r"([　-〿㐀-鿿＀-￯]+)")
_cjk_cache = {}


def cjk_font(fnt):
    if fnt.size not in _cjk_cache:
        _cjk_cache[fnt.size] = ImageFont.truetype(str(FONTS / "msyh.ttc"), fnt.size)
    return _cjk_cache[fnt.size]


def runs(text, fnt):
    for i, part in enumerate(CJK.split(text)):
        if part:
            yield part, (cjk_font(fnt) if i % 2 else fnt)


def tlen(text, fnt):
    return sum(f.getlength(part) for part, f in runs(text, fnt))


def mtext(d, xy, text, fnt, fill, center=False):
    """Текст с иероглифами: кириллица своим шрифтом, китайские знаки — Microsoft YaHei."""
    x, y = xy
    if center:
        x -= tlen(text, fnt) / 2
    asc = fnt.getmetrics()[0]
    for part, f in runs(text, fnt):
        d.text((x, y + asc), part, font=f, fill=fill, anchor="ls")
        x += f.getlength(part)


def wrap(text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if tlen(test, fnt) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def hav(a, b):
    r = 6371000
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def km(m):
    return f"{m / 1000:.1f}".replace(".", ",")


# ---------------------------------------------------------------- данные
def load(walk_id):
    walk = next(w for w in content.WALKS if w["id"] == walk_id)
    geo = B.walks_geo()
    credits = B.load_credits()
    data = B.walk_data(walk, geo, credits)
    photos = credits.get("photos") or {}
    stops = []
    for s, d in zip(walk["stops"], data["stops"]):
        page = next((p for p in content.PAGES if p["file"] == s["file"]), {})
        keys = [s["point"]] + list(page.get("photos") or [])
        photo = None
        for k in keys:
            ph = photos.get(k) or {}
            f = SITE / (ph.get("file") or f"img/{k}.jpg")
            if ph and f.exists():
                kind = content.PHOTO_WHEN.get(k, ("today", "", ""))[0]
                who = ph.get("artist") or ""
                lic = ph.get("license") or ""
                pre = "Архивный снимок" if kind == "archive" else "Фото"
                photo = {"file": f, "credit": f"{pre}: {who}, {lic}. Викисклад".replace(" , ", " ")}
                break
        stops.append({"n": d["n"], "lat": d["lat"], "lon": d["lon"], "title": s["title_ru"],
                      "text": s["look_ru"], "photo": photo})
    return walk, geo["walks"][walk_id], data, stops


# ---------------------------------------------------------------- видео
class Renderer:
    def __init__(self, walk_id):
        self.walk, self.g, self.data, self.stops = load(walk_id)
        self.color = hexrgb(self.walk["color"])
        self.total_m = self.g["m"]
        path = self.data["path"]
        self.wpath = [world_px(lat, lon) for lat, lon in path]
        self.cum = [0.0]
        for a, b in zip(path, path[1:]):
            self.cum.append(self.cum[-1] + hav(a, b))
        self.plen = self.cum[-1]
        # индексы остановок на линии
        idx, last = [], 0
        for s in self.stops:
            sp = world_px(s["lat"], s["lon"])
            best = min(range(last, len(self.wpath)), key=lambda i: (self.wpath[i][0] - sp[0]) ** 2 + (self.wpath[i][1] - sp[1]) ** 2)
            idx.append(best)
            last = best
            s["w"] = sp
        self.stop_d = [self.cum[i] for i in idx]
        self.ends = [dict(e, w=world_px(e["lat"], e["lon"])) for e in self.data["ends"]]
        st_keys = [k for k in (self.walk["start"], self.walk["finish"]) if k in content.WALK_STATIONS]
        for e, k in zip(self.ends, st_keys):
            e["key"] = k
        self.start_end = next((e for e in self.ends if e["key"] == self.walk["start"]), None)
        self.finish_end = next((e for e in self.ends if e["key"] == self.walk["finish"]), None)
        xs = [p[0] for p in self.wpath]
        ys = [p[1] for p in self.wpath]
        self.bbox = (min(xs), min(ys), max(xs), max(ys))
        self.s_over = min((W - 160) / (self.bbox[2] - self.bbox[0]), 620 / (self.bbox[3] - self.bbox[1]))
        self.s_follow = 0.9
        cx, cy = (self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2
        halfw = W / 2 / self.s_over + 40
        halfh = (H / 2 + 330) / self.s_over + 40
        self.map, self.mx, self.my = mosaic(cx - halfw - 700, cy - halfh, cx + halfw + 700, cy + halfh)
        self.map_half = self.map.resize((self.map.width // 2, self.map.height // 2), Image.LANCZOS)
        self.overview_c = (cx, cy + (H / 2 - 650) / self.s_over)
        self.build_timeline()
        self.cam = None
        self.photo_cache = {}

    # --- таймлайн: список сегментов
    def build_timeline(self):
        segs = [("intro", 3.6)]
        dists = [0.0] + self.stop_d + [self.plen]
        for i in range(len(dists) - 1):
            meters = (dists[i + 1] - dists[i]) / self.plen * self.total_m
            if meters >= 40:
                segs.append(("walk", max(2.4, meters / 230.0), dists[i], dists[i + 1]))
            if i < len(self.stops):
                segs.append(("stop", 6.0 if self.stops[i]["photo"] else 5.0, i))
        segs.append(("finish", 1.6))
        segs.append(("outro", 5.0))
        self.segs = segs
        self.duration = sum(s[1] for s in segs)

    def at(self, t):
        acc = 0.0
        for s in self.segs:
            if t < acc + s[1]:
                return s, (t - acc) / s[1], t - acc
            acc += s[1]
        return self.segs[-1], 1.0, self.segs[-1][1]

    def point_at(self, d):
        d = max(0.0, min(self.plen, d))
        for i in range(1, len(self.cum)):
            if self.cum[i] >= d:
                a, b = self.wpath[i - 1], self.wpath[i]
                span = self.cum[i] - self.cum[i - 1] or 1
                k = (d - self.cum[i - 1]) / span
                return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k), i
        return self.wpath[-1], len(self.wpath) - 1

    # --- состояние кадра
    def state(self, t):
        seg, k, local = self.at(t)
        kind = seg[0]
        st = {"kind": kind, "k": k, "local": local, "card": None, "stop_i": None}
        if kind == "intro":
            st["drawn"] = 0.0
            st["target"] = (self.overview_c, self.s_over)
        elif kind == "walk":
            d = seg[2] + (seg[3] - seg[2]) * ease(k)
            st["drawn"] = d
            head, _ = self.point_at(d)
            st["target"] = ((head[0], head[1] - 60 / self.s_follow), self.s_follow)
        elif kind == "stop":
            i = seg[2]
            st["drawn"] = self.stop_d[i]
            st["stop_i"] = i
            sp = self.stops[i]["w"]
            # остановка в верхней части кадра, под шапкой, над карточкой
            st["target"] = ((sp[0], sp[1] + (H / 2 - 560) / self.s_follow), self.s_follow)
            st["card"] = i
        else:
            st["drawn"] = self.plen
            st["target"] = (self.overview_c, self.s_over)
        return st

    def step_camera(self, target, first=False):
        (tx, ty), ts = target
        if self.cam is None or first:
            self.cam = [tx, ty, ts]
            return
        a = 0.11
        self.cam[0] += (tx - self.cam[0]) * a
        self.cam[1] += (ty - self.cam[1]) * a
        self.cam[2] += (ts - self.cam[2]) * a

    def to_screen(self, p):
        cx, cy, s = self.cam
        return (W / 2 + (p[0] - cx) * s, H / 2 + (p[1] - cy) * s)

    # --- рисование
    def draw_map(self):
        cx, cy, s = self.cam
        src, ss, ox, oy = (self.map, s, self.mx, self.my)
        if s < 0.62:
            src, ss = self.map_half, s * 2
            ox, oy = self.mx / 2, self.my / 2
            cx, cy = cx / 2, cy / 2
        x0 = (cx - ox) - W / 2 / ss
        y0 = (cy - oy) - H / 2 / ss
        return src.transform((W, H), Image.AFFINE, (1 / ss, 0, x0, 0, 1 / ss, y0), resample=Image.BILINEAR)

    def draw_overlay(self, st, t):
        ov = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        sc = lambda p: tuple(v * SS for v in self.to_screen(p))  # noqa: E731
        allpts = [sc(p) for p in self.wpath]
        # призрачная линия всего маршрута
        d.line(allpts, fill=self.color + (90,), width=6 * SS, joint="curve")
        drawn = st["drawn"]
        if drawn > 0:
            head, i = self.point_at(drawn)
            pts = [sc(p) for p in self.wpath[:i]] + [sc(head)]
            if len(pts) >= 2:
                d.line(pts, fill=(255, 255, 255, 235), width=19 * SS, joint="curve")
                d.line(pts, fill=self.color + (255,), width=11 * SS, joint="curve")
        # станции метро
        for j, e in enumerate(self.ends):
            x, y = sc(e["w"])
            r = 13 * SS
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255), outline=self.color + (255,), width=6 * SS)
        # остановки
        for i, s in enumerate(self.stops):
            x, y = sc(s["w"])
            reached = drawn >= self.stop_d[i] - 1
            r = (27 if reached else 22) * SS
            if st["stop_i"] == i:
                pulse = 0.5 + 0.5 * math.sin(t * 5)
                rr = r + (10 + 10 * pulse) * SS
                d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=self.color + (60,))
            d.ellipse((x - r - 4 * SS, y - r - 4 * SS, x + r + 4 * SS, y + r + 4 * SS), fill=(255, 255, 255, 255))
            d.ellipse((x - r, y - r, x + r, y + r), fill=(self.color + (255,)) if reached else (255, 255, 255, 255),
                      outline=self.color + (255,), width=4 * SS)
            fnt = font("segoeuib.ttf", (34 if reached else 28) * SS)
            d.text((x, y + 1 * SS), str(s["n"]), font=fnt, anchor="mm", fill=(255, 255, 255) if reached else self.color)
        # голова линии
        if st["kind"] == "walk":
            hx, hy = sc(self.point_at(drawn)[0])
            r = 12 * SS
            d.ellipse((hx - r - 5 * SS, hy - r - 5 * SS, hx + r + 5 * SS, hy + r + 5 * SS), fill=(255, 255, 255, 255))
            d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=INK + (255,))
        return ov.reduce(SS)

    def pill(self, frame, xy, text, anchor_above=True):
        d = ImageDraw.Draw(frame)
        x, y = xy
        tw = F_LABEL.getlength(text)
        w, h = tw + 36, 52
        bx = max(20, min(W - 20 - w, x - w / 2))
        by = y - 30 - h if anchor_above else y + 30
        d.rounded_rectangle((bx, by, bx + w, by + h), radius=26, fill=(255, 255, 255), outline=self.color, width=3)
        d.text((bx + w / 2, by + h / 2), text, font=F_LABEL, fill=INK, anchor="mm")

    def header(self, frame, st):
        top = Image.new("RGBA", (W, 250), PAPER + (238,))
        frame.paste(top, (0, 0), top)
        d = ImageDraw.Draw(frame)
        d.text((60, 52), "ПЕШАЯ ПРОГУЛКА ПО ШАНХАЮ", font=F_KICK, fill=self.color)
        size = 60
        while font("georgiab.ttf", size).getlength(self.walk["title_ru"]) > W - 120 and size > 40:
            size -= 2
        d.text((60, 92 + (60 - size) // 2), self.walk["title_ru"], font=font("georgiab.ttf", size), fill=INK)
        walked = st["drawn"] / self.plen * self.total_m
        meta = f"пройдено {km(walked)} из {km(self.total_m)} км"
        n_done = sum(1 for sd in self.stop_d if st["drawn"] >= sd - 1)
        meta += f"  ·  остановок {n_done} из {len(self.stops)}"
        d.text((60, 178), meta, font=F_META, fill=MUTED)
        d.rectangle((0, 247, W, 250), fill=self.color)
        d.text((W - 24, 262), "Карта © Яндекс", font=F_SMALL, fill=(120, 120, 120), anchor="ra")

    def get_photo(self, f, size):
        key = (str(f), size)
        if key not in self.photo_cache:
            im = Image.open(f).convert("RGB")
            tw, th = size
            k = max(tw / im.width, th / im.height)
            im = im.resize((math.ceil(im.width * k), math.ceil(im.height * k)), Image.LANCZOS)
            l, t = (im.width - tw) // 2, (im.height - th) // 2
            im = im.crop((l, t, l + tw, t + th))
            mask = Image.new("L", (tw * 2, th * 2), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw * 2, th * 2), radius=36, fill=255)
            self.photo_cache[key] = (im, mask.resize((tw, th), Image.LANCZOS))
        return self.photo_cache[key]

    def card(self, frame, st):
        i = st["card"]
        s = self.stops[i]
        seg_len = self.segs and next(sg[1] for sg in self.segs if sg[0] == "stop" and sg[2] == i)
        local = st["local"]
        appear = ease(local / 0.5) * (1 - ease((local - (seg_len - 0.45)) / 0.45))
        if appear <= 0:
            return
        pad, cw = 44, W - 80
        lines = wrap(s["text"], F_BODY, cw - 2 * pad)
        title_lines = wrap(s["title"], F_CARD_T, cw - 2 * pad - 90)
        ph_h = 520 if s["photo"] else 0
        h = pad + ph_h + (30 if ph_h else 0) + len(title_lines) * 62 + 18 + len(lines) * 50 + (44 if s["photo"] else 0) + pad
        bottom = H - 210
        y0 = bottom - h + (1 - appear) * 120
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        x0 = 40
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 10, x0 + cw, y0 + h + 10), radius=34, fill=(0, 0, 0, 70))
        sh = sh.filter(ImageFilter.GaussianBlur(14))
        layer.alpha_composite(sh)
        d.rounded_rectangle((x0, y0, x0 + cw, y0 + h), radius=34, fill=PAPER + (255,))
        y = y0 + pad
        if s["photo"]:
            im, mask = self.get_photo(s["photo"]["file"], (cw - 2 * pad, ph_h))
            layer.paste(im, (int(x0 + pad), int(y)), mask)
            y += ph_h + 30
        # номер
        r = 34
        cxn, cyn = x0 + pad + r, y + 30
        d.ellipse((cxn - r, cyn - r, cxn + r, cyn + r), fill=self.color + (255,))
        d.text((cxn, cyn + 1), str(s["n"]), font=F_NUM, fill=(255, 255, 255), anchor="mm")
        for j, ln in enumerate(title_lines):
            d.text((x0 + pad + 90, y + j * 62), ln, font=F_CARD_T, fill=INK)
        y += max(len(title_lines) * 62, 70) + 18
        for ln in lines:
            mtext(d, (x0 + pad, y), ln, F_BODY, INK)
            y += 50
        if s["photo"]:
            d.text((x0 + pad, y + 10), s["photo"]["credit"], font=F_CREDIT, fill=MUTED)
        if appear < 1:
            a = layer.getchannel("A").point(lambda v: int(v * appear))
            layer.putalpha(a)
        frame.alpha_composite(layer)

    def center_card(self, frame, lines, alpha, y_center=1180):
        """lines: список (текст, шрифт, цвет)."""
        if alpha <= 0:
            return
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        cw = W - 120
        wrapped = []
        for text, fnt, col, gap in lines:
            for ln in wrap(text, fnt, cw - 100):
                wrapped.append((ln, fnt, col, fnt.size + gap))
        h = sum(x[3] for x in wrapped) + 100
        y0 = y_center - h / 2
        d.rounded_rectangle((60, y0, W - 60, y0 + h), radius=34, fill=PAPER + (248,), outline=self.color + (255,), width=4)
        y = y0 + 50
        for ln, fnt, col, step in wrapped:
            mtext(d, (W / 2, y), ln, fnt, col, center=True)
            y += step
        if alpha < 1:
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
        frame.alpha_composite(layer)

    def frame(self, t, first=False):
        st = self.state(t)
        self.step_camera(st["target"], first)
        base = self.draw_map().convert("RGBA")
        base.alpha_composite(self.draw_overlay(st, t))
        kind = st["kind"]
        if self.start_end and kind in ("intro", "walk") and st["drawn"] < self.stop_d[0]:
            self.pill(base, self.to_screen(self.start_end["w"]), "Старт: м. «" + SHORT[self.start_end["key"]] + "»")
        if self.finish_end and (kind in ("finish", "outro") or (kind == "walk" and st["drawn"] > self.stop_d[-1] + 50)):
            self.pill(base, self.to_screen(self.finish_end["w"]), "Финиш: м. «" + SHORT[self.finish_end["key"]] + "»")
        self.header(base, st)
        if st["card"] is not None:
            self.card(base, st)
        if kind == "intro":
            a = 1 - ease((st["local"] - 2.9) / 0.6)
            self.center_card(base, [
                ("Русский Шанхай пешком", F_KICK, self.color, 26),
                (self.walk["title_ru"], F_BIG, INK, 26),
                (self.walk["deck_ru"], F_BODY, INK, 30),
                (f"{km(self.total_m)} км  ·  {len(self.stops)} остановки  ·  около {B.walk_minutes(self.total_m)} минут ходьбы", F_META, MUTED, 14),
            ], a, 1380)
        if kind == "outro":
            a = ease(st["local"] / 0.6)
            self.center_card(base, [
                ("Истории всех остановок, адреса и источники", F_BODY, INK, 20),
                ("ulitsy-shanhaya.ru", F_BIG, self.color, 30),
                ("История России на улицах Шанхая", F_META, MUTED, 10),
            ], a, 1420)
        return base.convert("RGB")


def main():
    walk_id = sys.argv[1]
    out = sys.argv[2]
    preview = "--preview" in sys.argv
    r = Renderer(walk_id)
    print("duration", round(r.duration, 1), "s")
    if preview:
        outdir = HERE / "preview"
        outdir.mkdir(exist_ok=True)
        n = int(r.duration * FPS)
        marks = {int(x * FPS) for x in sys.argv[3].split(",")} if len(sys.argv) > 3 and not sys.argv[3].startswith("-") else set(range(0, n, FPS * 4))
        for f in range(n):
            im = r.frame(f / FPS, f == 0)
            if f in marks:
                im.resize((W // 2, H // 2), Image.LANCZOS).save(outdir / f"f{f:05d}.jpg", quality=85)
        return
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(r.duration * FPS)
    for f in range(n):
        p.stdin.write(r.frame(f / FPS, f == 0).tobytes())
        if f % 150 == 0:
            print(f, "/", n, flush=True)
    p.stdin.close()
    p.wait()
    print("done", out)


if __name__ == "__main__":
    main()
