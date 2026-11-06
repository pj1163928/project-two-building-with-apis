// The right-edge scroll ruler (Phase 12), on the main page and Discover
// (templates/partials/scroll_ruler.html). Its section links are plain #anchors,
// so they jump without JavaScript. This adds three things:
// - the ink fill along the track follows how far #content (the page's scroll
//   container) has scrolled (--ruler-progress, 0 to 1)
// - the section in view is marked aria-current="true": the last one whose top
//   has passed a line a third of the way down, or the last one at the very end
// - a click scrolls smoothly to the section (instantly under reduced motion),
//   moves keyboard focus there and puts its #id in the address bar
// Delegated and set up again after every swap, like the shell's other scripts.
(function () {
  var reduce = matchMedia("(prefers-reduced-motion: reduce)");
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
