// The editor shell's behaviour. Navigation is boosted (hx-boost on <body>), so
// each page swaps a new #app in without reloading the document. Everything here
// therefore listens on the document (delegation) rather than binding to
// elements a swap would replace, and re-syncs after every swap.
(function () {
  var root = document.documentElement;

  // ---------- Side-panel toggle ----------
  // base.html sets <html data-panel> before first paint; this keeps the
  // button, its tooltip and localStorage in step with it.
  function syncPanel() {
    var button = document.getElementById("panel-toggle");
    if (!button) return;
    var open = root.dataset.panel !== "collapsed";
    button.setAttribute("aria-expanded", String(open));
    var tip = button.querySelector(".tip");
    if (tip) tip.textContent = open ? "Collapse panel" : "Expand panel";
  }

  document.addEventListener("click", function (event) {
    if (!event.target.closest("#panel-toggle")) return;
    root.dataset.panel = root.dataset.panel === "collapsed" ? "open" : "collapsed";
    localStorage.setItem("ax-panel", root.dataset.panel);
    syncPanel();
  });
  syncPanel();

  // Turn on the slide animation only after the first frame, so the first page
  // load never animates. It stays on: swaps don't change the panel's state.
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      root.dataset.panelReady = "";
    });
  });

  // ---------- Hover gate ----------
  // After a click, the next page appears under a cursor that hasn't moved, and
  // the browser hovers whatever chip or icon is now beneath it: a chip flips to
  // its icon and turns white, or a tooltip slides out, the moment the page
  // appears. The title-bar and activity-bar hover styles wait for
  // <html data-pointer>, which is set only once the pointer really moves (more
  // than a few pixels, so the browser's own synthetic move doesn't count). Each
  // swap clears it again.
  var start = null;

  function onMove(event) {
    if (start === null) {
      start = { x: event.clientX, y: event.clientY };
      return;
    }
    if (Math.abs(event.clientX - start.x) + Math.abs(event.clientY - start.y) < 4) return;
    root.dataset.pointer = "";
    removeEventListener("pointermove", onMove);
  }

  function armHoverGate() {
    delete root.dataset.pointer;
    start = null;
    removeEventListener("pointermove", onMove);
    addEventListener("pointermove", onMove, { passive: true });
  }
  armHoverGate();

  // ---------- "/" focuses the page's search ----------
  // A page marks its search input with data-search-shortcut (Discover's command
  // bar). The key is left alone while the cursor is already in a text field,
  // so typing "/" in a search or a note still types it.
  function inTextField(element) {
    if (!element || !element.tagName) return false;
    return element.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(element.tagName);
  }

  document.addEventListener("keydown", function (event) {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.defaultPrevented || inTextField(event.target)) return;
    var search = document.querySelector("[data-search-shortcut]");
    if (!search) return;
    event.preventDefault();
    search.focus();
    search.select();
  });

  // ---------- After every boosted swap ----------
  document.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.boosted) {
      armHoverGate();
      syncPanel();
    }
  });
})();
