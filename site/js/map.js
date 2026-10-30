(function () {
  var el = document.getElementById("map");
  if (!el || typeof L === "undefined") return;
  var points = [];
  try { points = JSON.parse(el.getAttribute("data-points") || "[]"); } catch (e) { return; }
  var map = L.map(el, { scrollWheelZoom: false });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap"
  }).addTo(map);
  var bounds = [];
  points.forEach(function (p) {
    if (typeof p.lat !== "number" || typeof p.lon !== "number") return;
    var html = "<b><span class=\"ru\">" + p.title_ru + "</span><span class=\"zh\">" + p.title_zh + "</span></b><br>" +
      "<span class=\"ru\">" + p.addr_ru + "</span><span class=\"zh\">" + p.addr_zh + "</span><br>" +
      "<a href=\"" + p.href + "\"><span class=\"ru\">Открыть</span><span class=\"zh\">打开</span></a>";
    L.marker([p.lat, p.lon]).addTo(map).bindPopup(html);
    bounds.push([p.lat, p.lon]);
  });
  if (bounds.length) map.fitBounds(bounds, { padding: [28, 28] });
  setTimeout(function () { map.invalidateSize(); }, 200);
})();
