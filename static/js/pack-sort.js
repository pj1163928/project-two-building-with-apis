// Drag and drop in the pack builder's item list (packs/partials/items.html).
// An item is dragged by its grip ([data-drag-handle]): pressing the grip makes
// its row draggable for that one drag, so text in the variant and import path
// fields can still be selected. While dragging, the row moves live to where it
// would land. On drop the new order is posted to the list's
// data-reorder-url as `order` (every item's id, comma-separated), and the
// reply swaps #pack-items. Escape (or dropping outside) puts the row back.
// Move up and Move down stay for the keyboard. Listens on the document, so a
// swapped-in list works without setup.
(function () {
  var dragged = null;
  var origin = null; // { list, next } to put the row back on a cancelled drag

  function rows(list) {
    return Array.prototype.slice.call(list.querySelectorAll(":scope > [data-sortable-item]"));
  }

  function order(list) {
    return rows(list).map(function (row) { return row.dataset.itemId; }).join(",");
  }

  document.addEventListener("pointerdown", function (event) {
    var handle = event.target.closest && event.target.closest("[data-drag-handle]");
    if (!handle) return;
    var row = handle.closest("[data-sortable-item]");
    if (row) row.draggable = true;
  });

  document.addEventListener("pointerup", function () {
    if (dragged) return;
    document.querySelectorAll("[data-sortable-item][draggable='true']").forEach(function (row) {
      row.draggable = false;
    });
  });

  document.addEventListener("dragstart", function (event) {
    var row = event.target.closest && event.target.closest("[data-sortable-item]");
    if (!row || !row.draggable) return;
    var list = row.closest("[data-sortable-list]");
    if (!list) return;
    dragged = row;
    origin = { list: list, before: order(list), next: row.nextElementSibling };
    list.dataset.sorting = "true";
    row.dataset.dragging = "true";
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", row.dataset.itemId);
  });

  document.addEventListener("dragover", function (event) {
    if (!dragged) return;
    var over = event.target.closest && event.target.closest("[data-sortable-item]");
    if (!over || over.parentElement !== dragged.parentElement) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    if (over === dragged) return;
    var box = over.getBoundingClientRect();
    var after = event.clientY > box.top + box.height / 2;
    var target = after ? over.nextElementSibling : over;
    if (target !== dragged && target !== dragged.nextElementSibling) {
      over.parentElement.insertBefore(dragged, target);
    }
  });

  document.addEventListener("drop", function (event) {
    if (dragged) event.preventDefault();
  });

  document.addEventListener("dragend", function (event) {
    if (!dragged) return;
    var row = dragged;
    var list = origin.list;
    dragged = null;
    row.draggable = false;
    delete row.dataset.dragging;
    delete list.dataset.sorting;
    if (event.dataTransfer.dropEffect === "none") {
      // Cancelled: back where it was.
      list.insertBefore(row, origin.next);
      return;
    }
    var now = order(list);
    if (now === origin.before || !window.htmx) return;
    htmx.ajax("POST", list.dataset.reorderUrl, {
      source: list,
      target: "#pack-items",
      swap: "outerHTML transition:false",
      values: { order: now },
    });
  });
})();
