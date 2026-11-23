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
  var toLatLng = function (lat, lon) { return [lat, lon]; };

  function pos(p) {
    return toLatLng(p.lat, p.lon);
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

  if (typeof L !== "undefined" && window.ulitsyBasemap) {
    window.ulitsyBasemap(el, { scrollWheelZoom: false }, function (m, conv) {
      map = m;
      toLatLng = conv;
      markers = [];
      points.forEach(function (p) {
        if (typeof p.lat !== "number" || typeof p.lon !== "number") return;
        var html = (p.img ? "<a class=\"pop-photo\" href=\"" + p.href + "\"><img src=\"" + p.img + "\" alt=\"\" loading=\"lazy\"></a>" : "") +
          "<b><span class=\"ru\">" + p.title_ru + "</span><span class=\"zh\">" + p.title_zh + "</span></b><br>" +
          "<span class=\"ru\">" + p.addr_ru + "</span><span class=\"zh\">" + p.addr_zh + "</span><br>" +
          "<a href=\"" + p.href + "\"><span class=\"ru\">Открыть историю</span><span class=\"zh\">打开故事</span></a>";
        var icon = L.divIcon({
          className: "pin pin-" + (p.period || "emigration"),
          html: "<span style=\"background:" + markerColor(p.period) + "\"></span>",
          iconSize: [16, 16],
          iconAnchor: [8, 8]
        });
        var marker = L.marker(pos(p), { icon: icon }).addTo(map).bindPopup(html, { maxWidth: 240, minWidth: 200 });
        markers.push({ point: p, marker: marker });
      });
      apply();
      if (points.length === 1) map.setView(pos(points[0]), 15);
    });
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
