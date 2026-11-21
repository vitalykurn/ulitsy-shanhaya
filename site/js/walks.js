(function () {
  // Карты пеших прогулок. Подложка Gaode (GCJ-02), точки и линии в WGS-84:
  // переводим при показе. Если Gaode не грузится, переходим на OpenStreetMap.
  if (typeof L === "undefined") return;
  var els = document.querySelectorAll("[data-walks]");
  if (!els.length) return;

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

  els.forEach(function (el) {
    var walks = [];
    try { walks = JSON.parse(el.getAttribute("data-walks") || "[]"); } catch (e) { walks = []; }
    if (!walks.length) return;
    var useGcj = true;
    var map = L.map(el, { scrollWheelZoom: false, attributionControl: false, zoomSnap: 0.25 });
    var layers = L.layerGroup().addTo(map);

    function p(ll) { return useGcj ? gcj(ll[0], ll[1]) : [ll[0], ll[1]]; }

    var bounds = [];
    function fit() {
      map.invalidateSize();
      if (bounds.length) map.fitBounds(bounds, { padding: [24, 24] });
    }

    function draw() {
      layers.clearLayers();
      bounds = [];
      walks.forEach(function (w) {
        var line = w.path.map(p);
        bounds = bounds.concat(line);
        L.polyline(line, { color: "#fff", weight: 8, opacity: 0.85 }).addTo(layers);
        var pl = L.polyline(line, { color: w.color, weight: 5, opacity: 0.95 }).addTo(layers);
        if (w.href) pl.bindTooltip(w.title, { sticky: true });
        (w.ends || []).forEach(function (e) {
          L.circleMarker(p([e.lat, e.lon]), { radius: 6, color: w.color, weight: 3, fillColor: "#fff", fillOpacity: 1 })
            .addTo(layers).bindPopup("<b>" + e.label + "</b>");
        });
        w.stops.forEach(function (s) {
          var icon = L.divIcon({
            className: "walk-num",
            html: "<span style=\"background:" + w.color + "\">" + s.n + "</span>",
            iconSize: [26, 26],
            iconAnchor: [13, 13]
          });
          var html = "<b>" + s.n + ". " + s.title + "</b>" + (s.href ? "<br><a href=\"" + s.href + "\">" + s.more + "</a>" : "");
          L.marker(p([s.lat, s.lon]), { icon: icon }).addTo(layers).bindPopup(html);
        });
      });
      if (bounds.length) map.fitBounds(bounds, { padding: [24, 24] });
    }

    var gaode = L.tileLayer("https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}", {
      subdomains: "1234", maxZoom: 18
    }).addTo(map);
    var osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18 });
    var errors = 0;
    gaode.on("tileerror", function () {
      errors += 1;
      if (errors < 4 || !useGcj) return;
      useGcj = false;
      map.removeLayer(gaode);
      osm.addTo(map);
      draw();
    });
    draw();
    setTimeout(fit, 80);
    window.addEventListener("load", fit);
    if (window.ResizeObserver) {
      var last = 0;
      new ResizeObserver(function () {
        var w = el.clientWidth;
        if (w && Math.abs(w - last) > 40) { last = w; fit(); }
      }).observe(el);
    }
  });
})();
