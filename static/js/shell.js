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

  // ---------- Broken thumbnails ----------
  // A provider thumbnail that fails to load is removed, uncovering the type
  // icon beneath it (catalog/partials/result_card.html). Image errors don't
  // bubble, so this listens in the capture phase, which also covers every
  // image a shelf swap brings in later.
  document.addEventListener(
    "error",
    function (event) {
      var image = event.target;
      if (image.tagName === "IMG" && image.hasAttribute("data-thumb-fallback")) image.remove();
    },
    true
  );

  // ---------- Colour scheme ----------
  // The title bar's switch steps System → Light → Dark, and the Settings page's
  // Appearance chips pick one. Either switches at once and saves the ax-theme
  // cookie, which the server reads for the next page's first paint (see the
  // inline script in base.html). Without JavaScript the forms post to
  // accounts:theme instead.
  var SCHEMES = ["system", "light", "dark"];
  var SCHEME_LABELS = { system: "System", light: "Light", dark: "Dark" };

  function setScheme(choice) {
    if (SCHEMES.indexOf(choice) === -1) return;
    root.dataset.schemeChoice = choice;
    document.cookie = "ax-theme=" + choice + "; path=/; max-age=31536000; SameSite=Lax";
    if (window.axScheme) window.axScheme.apply();
    syncScheme(document);
  }

  function syncScheme(within) {
    if (!within.querySelectorAll) return;
    var choice = root.dataset.schemeChoice || "system";
    var next = SCHEMES[(SCHEMES.indexOf(choice) + 1) % SCHEMES.length];
    within.querySelectorAll("#theme-toggle").forEach(function (button) {
      button.value = next;
      button.title = "Theme: " + SCHEME_LABELS[choice];
      button.setAttribute("aria-label", "Theme: " + SCHEME_LABELS[choice] + ". Switch to " + SCHEME_LABELS[next]);
    });
    within.querySelectorAll("input[data-theme-choice]").forEach(function (input) {
      input.checked = input.value === choice;
    });
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("#theme-toggle");
    if (!button) return;
    event.preventDefault();
    setScheme(button.value);
  });
  document.addEventListener("change", function (event) {
    if (event.target.matches && event.target.matches("input[data-theme-choice]")) setScheme(event.target.value);
  });
  // A boosted swap keeps <html> (and so the choice) but brings a new switch.
  if (window.htmx) htmx.onLoad(syncScheme);

  // ---------- Remembered folds ----------
  // A <details data-remember="key"> (the library's "Show N more" tags) opens the
  // way the member last left it, in localStorage. One the server opened because
  // a chosen chip sits inside (data-forced-open) stays open.
  function restoreFolds(root) {
    if (!root.querySelectorAll) return;
    root.querySelectorAll("details[data-remember]").forEach(function (fold) {
      if (fold.hasAttribute("data-forced-open")) return;
      var saved = null;
      try { saved = localStorage.getItem(fold.dataset.remember); } catch (error) { /* storage off */ }
      if (saved !== null) fold.open = saved === "open";
    });
  }
  document.addEventListener(
    "toggle",
    function (event) {
      var fold = event.target;
      if (!fold.matches || !fold.matches("details[data-remember]")) return;
      // A fold the server opened fires toggle as it's parsed; that isn't the member's choice.
      if (fold.hasAttribute("data-forced-open") && fold.open) return;
      try { localStorage.setItem(fold.dataset.remember, fold.open ? "open" : "closed"); } catch (error) { /* storage off */ }
    },
    true
  );
  if (window.htmx) htmx.onLoad(restoreFolds);

  // ---------- Filters that apply as they change ----------
  // A [data-autosubmit] input (Discover's license chips, in the side panel)
  // submits its form at once. The input names its form with form="…", and
  // requestSubmit() goes through htmx's boost like any other submit.
  document.addEventListener("change", function (event) {
    var input = event.target;
    if (!input.matches || !input.matches("[data-autosubmit]") || !input.form) return;
    if (input.form.requestSubmit) input.form.requestSubmit();
    else input.form.submit();
  });

  // ---------- A newer stylesheet or script ----------
  // A boosted swap replaces only <body>, so the page would go on using the
  // stylesheet and scripts it first loaded, however often they change: a style
  // fix looked unfixed until a hard reload (user report, 2026-11-06). Each one's
  // URL carries its version (?v=, versioned_static), so when a page arriving by
  // a GET names different ones, it's loaded in full instead of swapped in.
  var ASSET_URL = /(?:href|src)="([^"]*\/static\/[^"]*\?v=\d+)"/g;
  function assetsIn(html) {
    var head = html.split(/<body[\s>]/i)[0], found = [], match;
    ASSET_URL.lastIndex = 0;
    while ((match = ASSET_URL.exec(head))) found.push(match[1]);
    return found.sort().join(" ");
  }
  function loadedAssets() {
    var found = [];
    document.querySelectorAll('head link[href*="?v="], head script[src*="?v="]').forEach(function (node) {
      found.push(node.getAttribute("href") || node.getAttribute("src"));
    });
    return found.sort().join(" ");
  }
  document.addEventListener("htmx:beforeSwap", function (event) {
    var detail = event.detail, html = detail.serverResponse;
    if (!detail.boosted && !(detail.requestConfig && detail.requestConfig.boosted)) return;
    if (!detail.requestConfig || detail.requestConfig.verb !== "get" || typeof html !== "string") return;
    var arriving = assetsIn(html);
    if (!arriving || arriving === loadedAssets()) return;
    detail.shouldSwap = false;
    window.location.assign(detail.xhr.responseURL || detail.requestConfig.path);
  });

  // ---------- After every boosted swap ----------
  document.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.boosted) {
      armHoverGate();
      syncPanel();
    }
  });
})();
