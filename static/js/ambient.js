// The ambient glow (base.html's <div class="ambient" data-ambient>): big, loose
// drops of lava-lamp wax in the page's three drop colours, scattered at random
// through the whole content area, however long the page is (user requests,
// 2026-11-05: fluid, random and subtle; then bigger and like water drops; then
// bigger, looser and faster, like a lava lamp).
//
// Every page load rolls a new arrangement. Drops are spread down the page in
// bands, about one per 650 px, so a long page gets as many as it needs, and a
// page that grows (Load more, a filter) gets more drops for the new part. Each
// drop has its own shape, size, two-colour gradient with an off-centre light,
// rising-and-falling path (stretching tall as it travels, squashing wide as it
// turns, like wax), loose wobble (squash one way, stretch the other), speeds and
// starting point in its cycle, so no two move alike.
// The CSS (styles/source.css, "Ambient glow") reads the custom properties set
// here and animates transforms only. Reduced motion keeps the arrangement, still.
(function () {
  var BAND = 650; // px of page per drop, roughly
  var MAX_DROPS = 22;
  var COLOURS = ["var(--drop-a)", "var(--drop-b)", "var(--drop-c)"];

  function between(min, max) { return min + Math.random() * (max - min); }
  function whole(min, max) { return Math.round(between(min, max)); }
  function pick(list) { return list[Math.floor(Math.random() * list.length)]; }
  function signed(min, max) { return (Math.random() < 0.5 ? -1 : 1) * between(min, max); }

  // A loose, uneven outline, like a blob of wax that never quite settles.
  function shape() {
    var a = whole(30, 70), b = whole(30, 70), c = whole(30, 70), d = whole(30, 70);
    return a + "% " + (100 - a) + "% " + b + "% " + (100 - b) + "% / " + c + "% " + d + "% " + (100 - d) + "% " + (100 - c) + "%";
  }

  function layer(className) {
    var element = document.createElement("i");
    element.className = className;
    return element;
  }

  function drop(top, width) {
    var size = whole(620, Math.max(720, Math.min(1300, width * 0.8)));
    var from = pick(COLOURS);
    var to = pick(COLOURS.filter(function (colour) { return colour !== from; }));
    var drift = whole(18, 34); // seconds for one pass of its path
    var squash = between(1.1, 1.24); // how far it stretches; the other way gives as much
    var stretch = between(1.1, 1.22); // how tall it pulls out while it travels
    var outer = document.createElement("span");
    outer.className = "ambient-blob";
    var style = outer.style;
    style.setProperty("--top", Math.round(top) + "px");
    style.setProperty("--left", between(-5, 105) + "%");
    style.setProperty("--size", size + "px");
    style.setProperty("--aspect", between(0.7, 1.15).toFixed(2));
    style.setProperty("--shape", shape());
    style.setProperty("--from", from);
    style.setProperty("--to", to);
    style.setProperty("--hx", whole(30, 70) + "%");
    style.setProperty("--hy", whole(25, 60) + "%");
    style.setProperty("--alpha", between(0.45, 0.85).toFixed(2));
    style.setProperty("--blur", whole(30, 52) + "px");
    style.setProperty("--drift", drift + "s");
    style.setProperty("--wobble", between(5, 9).toFixed(1) + "s");
    style.setProperty("--delay", -between(0, drift).toFixed(1) + "s");
    // Mostly up and down, a long way, like wax rising and falling; a little sideways.
    for (var i = 1; i <= 3; i += 1) {
      style.setProperty("--x" + i, Math.round(signed(20, Math.min(110, width * 0.07))) + "px");
      style.setProperty("--y" + i, Math.round(signed(180, 480)) + "px");
    }
    // Tall and thin while it travels, wide and squat as it turns.
    style.setProperty("--tall", stretch.toFixed(3));
    style.setProperty("--thin", (2 - stretch).toFixed(3));
    style.setProperty("--squat", (1 - (stretch - 1) / 2).toFixed(3));
    style.setProperty("--flat", (1 + (stretch - 1) / 2).toFixed(3));
    style.setProperty("--spin", Math.round(signed(10, 40)) + "deg");
    style.setProperty("--wa", squash.toFixed(3));
    style.setProperty("--wb", (2 - squash).toFixed(3));
    style.setProperty("--wc", (1 + (squash - 1) / 2).toFixed(3));
    style.setProperty("--wd", (1 - (squash - 1) / 2).toFixed(3));
    outer.appendChild(layer("ambient-shell"));
    outer.appendChild(layer("ambient-shell"));
    outer.appendChild(layer("ambient-drop"));
    return outer;
  }

  // Fill the layer from `from` px down to its current height, one drop per band,
  // each at a random height inside its band.
  function fill(layerElement, from) {
    var height = layerElement.offsetHeight;
    var width = layerElement.offsetWidth || 1200;
    var count = layerElement.childElementCount;
    var top = from;
    var fragment = document.createDocumentFragment();
    while (top < height && count < MAX_DROPS) {
      var band = Math.min(BAND, height - top);
      if (band < BAND / 3 && top > 0) break;
      fragment.appendChild(drop(top + between(0, band), width));
      // A wide screen gets a second drop in some bands, so it never looks sparse.
      if (width > 1400 && Math.random() < 0.3 && count + 1 < MAX_DROPS) {
        fragment.appendChild(drop(top + between(0, band), width));
        count += 1;
      }
      count += 1;
      top += BAND;
    }
    layerElement.appendChild(fragment);
    layerElement.dataset.filled = String(Math.max(top, height));
  }

  function setUp(root) {
    var layers = root.querySelectorAll ? root.querySelectorAll("[data-ambient]") : [];
    Array.prototype.forEach.call(layers, function (layerElement) {
      if (layerElement.dataset.filled) return;
      fill(layerElement, 0);
      if (!window.ResizeObserver) return;
      // A page that grows gets drops for its new part; the old ones stay put.
      new ResizeObserver(function () {
        var filled = Number(layerElement.dataset.filled || 0);
        if (layerElement.offsetHeight > filled + BAND / 2) fill(layerElement, filled);
      }).observe(layerElement);
    });
  }

  if (window.htmx) htmx.onLoad(setUp);
  document.addEventListener("DOMContentLoaded", function () { setUp(document); });
})();
