(function () {
  // Подложка карты по языку сайта.
  // Русский: Яндекс (подписи по-русски, проекция EPSG:3395, координаты WGS-84).
  // Китайский: Gaode (подписи по-китайски, проекция EPSG:3857, сдвиг GCJ-02).
  // Если плитки не грузятся, переходим на следующую подложку, последняя — OpenStreetMap.
  if (typeof L === "undefined") return;

  function outOfChina(lat, lon) {
    return lon < 72.004 || lon > 137.8347 || lat < 0.8293 || lat > 55.8271;
  }
  function tLat(x, y) {
    var r = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
    r += (20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2 / 3;
    r += (20 * Math.sin(y * Math.PI) + 40 * Math.sin(y / 3 * Math.PI)) * 2 / 3;
    r += (160 * Math.sin(y / 12 * Math.PI) + 320 * Math.sin(y * Math.PI / 30)) * 2 / 3;
    return r;
  }
  function tLon(x, y) {
    var r = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
    r += (20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2 / 3;
    r += (20 * Math.sin(x * Math.PI) + 40 * Math.sin(x / 3 * Math.PI)) * 2 / 3;
    r += (150 * Math.sin(x / 12 * Math.PI) + 300 * Math.sin(x / 30 * Math.PI)) * 2 / 3;
    return r;
  }
  function gcj(lat, lon) {
    if (outOfChina(lat, lon)) return [lat, lon];
    var a = 6378245.0, ee = 0.00669342162296594323;
    var dLat = tLat(lon - 105.0, lat - 35.0), dLon = tLon(lon - 105.0, lat - 35.0);
    var rad = lat / 180.0 * Math.PI, m = Math.sin(rad);
    m = 1 - ee * m * m;
    var s = Math.sqrt(m);
    dLat = (dLat * 180.0) / ((a * (1 - ee)) / (m * s) * Math.PI);
    dLon = (dLon * 180.0) / (a / s * Math.cos(rad) * Math.PI);
    return [lat + dLat, lon + dLon];
  }
  function wgs(lat, lon) { return [lat, lon]; }

  var KINDS = {
    yandex: {
      url: "https://core-renderer-tiles.maps.yandex.net/tiles?l=map&x={x}&y={y}&z={z}&scale=1&lang=ru_RU",
      crs: L.CRS.EPSG3395, conv: wgs, opts: { maxZoom: 18 }
    },
    gaode: {
      url: "https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
      crs: L.CRS.EPSG3857, conv: gcj, opts: { maxZoom: 18, subdomains: "1234" }
    },
    osm: {
      url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      crs: L.CRS.EPSG3857, conv: wgs, opts: { maxZoom: 18 }
    }
  };
  var ORDER = { ru: ["yandex", "gaode", "osm"], zh: ["gaode", "osm"] };

  function siteLang() {
    return document.body.getAttribute("data-lang") === "zh" ? "zh" : "ru";
  }

  // draw(map, toLatLng) вызывается после каждого (пере)создания карты.
  window.ulitsyBasemap = function (el, options, draw) {
    var state = { map: null, kind: null, lang: siteLang(), failed: {} };

    function build(kind) {
      var k = KINDS[kind];
      if (state.map) { state.map.remove(); state.map = null; }
      var opts = {};
      for (var key in options) opts[key] = options[key];
      opts.crs = k.crs;
      opts.attributionControl = false;
      var map = L.map(el, opts);
      var layer = L.tileLayer(k.url, k.opts).addTo(map);
      var errors = 0, loaded = 0;
      layer.on("tileload", function () { loaded += 1; });
      layer.on("tileerror", function () {
        errors += 1;
        if (errors < 4 || loaded > 0 || state.map !== map) return;
        state.failed[kind] = true;
        var next = nextKind();
        if (next && next !== kind) setTimeout(function () { build(next); }, 0);
      });
      state.map = map;
      state.kind = kind;
      draw(map, k.conv);
    }

    function nextKind() {
      var list = ORDER[state.lang];
      for (var i = 0; i < list.length; i += 1) {
        if (!state.failed[list[i]]) return list[i];
      }
      return list[list.length - 1];
    }

    document.addEventListener("ulitsy:lang", function () {
      var lang = siteLang();
      if (lang === state.lang) return;
      state.lang = lang;
      var want = nextKind();
      if (want !== state.kind) build(want);
    });

    build(nextKind());
    return state;
  };
})();
