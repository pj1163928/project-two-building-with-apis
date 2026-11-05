// Result and library cards' corner actions: Details, which keeps a card's details
// panel open, and Add to pack, which opens the pack picker
// (catalog/partials/pack_picker.html) and loads the member's packs into it.
// Also the page's other small dialogs (.picker-dialog): one that HTMX fills
// (the library's Remove confirm) opens once it arrives, a [data-dialog-open]
// button opens its dialog (the builder's Delete pack), and a [data-dialog-done]
// form closes its dialog once its request succeeds.
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
      // The list is fetched each time it opens, so it's always current.
      var list = dialog.querySelector("#pack-picker-list");
      if (list && opener.dataset.pickerUrl && window.htmx) {
        list.innerHTML = '<p class="picker-empty">Loading your packs…</p>';
        htmx.ajax("GET", opener.dataset.pickerUrl, { source: list, target: list, swap: "innerHTML transition:false" });
      }
      dialog.showModal();
      return;
    }

    var dialogOpener = event.target.closest("[data-dialog-open]");
    if (dialogOpener) {
      var named = document.getElementById(dialogOpener.dataset.dialogOpen);
      if (named && !named.open) named.showModal();
      return;
    }

    // A click on the backdrop lands on the <dialog> itself, outside its panel.
    if (event.target.matches && event.target.matches("dialog.picker-dialog")) event.target.close();
  });

  // A dialog that HTMX has just filled (the library's Remove confirm) opens.
  document.addEventListener("htmx:afterSwap", function (event) {
    var target = event.detail.target;
    if (target && target.matches && target.matches("dialog.picker-dialog") && !target.open) target.showModal();
  });

  // A [data-dialog-done] form's dialog closes once its request has succeeded.
  document.addEventListener("htmx:afterRequest", function (event) {
    var form = event.detail.elt.closest && event.detail.elt.closest("[data-dialog-done]");
    if (!form || !event.detail.successful) return;
    var dialog = form.closest("dialog");
    if (dialog && dialog.open) dialog.close();
  });

  // Escape lets go of every kept-open details panel, unless it's closing a dialog
  // (a picker, or the library drawer).
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape" || document.querySelector("dialog[open]")) return;
    document.querySelectorAll('.result-card[data-details="open"]').forEach(function (card) {
      setDetails(card, false);
    });
  });
})();
