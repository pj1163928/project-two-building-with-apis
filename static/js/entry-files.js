// An entry's file filters (catalog/partials/entry_files.html): the Resolution
// and Format chips narrow the variant list in the page, without a request.
// Without JavaScript the chips stay hidden and every variant shows. Listens on
// the document, so a drawer that swaps in later works too.
(function () {
  function section(element) { return element.closest(".entry-section"); }

  function apply(root) {
    var chosen = {};
    root.querySelectorAll("[data-file-filter]:checked").forEach(function (input) {
      chosen[input.dataset.fileFilter] = input.value;
    });
    var shown = 0;
    root.querySelectorAll("[data-file-list] > li").forEach(function (item) {
      var match = (!chosen.resolution || item.dataset.resolution === chosen.resolution) &&
        (!chosen.format || item.dataset.format === chosen.format);
      item.hidden = !match;
      if (match) shown += 1;
    });
    var empty = root.querySelector("[data-file-empty]");
    if (empty) empty.hidden = shown > 0;
  }

  document.addEventListener("change", function (event) {
    if (event.target.matches && event.target.matches("[data-file-filter]")) apply(section(event.target));
  });

  function setUp(root) {
    if (!root.querySelectorAll) return;
    root.querySelectorAll("[data-file-filters]").forEach(function (filters) {
      filters.hidden = false;
      apply(section(filters));
    });
  }

  if (window.htmx) htmx.onLoad(setUp);
})();
