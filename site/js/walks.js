(function () {
  // Карты пеших прогулок. Подложку по языку сайта выбирает basemap.js.
  if (typeof L === "undefined" || !window.ulitsyBasemap) return;
  var els = document.querySelectorAll("[data-walks]");
  if (!els.length) return;

  function label(obj, key) {
    return "<span class=\"ru\">" + obj[key + "_ru"] + "</span><span class=\"zh\">" + obj[key + "_zh"] + "</span>";
  }

  els.forEach(function (el) {
    var walks = [];
    try { walks = JSON.parse(el.getAttribute("data-walks") || "[]"); } catch (e) { walks = []; }
    if (!walks.length) return;
    var map = null;
    var bounds = [];

    function fit() {
      if (!map) return;
      map.invalidateSize();
      if (bounds.length) map.fitBounds(bounds, { padding: [24, 24] });
    }

    window.ulitsyBasemap(el, { scrollWheelZoom: false, zoomSnap: 0.25 }, function (m, conv) {
      map = m;
      bounds = [];
      function p(ll) { return conv(ll[0], ll[1]); }
      walks.forEach(function (w) {
        var line = w.path.map(p);
        bounds = bounds.concat(line);
        L.polyline(line, { color: "#fff", weight: 8, opacity: 0.85 }).addTo(map);
        L.polyline(line, { color: w.color, weight: 5, opacity: 0.95 }).addTo(map);
        (w.ends || []).forEach(function (e) {
          L.circleMarker(p([e.lat, e.lon]), { radius: 6, color: w.color, weight: 3, fillColor: "#fff", fillOpacity: 1 })
            .addTo(map).bindPopup("<b>" + label(e, "label") + "</b>");
        });
        w.stops.forEach(function (s) {
          var icon = L.divIcon({
            className: "walk-num",
            html: "<span style=\"background:" + w.color + "\">" + s.n + "</span>",
            iconSize: [26, 26],
            iconAnchor: [13, 13]
          });
          var html = (s.img ? "<a class=\"pop-photo\" href=\"" + s.href + "\"><img src=\"" + s.img + "\" alt=\"\" loading=\"lazy\"></a>" : "") +
            "<b>" + s.n + ". " + label(s, "title") + "</b><br><a href=\"" + s.href + "\">" +
            "<span class=\"ru\">Открыть историю</span><span class=\"zh\">打开故事</span></a>";
          L.marker(p([s.lat, s.lon]), { icon: icon }).addTo(map).bindPopup(html, { maxWidth: 240, minWidth: 200 });
        });
      });
      fit();
      setTimeout(fit, 80);
    });

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
