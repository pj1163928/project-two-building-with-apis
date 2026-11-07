// The branding's motion (Phase 13): the little JavaScript the CSS needs. Most of the
// motion is CSS (styles/source.css, "Motion"); this script only marks state for it.
// It listens on the document, so swapped-in content needs nothing re-bound. Under
// reduced motion the CSS stops every animation, and the spotlight isn't lit at all.
(function () {
  var root = document.documentElement;
  var reduce = matchMedia("(prefers-reduced-motion: reduce)");

  // ---------- Intros: a full page load only ----------
  // The wordmark's wipe and the mark's cut-in match html:not([data-booted]). Once
  // they've played, this sets the flag, so a boosted swap never plays them again.
  setTimeout(function () {
    root.dataset.booted = "";
  }, 1600);

  // ---------- The logo loader: busy while any htmx request runs ----------
  // Counted from beforeSend (past every point a request can be cancelled) to the
  // request's own loadend, which fires on success, error, abort and timeout alike,
  // even when the element that sent it has been swapped away. The status bar's mark
  // sweeps only after 150 ms, so a quick request doesn't make it flicker.
  var pending = 0;
  var showTimer = null;

  function setBusy(busy) {
    var content = document.getElementById("content");
    if (busy) {
      root.dataset.busy = "";
      if (content) content.setAttribute("aria-busy", "true");
    } else {
      delete root.dataset.busy;
      if (content) content.removeAttribute("aria-busy");
    }
  }

  function update() {
    if (pending > 0) {
      if (showTimer === null) {
        showTimer = setTimeout(function () {
          setBusy(true);
        }, 150);
      }
      return;
    }
    clearTimeout(showTimer);
    showTimer = null;
    setBusy(false);
  }

  document.addEventListener("htmx:beforeSend", function (event) {
    var xhr = event.detail && event.detail.xhr;
    if (!xhr) return;
    pending += 1;
    update();
    xhr.addEventListener(
      "loadend",
      function () {
        pending = Math.max(0, pending - 1);
        update();
      },
      { once: true }
    );
  });

  // ---------- View Transitions on fragment swaps ----------
  // Every swap runs as a View Transition (globalViewTransitions in base.html). htmx
  // only starts one where the browser has document.startViewTransition, so others
  // just swap. Boosted navigation keeps the page's drop and rise; any other swap
  // gets html[data-swap="fragment"], and the content crossfades in place instead.
  document.addEventListener("htmx:beforeTransition", function (event) {
    var detail = event.detail || {};
    var boosted = detail.boosted || (detail.requestConfig && detail.requestConfig.boosted);
    if (boosted) delete root.dataset.swap;
    else root.dataset.swap = "fragment";
  });

  // ---------- Past the main page's cover ----------
  // The main page tucks its title bar and sidebar away while its cover is in view
  // (CSS, "The main page is all cover"). Once the cover's bottom edge rises above the
  // middle of the window, this sets <html data-cover="past"> and the bars come in;
  // back down past 60 % it clears it and they leave. The gap between the two lines
  // stops them flickering at the edge. Scroll events don't bubble, so this listens
  // in the capture phase, which catches #content's scrolling, whatever page is in.
  var coverFrame = 0;

  function checkCover() {
    coverFrame = 0;
    var hero = document.getElementById("home-hero");
    if (!hero) {
      delete root.dataset.cover;
      return;
    }
    var bottom = hero.getBoundingClientRect().bottom;
    var height = window.innerHeight;
    if (bottom < height * 0.5) root.dataset.cover = "past";
    else if (bottom > height * 0.6) delete root.dataset.cover;
  }

  function queueCover() {
    if (!coverFrame) coverFrame = requestAnimationFrame(checkCover);
  }

  document.addEventListener("scroll", queueCover, { capture: true, passive: true });
  window.addEventListener("resize", queueCover, { passive: true });
  document.addEventListener("htmx:afterSettle", queueCover);
  checkCover();

  // ---------- Cursor spotlight ----------
  // The card or tile under the mouse gets data-spot and the pointer's position in
  // --spot-x and --spot-y, once per frame. Mouse only: a touch has no hover.
  var SPOTLIGHT = ".result-card, .type-tile, .gallery-card, .pack-card, .pack-row";
  var lit = null;
  var frame = 0;
  var last = null;

  function light(card) {
    if (lit === card) return;
    if (lit) delete lit.dataset.spot;
    lit = card;
    if (card) card.dataset.spot = "";
  }

  document.addEventListener(
    "pointermove",
    function (event) {
      if (event.pointerType !== "mouse" || reduce.matches) {
        light(null);
        return;
      }
      last = event;
      if (frame) return;
      frame = requestAnimationFrame(function () {
        frame = 0;
        var target = last.target;
        var card = target && target.closest ? target.closest(SPOTLIGHT) : null;
        light(card);
        if (!card) return;
        var box = card.getBoundingClientRect();
        card.style.setProperty("--spot-x", Math.round(last.clientX - box.left) + "px");
        card.style.setProperty("--spot-y", Math.round(last.clientY - box.top) + "px");
      });
    },
    { passive: true }
  );
  root.addEventListener("mouseleave", function () {
    light(null);
  });
})();
