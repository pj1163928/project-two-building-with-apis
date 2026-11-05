// Result and library cards' corner actions: Details, which keeps a card's details
// panel open, and Add to pack, which opens the pack picker
// (catalog/partials/pack_picker.html).
// Listens on the document, like shell.js, so cards that shelves, Load more and
// the library's swaps bring in later work too.
(function () {
  function setDetails(card, open) {
    if (open) card.dataset.details = "open";
    else delete card.dataset.details;
    var button = card.querySelector("[data-card-details]");
    if (button) button.setAttribute("aria-pressed", String(open));
  }

  document.addEventListener("click", function (event) {
    var toggle = event.target.closest("[data-card-details]");
    if (toggle) {
      var card = toggle.closest(".result-card");
      if (card) setDetails(card, card.dataset.details !== "open");
      return;
    }

    // A picker button names its page's dialog and carries the asset's title.
    var opener = event.target.closest("[data-picker]");
    if (opener) {
      var dialog = document.getElementById(opener.dataset.picker);
      if (!dialog) return;
      dialog.querySelectorAll("[data-picker-asset]").forEach(function (element) {
        element.textContent = opener.dataset.pickerAsset;
      });
      dialog.showModal();
      return;
    }

    // A click on the backdrop lands on the <dialog> itself, outside its panel.
    if (event.target.matches && event.target.matches("dialog.picker-dialog")) event.target.close();
  });

  // Escape lets go of every kept-open details panel, unless it's closing a picker.
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape" || document.querySelector("dialog.picker-dialog[open]")) return;
    document.querySelectorAll('.result-card[data-details="open"]').forEach(function (card) {
      setDetails(card, false);
    });
  });
})();
