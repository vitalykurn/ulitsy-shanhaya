(function () {
  var el = document.getElementById("map")
    || document.getElementById("map-home")
    || document.getElementById("map-spot");
  var list = document.querySelector("[data-map-list]");
  if (!el) return;
  var points = [];
  try { points = JSON.parse(el.getAttribute("data-points") || "[]"); } catch (e) { points = []; }
  var items = list ? Array.prototype.slice.call(list.querySelectorAll("[data-themes]")) : [];
  var empty = document.getElementById("map-empty");
  var layout = document.querySelector(".map-layout");
  var theme = "all";
  var markers = [];
  var map = null;
  // Подложка Gaode (高德) открывается в Китае, OpenStreetMap часто нет.
  // Gaode рисует в системе GCJ-02, наши точки в WGS-84: переводим при показе.
  // Если плитки Gaode не грузятся, карта сама переходит на OpenStreetMap.
  var useGcj = true;

  function outOfChina(lat, lon) {
    return lon < 72.004 || lon > 137.8347 || lat < 0.8293 || lat > 55.8271;
  }

  function transformLat(x, y) {
    var r = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
    r += (20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2 / 3;
    r += (20 * Math.sin(y * Math.PI) + 40 * Math.sin(y / 3 * Math.PI)) * 2 / 3;
    r += (160 * Math.sin(y / 12 * Math.PI) + 320 * Math.sin(y * Math.PI / 30)) * 2 / 3;
    return r;
  }

  function transformLon(x, y) {
    var r = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
    r += (20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2 / 3;
    r += (20 * Math.sin(x * Math.PI) + 40 * Math.sin(x / 3 * Math.PI)) * 2 / 3;
    r += (150 * Math.sin(x / 12 * Math.PI) + 300 * Math.sin(x / 30 * Math.PI)) * 2 / 3;
    return r;
  }

  function wgsToGcj(lat, lon) {
    if (outOfChina(lat, lon)) return [lat, lon];
    var a = 6378245.0, ee = 0.00669342162296594323;
    var dLat = transformLat(lon - 105.0, lat - 35.0);
    var dLon = transformLon(lon - 105.0, lat - 35.0);
    var radLat = lat / 180.0 * Math.PI;
    var magic = Math.sin(radLat);
    magic = 1 - ee * magic * magic;
    var sqrtMagic = Math.sqrt(magic);
    dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * Math.PI);
    dLon = (dLon * 180.0) / (a / sqrtMagic * Math.cos(radLat) * Math.PI);
    return [lat + dLat, lon + dLon];
  }

  function pos(p) {
    return useGcj ? wgsToGcj(p.lat, p.lon) : [p.lat, p.lon];
  }

  function markerColor(period) {
    if (period === "fifties") return "#234864";
    if (period === "empire") return "#3f6b46";
    return "#8d4a3d";
  }

  function hasTheme(value, current) {
    if (current === "all") return true;
    return (" " + value + " ").indexOf(" " + current + " ") !== -1;
  }

  function setPressed(selector, current) {
    document.querySelectorAll(selector).forEach(function (btn) {
      var on = btn.getAttribute(selector.slice(1, -1)) === current;
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  function apply() {
    var visibleMarkers = 0;
    items.forEach(function (item) {
      var show = hasTheme(item.getAttribute("data-themes") || "", theme);
      item.hidden = !show;
    });
    markers.forEach(function (row) {
      var show = hasTheme((row.point.themes || []).join(" "), theme);
      if (!map) return;
      if (show) {
        if (!map.hasLayer(row.marker)) row.marker.addTo(map);
        visibleMarkers += 1;
      } else if (map.hasLayer(row.marker)) {
        map.removeLayer(row.marker);
      }
    });
    if (empty) empty.hidden = theme === "all" || visibleMarkers > 0;
    if (layout) layout.classList.toggle("no-pins", visibleMarkers === 0);
    if (map) {
      var bounds = markers.filter(function (row) {
        return map.hasLayer(row.marker);
      }).map(function (row) {
        return pos(row.point);
      });
      if (bounds.length) map.fitBounds(bounds, { padding: [28, 28] });
      setTimeout(function () { map.invalidateSize(); }, 80);
    }
  }

  if (typeof L !== "undefined") {
    map = L.map(el, { scrollWheelZoom: false, attributionControl: false });
    var gaode = L.tileLayer("https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}", {
      subdomains: "1234",
      maxZoom: 18,
      attribution: "&copy; 高德地图 AutoNavi"
    }).addTo(map);
    var osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap"
    });
    var tileErrors = 0;
    gaode.on("tileerror", function () {
      tileErrors += 1;
      if (tileErrors < 4 || !useGcj) return;
      useGcj = false;
      map.removeLayer(gaode);
      osm.addTo(map);
      markers.forEach(function (row) { row.marker.setLatLng(pos(row.point)); });
      apply();
      if (points.length === 1) map.setView(pos(points[0]), 15);
    });
    points.forEach(function (p) {
      if (typeof p.lat !== "number" || typeof p.lon !== "number") return;
      var html = "<b><span class=\"ru\">" + p.title_ru + "</span><span class=\"zh\">" + p.title_zh + "</span></b><br>" +
        "<span class=\"ru\">" + p.addr_ru + "</span><span class=\"zh\">" + p.addr_zh + "</span><br>" +
        "<a href=\"" + p.href + "\"><span class=\"ru\">Открыть историю</span><span class=\"zh\">打开故事</span></a>";
      var icon = L.divIcon({
        className: "pin pin-" + (p.period || "emigration"),
        html: "<span style=\"background:" + markerColor(p.period) + "\"></span>",
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      });
      var marker = L.marker(pos(p), { icon: icon }).addTo(map).bindPopup(html);
      markers.push({ point: p, marker: marker });
    });
    if (points.length === 1) {
      map.setView(pos(points[0]), 15);
    }
  }

  document.querySelectorAll("[data-map-theme]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      theme = btn.getAttribute("data-map-theme");
      setPressed("[data-map-theme]", theme);
      apply();
    });
  });

  document.querySelectorAll("[data-view]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var view = btn.getAttribute("data-view");
      if (!layout) return;
      layout.classList.toggle("is-map", view === "map");
      layout.classList.toggle("is-list", view === "list");
      document.querySelectorAll("[data-view]").forEach(function (other) {
        other.setAttribute("aria-pressed", other === btn ? "true" : "false");
      });
      if (map) setTimeout(function () { map.invalidateSize(); }, 80);
    });
  });

  apply();
})();
