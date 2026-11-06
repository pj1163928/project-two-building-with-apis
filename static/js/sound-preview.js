// Sound previews: on Discover's result cards and drawer, library cards and the
// library drawer, and pack items in the builder and on a pack's page (user
// request, 2026-11-06). A play button (catalog/partials/sound_play.html)
// carries the provider's audio URL in data-sound-preview; the audio streams
// from the provider and is never copied. Its nearest [data-sound-card] takes
// the state (data-sound) and the progress (--progress). One preview plays at a
// time. Content arrives and changes through HTMX, so this listens on the
// document, stops the sound if its card is swapped away, and stops it when the
// dialog it plays in (a drawer) closes.
(function () {
  var current = null; // { button, card, audio }

  function setState(entry, state) {
    entry.card.dataset.sound = state;
    var playing = state === "playing" || state === "loading";
    entry.button.setAttribute("aria-pressed", String(playing));
    var title = entry.button.dataset.title;
    entry.button.setAttribute(
      "aria-label",
      state === "error"
        ? "Preview unavailable: " + title
        : (playing ? "Pause the preview of " : "Play a preview of ") + title
    );
  }

  function stop() {
    if (!current) return;
    current.audio.pause();
    current.audio.removeAttribute("src");
    current.audio.load();
    if (current.card.dataset.sound !== "error") setState(current, "idle");
    current.card.style.removeProperty("--progress");
    current = null;
  }

  function start(button) {
    var card = button.closest("[data-sound-card]") || button.parentNode;
    var audio = new Audio(button.dataset.soundPreview);
    audio.preload = "auto";
    var entry = { button: button, card: card, audio: audio };
    current = entry;
    setState(entry, "loading");
    audio.addEventListener("playing", function () {
      if (current === entry) setState(entry, "playing");
    });
    audio.addEventListener("pause", function () {
      if (current === entry && !audio.ended) setState(entry, "paused");
    });
    audio.addEventListener("timeupdate", function () {
      if (current === entry && audio.duration) {
        card.style.setProperty("--progress", String(audio.currentTime / audio.duration));
      }
    });
    audio.addEventListener("ended", function () {
      if (current === entry) stop();
    });
    audio.addEventListener("error", function () {
      if (current !== entry) return;
      setState(entry, "error");
      button.disabled = true;
      stop();
    });
    audio.play().catch(function () {
      // A refused or failed play() also fires "error" when the source is bad;
      // otherwise (autoplay rules) just fall back to paused.
      if (current === entry && card.dataset.sound === "loading") setState(entry, "paused");
    });
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-sound-preview]");
    if (!button) return;
    event.preventDefault();
    if (!button.dataset.title) {
      button.dataset.title = button.getAttribute("aria-label").replace(/^Play a preview of /, "");
    }
    if (current && current.button === button) {
      if (current.audio.paused) current.audio.play();
      else current.audio.pause();
      return;
    }
    stop();
    start(button);
  });

  // A shelf that's retried, or a page that's left, takes its cards with it.
  document.addEventListener("htmx:afterSwap", function () {
    if (current && !document.contains(current.button)) stop();
  });

  // A drawer that closes takes its sound with it ("close" doesn't bubble).
  document.addEventListener("close", function (event) {
    if (current && event.target.contains && event.target.contains(current.button)) stop();
  }, true);
})();
