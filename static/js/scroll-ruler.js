// The right-edge scroll ruler (Phase 12; on every page at the user's request,
// 2026-11-06; base.html). Its section links are plain #anchors, so they jump
// without JavaScript. This adds four things:
// - each entry sits level with its section's place in the page (--at), at
//   least MIN_GAP px from its neighbours, once [data-placed] is on the ruler
// - the ink fill and the cursor follow how far #content (the page's scroll
//   container) has scrolled (--ruler-progress, 0 to 1)
// - the section in view is marked aria-current="true": the last one whose top
//   has passed a line a third of the way down, or the last one at the very end
// - a click scrolls smoothly to the section (instantly under reduced motion),
//   moves keyboard focus there and puts its #id in the address bar
// Delegated and set up again after every swap, like the shell's other scripts.
(function () {
  var reduce = matchMedia("(prefers-reduced-motion: reduce)");
  var MIN_GAP = 28;
  var pending = false;

  function ruler() { return document.querySelector("[data-scroll-ruler]"); }
  function scroller() { return document.getElementById("content"); }

  function update() {
    pending = false;
    var nav = ruler(), box = scroller();
    if (!nav || !box) return;
    var max = box.scrollHeight - box.clientHeight;
    var progress = max > 0 ? Math.min(1, Math.max(0, box.scrollTop / max)) : 0;
    nav.style.setProperty("--ruler-progress", progress.toFixed(4));

    var links = Array.prototype.slice.call(nav.querySelectorAll("[data-ruler-target]"));
    var present = links.filter(function (link) { return document.getElementById(link.dataset.rulerTarget); });
    // An entry whose section isn't on the page (yet) has nowhere to go.
    links.forEach(function (link) { link.parentElement.hidden = present.indexOf(link) === -1; });
    place(nav, box, present);
    var line = box.getBoundingClientRect().top + box.clientHeight / 3;
    var current = present[0] || null;
    present.forEach(function (link) {
      if (document.getElementById(link.dataset.rulerTarget).getBoundingClientRect().top <= line) current = link;
    });
    if (max > 0 && box.scrollTop >= max - 2 && present.length) current = present[present.length - 1];
    links.forEach(function (link) {
      if (link === current) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    });
  }

  // Each entry level with where its section starts in the page, kept MIN_GAP
  // apart (pushed down, then back up from the bottom if they ran past it).
  function place(nav, box, present) {
    var index = nav.querySelector(".scroll-ruler-index");
    var height = index ? index.clientHeight : 0;
    if (!height || !present.length) return;
    var top = box.getBoundingClientRect().top - box.scrollTop;
    var spots = present.map(function (link) {
      var target = document.getElementById(link.dataset.rulerTarget);
      var at = (target.getBoundingClientRect().top - top) / Math.max(box.scrollHeight, 1);
      return Math.min(1, Math.max(0, at)) * height;
    });
    for (var i = 1; i < spots.length; i++) spots[i] = Math.max(spots[i], spots[i - 1] + MIN_GAP);
    var last = spots.length - 1;
    if (spots[last] > height) spots[last] = height;
    for (var j = last - 1; j >= 0; j--) spots[j] = Math.min(spots[j], spots[j + 1] - MIN_GAP);
    present.forEach(function (link, n) {
      link.parentElement.style.setProperty("--at", Math.max(0, spots[n]).toFixed(1) + "px");
    });
    nav.setAttribute("data-placed", "");
  }

  function schedule() {
    if (pending) return;
    pending = true;
    requestAnimationFrame(update);
  }

  // Scroll events don't bubble, so listen in the capture phase for #content's.
  document.addEventListener("scroll", function (event) {
    if (event.target === scroller()) schedule();
  }, true);
  window.addEventListener("resize", schedule);

  document.addEventListener("click", function (event) {
    var link = event.target.closest("[data-ruler-target]");
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    var target = document.getElementById(link.dataset.rulerTarget);
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: reduce.matches ? "auto" : "smooth", block: "start" });
    if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
    history.replaceState(history.state, "", "#" + target.id);
  });

  // A swap can bring a ruler (boosted navigation) or change the page's length
  // (a shelf loading, the gallery's results), so measure again after each.
  if (window.htmx) htmx.onLoad(schedule);
  schedule();
})();
