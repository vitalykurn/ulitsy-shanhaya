"""Мозаика плиток Яндекса (EPSG:3395, подписи по-русски) для района прогулки."""
import math, pathlib, time, urllib.request, io
from PIL import Image

HERE = pathlib.Path(__file__).parent
CACHE = HERE / "tiles"
CACHE.mkdir(exist_ok=True)
Z = 16
SCALE = 2          # плитки 512 px
TS = 256 * SCALE
E = 0.0818191908426
URL = "https://core-renderer-tiles.maps.yandex.net/tiles?l=map&x={x}&y={y}&z={z}&scale=2&lang=ru_RU"


def world_px(lat, lon, z=Z):
    """Пиксель в мировых координатах плиток 512 px (EPSG:3395)."""
    size = TS * 2 ** z
    x = (lon / 360.0 + 0.5) * size
    phi = math.radians(lat)
    es = E * math.sin(phi)
    y_merc = math.log(math.tan(math.pi / 4 + phi / 2) * ((1 - es) / (1 + es)) ** (E / 2))
    y = (0.5 - y_merc / (2 * math.pi)) * size
    return x, y


def fetch(x, y, z=Z):
    f = CACHE / f"{z}_{x}_{y}.png"
    if f.exists() and f.stat().st_size > 0:
        return Image.open(f).convert("RGB")
    req = urllib.request.Request(URL.format(x=x, y=y, z=z), headers={"User-Agent": "Mozilla/5.0 (map video render)"})
    for attempt in range(6):
        try:
            data = urllib.request.urlopen(req, timeout=30).read()
            break
        except Exception as e:  # обрывы через прокси
            print("retry", x, y, e)
            time.sleep(1.5 * (attempt + 1))
    else:
        raise RuntimeError(f"tile {x},{y} failed")
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.save(f)
    time.sleep(0.15)
    return im


def mosaic(px0, py0, px1, py1):
    """Склеить плитки, покрывающие прямоугольник в мировых пикселях. Вернуть (картинка, x0, y0)."""
    tx0, ty0 = int(px0 // TS), int(py0 // TS)
    tx1, ty1 = int(px1 // TS), int(py1 // TS)
    img = Image.new("RGB", ((tx1 - tx0 + 1) * TS, (ty1 - ty0 + 1) * TS), (240, 238, 232))
    n = 0
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            img.paste(fetch(tx, ty), ((tx - tx0) * TS, (ty - ty0) * TS))
            n += 1
    print("tiles", n, img.size)
    return img, tx0 * TS, ty0 * TS
