(function () {
  var root = document.querySelector("[data-catalog]");
  if (!root) return;
  var input = root.querySelector("[data-filter-text]");
  var cards = Array.prototype.slice.call(root.querySelectorAll("[data-themes]"));
  var empty = root.querySelector("[data-empty]");
  var theme = "all";
  var period = "all";
  var kind = "all";

  function match(value, current) {
    if (current === "all") return true;
    return value === current;
  }

  function hasTheme(value, current) {
    if (current === "all") return true;
    return (" " + value + " ").indexOf(" " + current + " ") !== -1;
  }

  function apply() {
    var query = (input && input.value || "").toLowerCase().trim();
    var shown = 0;
    cards.forEach(function (card) {
      var themes = card.getAttribute("data-themes") || "";
      var cardPeriod = card.getAttribute("data-period") || "";
      var cardKind = card.getAttribute("data-kind") || "";
      var text = (card.textContent || "").toLowerCase();
      var show = hasTheme(themes, theme)
        && match(cardPeriod, period)
        && match(cardKind, kind)
        && (!query || text.indexOf(query) !== -1);
      card.hidden = !show;
      if (show) shown += 1;
    });
    if (empty) empty.hidden = shown !== 0;
  }

  function bind(attr, setter) {
    root.querySelectorAll("[" + attr + "]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setter(btn.getAttribute(attr));
        root.querySelectorAll("[" + attr + "]").forEach(function (other) {
          other.setAttribute("aria-pressed", other === btn ? "true" : "false");
        });
        apply();
      });
    });
  }

  bind("data-theme", function (v) { theme = v; });
  bind("data-period-filter", function (v) { period = v; });
  bind("data-kind-filter", function (v) { kind = v; });

  if (input) input.addEventListener("input", apply);

  var params = new URLSearchParams(window.location.search);
  if (params.get("q") && input) input.value = params.get("q");
  apply();
})();
