(function () {
  var key = "ulitsy-lang";
  var saved = "ru";
  try { saved = localStorage.getItem(key) || "ru"; } catch (e) {}
  if (saved !== "zh") saved = "ru";

  function apply(lang) {
    document.body.setAttribute("data-lang", lang);
    document.documentElement.lang = lang === "zh" ? "zh-Hans" : "ru";
    var title = document.querySelector('meta[name="title-' + lang + '"]');
    if (title) document.title = title.getAttribute("content");
    var desc = document.querySelector('meta[name="desc-' + lang + '"]');
    var md = document.querySelector('meta[name="description"]');
    if (desc && md) md.setAttribute("content", desc.getAttribute("content"));
    document.querySelectorAll("img[data-alt-ru]").forEach(function (img) {
      img.alt = img.getAttribute(lang === "zh" ? "data-alt-zh" : "data-alt-ru") || "";
    });
    try { localStorage.setItem(key, lang); } catch (e) {}
  }

  apply(saved);
  document.querySelectorAll("[data-set-lang]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      apply(btn.getAttribute("data-set-lang"));
    });
  });
  document.querySelectorAll("[data-print]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      window.print();
    });
  });
})();
