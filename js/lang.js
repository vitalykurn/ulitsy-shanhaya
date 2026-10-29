(function () {
  var key = "ulitsy-lang";
  var saved = "ru";
  try { saved = localStorage.getItem(key) || "ru"; } catch (e) {}
  if (saved !== "zh") saved = "ru";

  function apply(lang) {
    document.body.setAttribute("data-lang", lang);
    document.documentElement.lang = lang === "zh" ? "zh-Hans" : "ru";
    try { localStorage.setItem(key, lang); } catch (e) {}
  }

  apply(saved);
  document.querySelectorAll("[data-set-lang]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      apply(btn.getAttribute("data-set-lang"));
    });
  });
})();
